from __future__ import annotations

import re
import json
import os
import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .embeddings import EmbeddingProvider, configured_embedding_provider


@dataclass(frozen=True)
class KnowledgeHit:
    document_id: str
    title: str
    source: str
    snippet: str
    score: float


@dataclass
class _Document:
    document_id: str
    title: str
    content: str
    source: str
    tokens: set[str] = field(default_factory=set)
    term_counts: Counter[str] = field(default_factory=Counter)
    embedding: list[float] | None = None
    embedding_model: str | None = None


class KnowledgeBase:
    """Local TF-IDF vector retrieval with source-aware snippets."""

    def __init__(self, storage_path: str | Path | None = None, embedding_provider: EmbeddingProvider | None = None) -> None:
        self._documents: dict[str, _Document] = {}
        self.storage_path = Path(storage_path) if storage_path else None
        self.embedding_provider = embedding_provider if embedding_provider is not None else configured_embedding_provider()
        self._load()

    def add_document(
        self,
        document_id: str,
        title: str,
        content: str,
        source: str | None = None,
        embedding: list[float] | None = None,
        embedding_model: str | None = None,
    ) -> dict[str, str]:
        if not document_id.strip() or not title.strip() or not content.strip():
            raise ValueError("document_id, title and content are required")
        document = _Document(
            document_id=document_id.strip(),
            title=title.strip(),
            content=content.strip(),
            source=(source or title).strip(),
        )
        document.term_counts = self._term_counts(f"{document.title} {document.content}")
        document.tokens = set(document.term_counts)
        if embedding is not None:
            document.embedding = [float(value) for value in embedding]
            document.embedding_model = embedding_model or getattr(self.embedding_provider, "model", None)
        elif self.embedding_provider is not None:
            document.embedding = self._embed(f"{document.title}\n{document.content}", "passage")
            document.embedding_model = self.embedding_provider.model if document.embedding is not None else None
        self._documents[document.document_id] = document
        self._persist()
        return {"document_id": document.document_id, "title": document.title, "source": document.source}

    def search(self, query: str, top_k: int = 5) -> list[KnowledgeHit]:
        if top_k < 1 or top_k > 20:
            raise ValueError("top_k must be between 1 and 20")
        query_counts = self._term_counts(query)
        query_tokens = set(query_counts)
        query_embedding = self._embed(query, "query") if self.embedding_provider is not None else None
        if not query_tokens and query_embedding is None:
            return []
        document_frequency = Counter(
            term
            for document in self._documents.values()
            for term in document.tokens
        )
        document_count = len(self._documents)
        query_vector = self._tfidf_vector(query_counts, document_frequency, document_count)
        hits: list[KnowledgeHit] = []
        for document in self._documents.values():
            overlap = query_tokens & document.tokens
            has_embedding_pair = (
                query_embedding is not None
                and document.embedding is not None
                and document.embedding_model == getattr(self.embedding_provider, "model", None)
                and len(query_embedding) == len(document.embedding)
            )
            if not overlap and not has_embedding_pair:
                continue
            if has_embedding_pair:
                score = self._cosine_lists(query_embedding, document.embedding)
            else:
                document_vector = self._tfidf_vector(document.term_counts, document_frequency, document_count)
                score = self._cosine(query_vector, document_vector)
            hits.append(KnowledgeHit(
                document_id=document.document_id,
                title=document.title,
                source=document.source,
                snippet=self._snippet(document.content, overlap),
                score=round(score, 4),
            ))
        return sorted(hits, key=lambda hit: (-hit.score, hit.title))[:top_k]

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[0-9a-zA-ZÀ-ÿ]+", text.casefold()))

    @classmethod
    def _term_counts(cls, text: str) -> Counter[str]:
        return Counter(re.findall(r"[0-9a-zA-ZÀ-ÿ]+", text.casefold()))

    @staticmethod
    def _tfidf_vector(term_counts: Counter[str], document_frequency: Counter[str], document_count: int) -> dict[str, float]:
        total = sum(term_counts.values()) or 1
        vector: dict[str, float] = {}
        for term, count in term_counts.items():
            frequency = count / total
            inverse_frequency = math.log((1 + document_count) / (1 + document_frequency[term])) + 1
            vector[term] = frequency * inverse_frequency
        return vector

    @staticmethod
    def _cosine(first: dict[str, float], second: dict[str, float]) -> float:
        dot = sum(first.get(term, 0.0) * weight for term, weight in second.items())
        first_norm = math.sqrt(sum(weight * weight for weight in first.values()))
        second_norm = math.sqrt(sum(weight * weight for weight in second.values()))
        if not first_norm or not second_norm:
            return 0.0
        return min(1.0, max(0.0, dot / (first_norm * second_norm)))

    @staticmethod
    def _cosine_lists(first: list[float], second: list[float]) -> float:
        dot = sum(left * right for left, right in zip(first, second))
        first_norm = math.sqrt(sum(value * value for value in first))
        second_norm = math.sqrt(sum(value * value for value in second))
        if not first_norm or not second_norm:
            return 0.0
        return min(1.0, max(0.0, dot / (first_norm * second_norm)))

    @staticmethod
    def _snippet(content: str, terms: set[str]) -> str:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n|\r?\n", content) if part.strip()]
        if not paragraphs:
            return content[:500]
        ranked = sorted(
            paragraphs,
            key=lambda paragraph: len(KnowledgeBase._tokens(paragraph) & terms),
            reverse=True,
        )
        return ranked[0][:500]

    def _load(self) -> None:
        if self.storage_path is None or not self.storage_path.exists():
            return
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
            documents = payload.get("documents", []) if isinstance(payload, dict) else payload
            for item in documents:
                stored_model = item.get("embedding_model")
                stored_embedding = item.get("embedding")
                if self.embedding_provider is not None and stored_model != self.embedding_provider.model:
                    stored_embedding = None
                self.add_document(
                    document_id=item["document_id"],
                    title=item["title"],
                    content=item["content"],
                    source=item.get("source"),
                    embedding=stored_embedding,
                    embedding_model=stored_model,
                )
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            # A corrupt optional index must not prevent the MCP from starting.
            self._documents = {}

    def _persist(self) -> None:
        if self.storage_path is None:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format_version": 2,
            "embedding_model": getattr(self.embedding_provider, "model", None),
            "embedding_dimensions": self._embedding_dimensions(),
            "documents": [
                {
                    "document_id": document.document_id,
                    "title": document.title,
                    "content": document.content,
                    "source": document.source,
                    "embedding": document.embedding,
                    "embedding_model": document.embedding_model,
                }
                for document in self._documents.values()
            ],
        }
        temporary = self.storage_path.with_suffix(self.storage_path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.storage_path)

    def _embed(self, text: str, input_type: str) -> list[float] | None:
        """Call current and legacy provider implementations safely."""

        if self.embedding_provider is None:
            return None
        try:
            return self.embedding_provider.embed(text, input_type=input_type)
        except TypeError as exc:
            if "input_type" not in str(exc):
                raise
            return self.embedding_provider.embed(text)

    def _embedding_dimensions(self) -> int | None:
        dimensions = {
            len(document.embedding)
            for document in self._documents.values()
            if document.embedding is not None
        }
        return dimensions.pop() if len(dimensions) == 1 else None
