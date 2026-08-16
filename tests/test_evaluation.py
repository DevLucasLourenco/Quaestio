from quaestio.backends import SolverOutcome
from quaestio.evaluation import load_dataset, evaluate_dataset
from quaestio.models import ProposedAnswer
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
    assert report.summary.evaluated == 3
    assert report.summary.correct == 1
    assert report.summary.accuracy == 1 / 3
    assert report.by_category["math"].total == 2
    assert len(report.confidence_bins) == 5
