from dataclasses import dataclass
from pathlib import Path

from quaestio.knowledge import KnowledgeBase
from quaestio.models import ProposedAnswer, Question
from quaestio.service import QuaestioService


class FakeEmbeddingProvider:
    model = "fake"

    def __init__(self):
        self.calls = []

    def embed(self, text, input_type="query"):
        self.calls.append((text, input_type))
        return [1.0, 0.0] if "tcp" in text.casefold() or "transporte" in text.casefold() else [0.0, 1.0]


def test_knowledge_base_returns_relevant_material_and_source():
    knowledge = KnowledgeBase()
    knowledge.add_document("aula-7", "Aula 7", "TCP estabelece uma conexão confiável e ordenada.", "Aula_07.pdf")
    knowledge.add_document("aula-1", "Aula 1", "Introdução a redes de computadores.", "Aula_01.pdf")
    hits = knowledge.search("Como funciona o TCP?", top_k=1)
    assert hits[0].source == "Aula_07.pdf"
    assert "conexão" in hits[0].snippet
    assert 0 < hits[0].score <= 1


def test_tfidf_ranking_prefers_document_with_more_query_evidence():
    knowledge = KnowledgeBase()
    knowledge.add_document("weak", "Notas", "TCP é um protocolo.", "weak.pdf")
    knowledge.add_document("strong", "Aula TCP", "TCP estabelece conexão confiável e entrega ordenada.", "strong.pdf")
    hits = knowledge.search("TCP conexão confiável", top_k=2)
    assert hits[0].source == "strong.pdf"
    assert hits[0].score > hits[1].score


def test_embeddings_can_retrieve_without_lexical_overlap():
    provider = FakeEmbeddingProvider()
    knowledge = KnowledgeBase(embedding_provider=provider)
    knowledge.add_document("tcp", "Redes", "TCP estabelece uma conexão.", "tcp.pdf")
    knowledge.add_document("other", "História", "Um evento histórico.", "historia.pdf")
    hits = knowledge.search("transporte seguro", top_k=1)
    assert hits[0].source == "tcp.pdf"
    assert hits[0].score == 1.0
    assert [input_type for _, input_type in provider.calls] == ["passage", "passage", "query"]


@dataclass
class ContextBackend:
    name: str = "context_stub"
    seen_context: str = ""

    def solve(self, question: Question):
        self.seen_context = question.context or ""
        return ProposedAnswer(answer="B", option_index=1, explanation="Resposta baseada no material.")


def test_service_injects_retrieved_material_and_returns_sources():
    knowledge = KnowledgeBase()
    knowledge.add_document("d1", "Redes", "TCP é orientado à conexão.", "redes.pdf")
    backend = ContextBackend()
    result = QuaestioService(backend=backend, knowledge_base=knowledge).solve(
        Question(question="Segundo o material, o TCP é orientado à conexão?", options=["A", "B"])
    )
    assert "TCP" in backend.seen_context
    assert result.sources == ["redes.pdf"]


def test_knowledge_base_can_persist_and_reload():
    path = Path("tests") / "_knowledge_test.json"
    try:
        first = KnowledgeBase(path)
        first.add_document("d1", "Aula", "Conteúdo sobre álgebra.", "aula.pdf")
        second = KnowledgeBase(path)
        assert second.search("álgebra")[0].source == "aula.pdf"
    finally:
        path.unlink(missing_ok=True)


def test_embedding_index_persists_model_metadata():
    path = Path("tests") / "_embedding_test.json"
    try:
        provider = FakeEmbeddingProvider()
        first = KnowledgeBase(path, embedding_provider=provider)
        first.add_document("d1", "Aula", "Conteúdo sobre redes.", "aula.pdf")
        payload = path.read_text(encoding="utf-8")
        assert '"format_version": 2' in payload
        assert '"embedding_model": "fake"' in payload
    finally:
        path.unlink(missing_ok=True)
