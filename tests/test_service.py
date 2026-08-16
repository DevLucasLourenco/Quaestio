from dataclasses import dataclass
from time import sleep

from quaestio.models import ProposedAnswer, Question, AnswerStatus, SemanticCheck, SemanticStatus
from quaestio.backends import ConsensusBackend, SolverOutcome
from quaestio.service import QuaestioService


@dataclass
class StubBackend:
    name: str = "stub"

    def solve(self, question: Question):
        return ProposedAnswer(answer="B", option_index=1, explanation="A alternativa B corresponde ao enunciado.")


def test_service_solves_batch_and_keeps_ids():
    result = QuaestioService(backend=StubBackend()).solve_batch([
        Question(id="q1", question="Uma pergunta", options=["A", "B"]),
        Question(id="q2", question="Outra pergunta", options=["A", "B"]),
    ])
    assert result.total == 2
    assert [item.question_id for item in result.answers] == ["q1", "q2"]
    assert all(item.status == AnswerStatus.ANSWERED for item in result.answers)


def test_service_returns_needs_review_without_backend():
    class EmptyBackend:
        name = "empty"

        def solve(self, question):
            return None

    result = QuaestioService(backend=EmptyBackend()).solve(Question(question="Pergunta"))
    assert result.status == AnswerStatus.NEEDS_REVIEW
    assert result.confidence == 0


def test_deterministic_math_is_verified():
    result = QuaestioService().solve(Question(
        question="Calcule: 2 + 2",
        options=["3", "4", "5"],
    ))
    assert result.answer == "4"
    assert result.option_index == 1
    assert result.status == AnswerStatus.VERIFIED
    assert result.method == "deterministic_math"
    assert result.verification.verified is True


def test_service_classifies_before_solving():
    result = QuaestioService().solve(Question(question="Calcule a derivada desta função."))
    assert result.subject == "mathematics"
    assert result.topic == "calculus"


class FixedBackend:
    def __init__(self, answer: str, option_index: int):
        self.answer = answer
        self.option_index = option_index
        self.name = answer

    def solve(self, question):
        return ProposedAnswer(answer=self.answer, option_index=self.option_index, explanation="Evidência independente.", confidence=0.8)


def test_consensus_returns_proposal_when_backends_agree():
    backend = ConsensusBackend(FixedBackend("B", 1), FixedBackend("B", 1))
    result = backend.solve(Question(question="Escolha", options=["A", "B"]))
    assert result.proposal is not None
    assert result.proposal.option_index == 1
    assert result.method == "consensus"


def test_consensus_refuses_disagreement():
    backend = ConsensusBackend(FixedBackend("A", 0), FixedBackend("B", 1))
    result = backend.solve(Question(question="Escolha", options=["A", "B"]))
    assert result.proposal is None
    assert result.method == "consensus_disagreement"
    assert result.warnings


def test_parallel_batch_keeps_per_question_backend_metadata():
    class PerQuestionBackend:
        name = "per_question"

        def solve(self, question):
            sleep(0.01 if question.id == "slow" else 0)
            return SolverOutcome(
                ProposedAnswer(answer="A", option_index=0, explanation="Resposta."),
                method=f"backend-{question.id}",
            )

    result = QuaestioService(backend=PerQuestionBackend()).solve_batch([
        Question(id="slow", question="Uma", options=["A", "B"]),
        Question(id="fast", question="Duas", options=["A", "B"]),
    ])
    assert [answer.method for answer in result.answers] == ["backend-slow", "backend-fast"]


def test_batch_evaluation_calculates_accuracy_without_changing_solver_input():
    result = QuaestioService().solve_batch([
        Question(id="q1", question="Calcule: 2 + 2", options=["3", "4"], expected_answer="B"),
        Question(id="q2", question="Calcule: 3 + 3", options=["5", "6"], expected_option_index=0),
    ])
    assert result.evaluated == 2
    assert result.correct == 1
    assert result.accuracy == 0.5
    assert [answer.correct for answer in result.answers] == [True, False]


def test_unverified_model_confidence_is_capped():
    class OverconfidentBackend:
        name = "model"

        def solve(self, question):
            return ProposedAnswer(answer="A", option_index=0, explanation="Uma resposta.", confidence=1.0)

    result = QuaestioService(backend=OverconfidentBackend()).solve(
        Question(question="Escolha", options=["A", "B"])
    )
    assert result.status == AnswerStatus.ANSWERED
    assert result.confidence == 0.65


class SupportingSemanticVerifier:
    def verify(self, question, proposal):
        return SemanticCheck(status=SemanticStatus.SUPPORTS, confidence=0.9, reason="evidência coerente")


class ContradictingSemanticVerifier:
    def verify(self, question, proposal):
        return SemanticCheck(status=SemanticStatus.CONTRADICTS, confidence=0.95, reason="alternativa incompatível")


def test_semantic_support_is_recorded_without_becoming_deterministic_proof():
    class HighConfidenceBackend:
        name = "model"

        def solve(self, question):
            return ProposedAnswer(answer="B", option_index=1, explanation="Resposta independente.", confidence=1.0)

    result = QuaestioService(
        backend=HighConfidenceBackend(),
        semantic_verifier=SupportingSemanticVerifier(),
    ).solve(Question(question="Escolha", options=["A", "B"]))
    assert result.status == AnswerStatus.ANSWERED
    assert result.verification.semantic.status == SemanticStatus.SUPPORTS
    assert "independent semantic verifier supports" in result.verification.checks[-1]
    assert result.confidence == 0.75


def test_semantic_contradiction_forces_review():
    result = QuaestioService(
        backend=StubBackend(),
        semantic_verifier=ContradictingSemanticVerifier(),
    ).solve(Question(question="Escolha", options=["A", "B"]))
    assert result.status == AnswerStatus.NEEDS_REVIEW
    assert result.confidence == 0
    assert result.verification.semantic.status == SemanticStatus.CONTRADICTS


def test_answer_contains_audit_trace_for_resolution_and_evaluation():
    result = QuaestioService().solve(Question(
        id="trace-1",
        question="Calcule: 2 + 2",
        options=["3", "4"],
        expected_answer="B",
    ))
    stages = [step.stage for step in result.trace]
    assert stages[:4] == ["classification", "material_retrieval", "solver", "semantic_verification"]
    assert "structural_verification" in stages
    assert stages[-1] == "expected_answer_evaluation"
    assert result.correct is True


def test_symbolic_math_backend_is_optional_and_safe():
    result = QuaestioService().solve(Question(question="Resolva x^2 - 5x + 6 = 0"))
    # SymPy is an optional extra in the development environment.
    if result.method == "symbolic_math":
        assert result.status == AnswerStatus.VERIFIED
        assert "x = 2" in result.answer and "x = 3" in result.answer
    else:
        assert result.status.name in {"NEEDS_REVIEW", "ERROR"}
