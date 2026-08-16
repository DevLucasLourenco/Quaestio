import pytest
from pydantic import ValidationError

from quaestio.models import Question, QuestionType


def test_question_type_is_inferred_from_options():
    assert Question(question="2 + 2 = ?", options=["3", "4"]).question_type == QuestionType.MULTIPLE_CHOICE
    assert Question(question="Explique a inércia.").question_type == QuestionType.OPEN


def test_invalid_options_are_rejected():
    with pytest.raises(ValidationError):
        Question(question="Escolha", options=["A"])
    with pytest.raises(ValidationError):
        Question(question="Escolha", options=["A", "A"])
