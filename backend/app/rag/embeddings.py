"""Embedding service supporting local Ollama (nomic-embed-text) with OpenAI fallback."""

import logging
import os
from typing import List, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
TARGET_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "768"))


class EmbeddingService:
    """Service to generate vector embeddings using Ollama with optional OpenAI fallback."""

    def __init__(
        self,
        ollama_base_url: Optional[str] = None,
        ollama_model: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        openai_model: Optional[str] = None,
        preferred_provider: Optional[str] = None,
        timeout: int = 30,
    ):
        self.ollama_base_url = (ollama_base_url or DEFAULT_OLLAMA_URL).rstrip("/")
        self.ollama_model = ollama_model or DEFAULT_OLLAMA_MODEL
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openai_model = openai_model or DEFAULT_OPENAI_MODEL
        self.preferred_provider = (
            preferred_provider or os.getenv("EMBEDDING_PROVIDER", "ollama")
        ).lower()
        self.timeout = timeout

    def _embed_ollama(self, text: str) -> List[float]:
        """Generate embedding using Ollama's /api/embeddings endpoint."""
        url = f"{self.ollama_base_url}/api/embeddings"
        payload = {"model": self.ollama_model, "prompt": text}
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if "embedding" not in data:
            raise ValueError(f"Unexpected response format from Ollama: {data}")
        embedding = data["embedding"]
        if len(embedding) != TARGET_DIMENSION:
            raise ValueError(
                f"Expected Ollama embedding dimension {TARGET_DIMENSION}, got {len(embedding)}"
            )
        return embedding

    def _embed_openai(self, text: str) -> List[float]:
        """Generate embedding using OpenAI text-embedding-3-small with target dimension."""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured for fallback embedding.")

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            response = client.embeddings.create(
                model=self.openai_model,
                input=text,
                dimensions=TARGET_DIMENSION,
            )
            embedding = response.data[0].embedding
            if len(embedding) != TARGET_DIMENSION:
                raise ValueError(
                    f"Expected OpenAI embedding dimension {TARGET_DIMENSION}, got {len(embedding)}"
                )
            return embedding
        except Exception as e:
            logger.error("OpenAI embedding generation failed: %s", e)
            raise

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text chunk, handling provider selection and fallback."""
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Cannot generate embedding for empty text.")

        if self.preferred_provider == "openai":
            return self._embed_openai(cleaned_text)

        # Primary: Ollama
        try:
            return self._embed_ollama(cleaned_text)
        except Exception as ollama_err:
            if self.openai_api_key:
                logger.warning(
                    "Ollama embedding failed (%s). Attempting fallback to OpenAI...",
                    ollama_err,
                )
                try:
                    return self._embed_openai(cleaned_text)
                except Exception as openai_err:
                    raise RuntimeError(
                        f"Both Ollama ({ollama_err}) and OpenAI ({openai_err}) failed."
                    ) from openai_err
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Batch generate embeddings for a list of document strings."""
        results: List[List[float]] = []
        for text in texts:
            results.append(self.embed_text(text))
        return results
