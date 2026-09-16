"""Unified LLM Bridge supporting Ollama and Anthropic with resilient timeout handling."""

import logging
import os
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
        anthropic_workspace_id: Optional[str] = None,
    ):
        self.ollama_base_url = (ollama_base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.ollama_default_model = ollama_default_model or settings.OLLAMA_DEFAULT_MODEL
        self.ollama_timeout = ollama_timeout or settings.OLLAMA_TIMEOUT_SECONDS

        self.anthropic_api_key = anthropic_api_key or settings.ANTHROPIC_API_KEY
        self.anthropic_default_model = anthropic_default_model or settings.ANTHROPIC_DEFAULT_MODEL
        self.anthropic_workspace_id = anthropic_workspace_id or getattr(settings, 'ANTHROPIC_WORKSPACE_ID', None)

        # Cache Anthropic client for connection reuse (faster subsequent calls)
        self._anthropic_client = None

    def _get_anthropic_client(self):
        """Lazy-initialize and cache the Anthropic async client for connection pooling."""
        if self._anthropic_client is None:
            import anthropic
            extra_headers = {}
            if self.anthropic_workspace_id:
                extra_headers['anthropic-workspace-id'] = self.anthropic_workspace_id
            self._anthropic_client = anthropic.AsyncAnthropic(
                api_key=self.anthropic_api_key,
                default_headers=extra_headers if extra_headers else None,
            )
        return self._anthropic_client

    async def _generate_ollama(
        self,
        system_prompt: str,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Call Ollama /api/generate with fast generation limits and strict timeout handling."""
        model_name = model or self.ollama_default_model
        endpoint = f"{self.ollama_base_url}/api/generate"
        predict_limit = max_tokens or 220
        payload = {
            "model": model_name,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "keep_alive": -1,
            "options": {
                "num_predict": predict_limit,
                "temperature": 0.6,
                "top_p": 0.9,
                "num_ctx": 1024,
                "num_thread": 8,
            },
        }

        logger.info("Dispatching Ollama request (model: %s, num_predict: %d) to %s", model_name, predict_limit, endpoint)

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
        max_tokens: Optional[int] = None,
    ) -> str:
        """Call Anthropic Claude via native SDK with connection pooling for speed."""
        if not self.anthropic_api_key:
            raise LLMConfigurationError(
                "ANTHROPIC_API_KEY is not configured on the server. "
                "Provide an API key in your environment or use 'ollama' provider."
            )

        model_name = model or self.anthropic_default_model
        token_limit = max_tokens or 1024
        logger.info("Dispatching Anthropic request (model: %s, max_tokens: %d)", model_name, token_limit)

        try:
            import anthropic
            client = self._get_anthropic_client()
            response = await client.messages.create(
                model=model_name,
                max_tokens=token_limit,
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

        except anthropic.BadRequestError as err:
            logger.error("Anthropic bad request: %s", err)
            err_str = str(err)
            if "credit balance" in err_str.lower():
                raise LLMConfigurationError(
                    "Your Anthropic account credit balance is too low. Please purchase credits at console.anthropic.com/settings/billing, or switch provider to free local 'ollama'."
                ) from err
            raise LLMGenerationError(f"Anthropic API error: {err_str}") from err

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

    async def _generate_gemini(
        self,
        system_prompt: str,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Call Google Gemini API via REST with ultra-fast latency."""
        api_key = getattr(settings, 'GEMINI_API_KEY', None) or os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
        if not api_key:
            raise LLMConfigurationError("Gemini API key is missing. Set GEMINI_API_KEY in your environment or .env file.")

        gemini_aliases = {
            "gemini-1.5-flash": "gemini-3.8-flash",
            "gemini-1.5-pro": "gemini-3.8-flash",
            "gemini-2.0-flash": "gemini-3.8-flash",
            "gemini-2.5-flash": "gemini-3.8-flash",
            "gemini-2.5-pro": "gemini-3.8-flash",
            "gemini-flash": "gemini-3.8-flash",
            "gemini-flash-latest": "gemini-3.8-flash",
            "gemini-pro": "gemini-3.8-flash",
        }
        model_name = model or getattr(settings, 'GEMINI_DEFAULT_MODEL', 'gemini-3.8-flash')
        if model_name.startswith("models/"):
            model_name = model_name[len("models/"):]
        model_name = gemini_aliases.get(model_name, model_name)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nPlease confirm understanding."}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will strictly follow these instructions."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens or 1024,
                "temperature": 0.2,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code in (503, 404) and model_name != "gemini-3.6-flash":
                    logger.warning("Gemini model %s returned %s, falling back to gemini-3.6-flash", model_name, resp.status_code)
                    fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
                    resp = await client.post(fallback_url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"]
                raise LLMGenerationError(f"Unexpected Gemini response structure: {data}")
        except httpx.HTTPStatusError as err:
            raise LLMGenerationError(f"Gemini API error {err.response.status_code}: {err.response.text}") from err
        except Exception as err:
            if isinstance(err, LLMBridgeError):
                raise
            raise LLMGenerationError(f"Gemini generation failed: {err}") from err

    async def _generate_groq(
        self,
        system_prompt: str,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Call Groq Cloud API for ultra-fast (500 tokens/sec) inference with automatic model fallback."""
        api_key = getattr(settings, 'GROQ_API_KEY', None) or os.environ.get('GROQ_API_KEY')
        if not api_key:
            raise LLMConfigurationError("Groq API key is missing. Set GROQ_API_KEY in your environment or .env file.")

        groq_aliases = {
            "llama-3.3-70b-versatile": "openai/gpt-oss-120b",
            "llama-3.1-70b-versatile": "openai/gpt-oss-120b",
            "llama-3.1-8b-instant": "openai/gpt-oss-20b",
            "mixtral-8x7b-32768": "qwen/qwen3.8-27b",
            "gemma2-9b-it": "openai/gpt-oss-20b",
            "llama3-70b-8192": "openai/gpt-oss-120b",
            "llama3-8b-8192": "openai/gpt-oss-20b",
        }

        requested_model = model or getattr(settings, 'GROQ_DEFAULT_MODEL', 'openai/gpt-oss-120b')
        model_name = groq_aliases.get(requested_model, requested_model)
        url = "https://api.groq.com/openai/v1/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens or 1024,
            "temperature": 0.1,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code in (400, 404) and model_name != "openai/gpt-oss-120b":
                    logger.warning("Groq model %s failed (%s), falling back to openai/gpt-oss-120b", model_name, resp.status_code)
                    payload["model"] = "openai/gpt-oss-120b"
                    resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as err:
            raise LLMGenerationError(f"Groq API error {err.response.status_code}: {err.response.text}") from err
        except Exception as err:
            if isinstance(err, LLMBridgeError):
                raise
            raise LLMGenerationError(f"Groq generation failed: {err}") from err

    async def _generate_openai(
        self,
        system_prompt: str,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Call OpenAI API for ChatGPT generation."""
        api_key = getattr(settings, 'OPENAI_API_KEY', None) or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise LLMConfigurationError("OpenAI API key is missing. Set OPENAI_API_KEY in your environment or .env file.")

        model_name = model or getattr(settings, 'OPENAI_DEFAULT_MODEL', 'gpt-4o-mini')
        url = "https://api.openai.com/v1/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens or 1024,
            "temperature": 0.7,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as err:
            raise LLMGenerationError(f"OpenAI API error {err.response.status_code}: {err.response.text}") from err
        except Exception as err:
            if isinstance(err, LLMBridgeError):
                raise
            raise LLMGenerationError(f"OpenAI generation failed: {err}") from err

    async def generate(
        self,
        system_prompt: str,
        prompt: str,
        provider: str = "ollama",
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
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
                max_tokens=max_tokens,
            )
        elif provider_normalized == "gemini":
            return await self._generate_gemini(
                system_prompt=system_prompt,
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
            )
        elif provider_normalized == "groq":
            return await self._generate_groq(
                system_prompt=system_prompt,
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
            )
        elif provider_normalized == "openai":
            return await self._generate_openai(
                system_prompt=system_prompt,
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
            )
        elif provider_normalized == "anthropic":
            return await self._generate_anthropic(
                system_prompt=system_prompt,
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
            )
        else:
            raise LLMConfigurationError(
                f"Unknown LLM provider '{provider}'. Must be 'ollama', 'gemini', 'groq', 'openai', or 'anthropic'."
            )

