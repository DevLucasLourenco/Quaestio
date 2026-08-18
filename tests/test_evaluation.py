from quaestio.backends import SolverOutcome
from quaestio.evaluation import EvaluationRecord, _summarize, load_dataset, evaluate_dataset
from quaestio.models import AnswerStatus, ProposedAnswer
from quaestio.service import QuaestioService


class DatasetBackend:
    name = "dataset_stub"

    def solve(self, question):
        if question.id == "math-001":
            return SolverOutcome(ProposedAnswer(answer="4", option_index=1, confidence=0.9), self.name)
        return SolverOutcome(ProposedAnswer(answer="wrong", confidence=0.6), self.name)


def test_evaluation_dataset_reports_group_and_confidence_metrics():
    dataset = load_dataset("data/evaluation/smoke.jsonl")
    report = evaluate_dataset(dataset, QuaestioService(backend=DatasetBackend()))

    assert report.summary.total == 3
    assert report.summary.evaluated == 2
    assert report.summary.correct == 1
    assert report.summary.incorrect == 1
    assert report.summary.needs_review == 1
    assert report.summary.coverage == 2 / 3
    assert report.summary.accuracy == 1 / 2
    assert report.by_category["math"].total == 2
    assert len(report.confidence_bins) == 5


def test_benchmark_v1_has_thirty_authorized_synthetic_items():
    dataset = load_dataset("data/evaluation/benchmark-v1.jsonl")

    assert len(dataset.items) == 30
    assert all(item.source == "synthetic" for item in dataset.items)
    assert sum(item.category == "math" for item in dataset.items) == 13
    assert sum(item.category == "software_engineering" for item in dataset.items) == 12


def test_needs_review_is_abstention_not_incorrect():
    report = _summarize([
        EvaluationRecord(
            id="review-001",
            language="pt",
            category="math",
            difficulty="easy",
            status=AnswerStatus.NEEDS_REVIEW,
            correct=False,
            confidence=0,
            method="consensus_disagreement",
        ),
    ])

    assert report.evaluated == 0
    assert report.incorrect == 0
    assert report.needs_review == 1
    assert report.coverage == 0
    assert report.accuracy is None
