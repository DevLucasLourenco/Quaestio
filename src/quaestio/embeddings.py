from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Protocol


class EmbeddingProvider(Protocol):
    model: str

    def embed(self, text: str) -> list[float] | None:
        """Return a vector or None when semantic retrieval is unavailable."""


class OpenAICompatibleEmbeddingProvider:
    def __init__(self, base_url: str, api_key: str, model: str, timeout_seconds: float = 30) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def embed(self, text: str) -> list[float] | None:
        payload = {"model": self.model, "input": text}
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/embeddings",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
            vector = body["data"][0]["embedding"]
            if not isinstance(vector, list) or not vector or not all(isinstance(value, (int, float)) for value in vector):
                return None
            return [float(value) for value in vector]
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
            return None


def configured_embedding_provider() -> EmbeddingProvider | None:
    base_url = os.getenv("QUAESTIO_EMBEDDING_BASE_URL")
    api_key = os.getenv("QUAESTIO_EMBEDDING_API_KEY")
    model = os.getenv("QUAESTIO_EMBEDDING_MODEL")
    if not (base_url and api_key and model):
        return None
    return OpenAICompatibleEmbeddingProvider(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=float(os.getenv("QUAESTIO_EMBEDDING_TIMEOUT_SECONDS", "30")),
    )
