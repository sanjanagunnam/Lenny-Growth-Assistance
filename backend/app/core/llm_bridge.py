"""Unified LLM Bridge supporting Ollama and Anthropic with resilient timeout handling."""

import logging
from typing import Optional
import httpx
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom Exception Hierarchy
# ---------------------------------------------------------------------------

class LLMBridgeError(Exception):
    """Base exception for LLM bridge operations."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class LLMTimeoutError(LLMBridgeError):
    """Raised when an LLM provider times out."""
    def __init__(self, message: str = "LLM request timed out."):
        super().__init__(message, status_code=504)


class LLMUnavailableError(LLMBridgeError):
    """Raised when an LLM provider is unreachable or offline."""
    def __init__(self, message: str = "LLM provider is currently unavailable."):
        super().__init__(message, status_code=503)


class LLMConfigurationError(LLMBridgeError):
    """Raised when required credentials or settings are missing."""
    def __init__(self, message: str = "LLM provider configuration is invalid."):
        super().__init__(message, status_code=400)


class LLMGenerationError(LLMBridgeError):
    """Raised when an LLM provider returns an unexpected error during generation."""
    def __init__(self, message: str = "Error occurred during text generation."):
        super().__init__(message, status_code=502)


# ---------------------------------------------------------------------------
# LLM Bridge Implementation
# ---------------------------------------------------------------------------

class LLMBridge:
    """Unified client for dynamic model generation supporting Ollama and Anthropic Claude."""

    def __init__(
        self,
        ollama_base_url: Optional[str] = None,
        ollama_default_model: Optional[str] = None,
        ollama_timeout: Optional[float] = None,
        anthropic_api_key: Optional[str] = None,
        anthropic_default_model: Optional[str] = None,
    ):
        self.ollama_base_url = (ollama_base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.ollama_default_model = ollama_default_model or settings.OLLAMA_DEFAULT_MODEL
        self.ollama_timeout = ollama_timeout or settings.OLLAMA_TIMEOUT_SECONDS

        self.anthropic_api_key = anthropic_api_key or settings.ANTHROPIC_API_KEY
        self.anthropic_default_model = anthropic_default_model or settings.ANTHROPIC_DEFAULT_MODEL

    async def _generate_ollama(
        self,
        system_prompt: str,
        prompt: str,
        model: Optional[str] = None,
    ) -> str:
        """Call Ollama /api/generate with strict timeout handling."""
        model_name = model or self.ollama_default_model
        endpoint = f"{self.ollama_base_url}/api/generate"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
        }

        logger.info("Dispatching Ollama request (model: %s) to %s", model_name, endpoint)

        timeout_config = httpx.Timeout(
            timeout=self.ollama_timeout,
            connect=5.0,
        )

        try:
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()
                data = response.json()
                if "response" not in data:
                    raise LLMGenerationError(f"Unexpected Ollama response format: {data}")
                return data["response"]

        except (httpx.ConnectError, httpx.ConnectTimeout) as err:
            logger.warning("Ollama connection failed: %s", err)
            raise LLMUnavailableError(
                f"Ollama daemon is offline at {self.ollama_base_url}. "
                "Ensure Ollama is running ('ollama serve') or switch to 'anthropic' provider."
            ) from err

        except httpx.TimeoutException as err:
            logger.warning("Ollama request timed out after %.1fs: %s", self.ollama_timeout, err)
            raise LLMTimeoutError(
                f"Local Ollama model timed out ({int(self.ollama_timeout)}s). Ensure Ollama is running, or toggle the model provider to 'Anthropic Claude' in the top bar."
            ) from err

        except httpx.HTTPStatusError as err:
            logger.error("Ollama HTTP status error %s: %s", err.response.status_code, err.response.text)
            raise LLMGenerationError(
                f"Ollama returned HTTP error {err.response.status_code}: {err.response.text}"
            ) from err

        except Exception as err:
            if isinstance(err, LLMBridgeError):
                raise
            logger.error("Unexpected error contacting Ollama: %s", err)
            raise LLMGenerationError(f"Ollama generation failed: {str(err)}") from err

    async def _generate_anthropic(
        self,
        system_prompt: str,
        prompt: str,
        model: Optional[str] = None,
    ) -> str:
        """Call Anthropic Claude via native SDK."""
        if not self.anthropic_api_key:
            raise LLMConfigurationError(
                "ANTHROPIC_API_KEY is not configured on the server. "
                "Provide an API key in your environment or use 'ollama' provider."
            )

        model_name = model or self.anthropic_default_model
        # Obfuscate log to prevent secret leakage
        logger.info("Dispatching Anthropic request (model: %s)", model_name)

        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=self.anthropic_api_key)
            response = await client.messages.create(
                model=model_name,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            text_blocks = [
                block.text for block in response.content if hasattr(block, "text")
            ]
            return "".join(text_blocks)

        except anthropic.AuthenticationError as err:
            logger.error("Anthropic authentication failed.")
            raise LLMConfigurationError(f"Invalid Anthropic API credentials: {err}") from err

        except anthropic.APIConnectionError as err:
            logger.warning("Anthropic connection failed: %s", err)
            raise LLMUnavailableError(f"Unable to reach Anthropic API: {err}") from err

        except anthropic.RateLimitError as err:
            logger.warning("Anthropic rate limit exceeded.")
            raise LLMUnavailableError(f"Anthropic rate limit exceeded: {err}") from err

        except Exception as err:
            if isinstance(err, LLMBridgeError):
                raise
            logger.error("Unexpected Anthropic error: %s", err)
            raise LLMGenerationError(f"Anthropic generation error: {str(err)}") from err

    async def generate(
        self,
        system_prompt: str,
        prompt: str,
        provider: str = "ollama",
        model: Optional[str] = None,
    ) -> str:
        """Dynamically execute LLM completion using the selected provider."""
        provider_normalized = provider.strip().lower()

        if not prompt.strip():
            raise ValueError("Prompt cannot be empty or whitespace only.")

        if provider_normalized == "ollama":
            return await self._generate_ollama(
                system_prompt=system_prompt,
                prompt=prompt,
                model=model,
            )
        elif provider_normalized == "anthropic":
            return await self._generate_anthropic(
                system_prompt=system_prompt,
                prompt=prompt,
                model=model,
            )
        else:
            raise LLMConfigurationError(
                f"Unknown LLM provider '{provider}'. Must be 'ollama' or 'anthropic'."
            )
