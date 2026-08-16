from quaestio.models import AnswerStatus, ProposedAnswer, Question
from quaestio.verification import AnswerVerifier


def test_verifier_accepts_existing_option_but_does_not_claim_verified():
    question = Question(question="Capital do Brasil?", options=["Brasília", "São Paulo"])
    result = AnswerVerifier().verify(question, ProposedAnswer(answer="Brasília", option_index=0, explanation="A capital federal é Brasília."))
    assert result.status == AnswerStatus.ANSWERED
    assert result.verified is False
    assert "selected option exists in the question" in result.checks


def test_trusted_verification_can_mark_a_deterministic_result():
    question = Question(question="Escolha", options=["A", "B"])
    result = AnswerVerifier().verify(
        question,
        ProposedAnswer(answer="B", option_index=1, explanation="A alternativa B."),
        trusted=True,
    )
    assert result.status == AnswerStatus.VERIFIED
    assert result.verified is True


def test_verifier_accepts_letter_for_indexed_option():
    question = Question(question="Escolha", options=["Primeira", "Segunda"])
    result = AnswerVerifier().verify(
        question,
        ProposedAnswer(answer="B", option_index=1),
    )
    assert result.status == AnswerStatus.ANSWERED


def test_verifier_normalizes_unindexed_letter():
    question = Question(question="Escolha", options=["Primeira", "Segunda"])
    proposal = AnswerVerifier().normalize_proposal(question, ProposedAnswer(answer="B"))
    assert proposal.answer == "Segunda"
    assert proposal.option_index == 1


def test_verifier_rejects_option_outside_question():
    question = Question(question="Escolha", options=["A", "B"])
    result = AnswerVerifier().verify(question, ProposedAnswer(answer="C", option_index=2))
    assert result.status == AnswerStatus.NEEDS_REVIEW
    assert result.verified is False


def test_verifier_handles_missing_proposal_conservatively():
    result = AnswerVerifier().verify(Question(question="Pergunta"), None)
    assert result.status == AnswerStatus.NEEDS_REVIEW
    assert result.verified is False
