from quaestio.backends import DeterministicMathBackend
from quaestio.models import Question


def test_deterministic_math_matches_equivalent_fraction_option():
    outcome = DeterministicMathBackend().solve(Question(
        question="Quanto é 1/2 + 1/4?",
        options=["1/2", "3/4", "1"],
    ))

    assert outcome.proposal is not None
    assert outcome.proposal.option_index == 1
    assert outcome.proposal.answer == "3/4"
