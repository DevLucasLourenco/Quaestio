from dataclasses import dataclass, field

from quaestio.backends import CompositeBackend, ConsensusBackend, TranslatedSolverBackend
from quaestio.models import Attachment, ProposedAnswer, Question, TranslationStatus
from quaestio.service import QuaestioService
from quaestio.translation import QuestionPreparer


@dataclass
class FakeTranslator:
    name: str = "fake_translator"
    translate_calls: int = 0
    translated_questions: list[Question] = field(default_factory=list)

    def translate_question(self, question, source_language, target_language):
        self.translate_calls += 1
        translated = question.model_copy(update={
            "question": "Which option is correct?",
            "context": "Translated context",
            "options": ["Translated A", "Translated B"],
            "subject": "history",
            "topic": "modern history",
        })
        self.translated_questions.append(translated)
        return translated

    def localize_proposal(self, question, proposal, source_language, working_language):
        answer = question.options[proposal.option_index] if proposal.option_index is not None else "Resposta aberta"
        return proposal.model_copy(update={
            "answer": answer,
            "explanation": "Explicação localizada da resposta.",
        }), ()


@dataclass
class RecordingBackend:
    name: str
    questions: list[Question] = field(default_factory=list)

    def solve(self, question):
        self.questions.append(question)
        return ProposedAnswer(answer="Translated B", option_index=1, explanation="Translated explanation.")


@dataclass
class FakeOcrResult:
    text: str
    warnings: list[str] = field(default_factory=list)


class FakeOcr:
    executable = "fake-tesseract"

    def extract(self, attachment, language="por+eng"):
        return FakeOcrResult("Texto visível na imagem.")


def test_question_preparer_preserves_original_and_attachments():
    original = Question(
        question="Qual alternativa está correta?",
        options=["A", "B"],
        attachments=[Attachment(mime_type="image/png", data_base64="aW1hZ2U=")],
    )
    translator = FakeTranslator()
    prepared = QuestionPreparer(translator).prepare(original)

    assert prepared.status == TranslationStatus.TRANSLATED
    assert prepared.original_question.question == "Qual alternativa está correta?"
    assert prepared.working_question.question == "Which option is correct?"
    assert prepared.working_question.options == ["Translated A", "Translated B"]
    assert prepared.working_question.attachments == original.attachments
    assert prepared.working_question.expected_answer == original.expected_answer


def test_translated_consensus_shares_one_working_question_and_localizes_answer():
    translator = FakeTranslator()
    first = RecordingBackend("first")
    second = RecordingBackend("second")
    backend = CompositeBackend(TranslatedSolverBackend(
        backend=ConsensusBackend(first, second),
        preparer=QuestionPreparer(translator),
        translator=translator,
    ))

    result = QuaestioService(backend=backend).solve(Question(
        question="Qual alternativa está correta?",
        options=["A original", "B original"],
    ))

    assert translator.translate_calls == 1
    assert len(first.questions) == 1 and len(second.questions) == 1
    assert first.questions[0] == second.questions[0]
    assert first.questions[0].question == "Which option is correct?"
    assert result.option_index == 1
    assert result.answer == "B original"
    assert result.explanation == "Explicação localizada da resposta."
    assert result.method == "consensus"
    assert "question_translation" in [step.stage for step in result.trace]
    assert "answer_localization" in [step.stage for step in result.trace]


def test_required_translation_without_backend_fails_closed():
    backend = CompositeBackend(TranslatedSolverBackend(
        backend=RecordingBackend("solver"),
        preparer=QuestionPreparer(None, mode="required"),
        translator=None,
    ))

    result = QuaestioService(backend=backend).solve(Question(
        question="Qual alternativa está correta?",
        options=["A", "B"],
    ))

    assert result.status.value == "needs_review"
    assert result.method == "translation_required"
    assert "question_translation" in [step.stage for step in result.trace]


def test_english_question_skips_translation():
    translator = FakeTranslator()
    prepared = QuestionPreparer(translator).prepare(Question(
        question="Which option is correct?",
        options=["A", "B"],
    ))

    assert prepared.status == TranslationStatus.SKIPPED
    assert translator.translate_calls == 0


def test_ocr_is_added_as_auxiliary_context_without_changing_image():
    original = Question(
        question="Qual alternativa está correta?",
        attachments=[Attachment(mime_type="image/png", data_base64="aW1hZ2U=")],
    )
    prepared = QuestionPreparer(FakeTranslator(), ocr=FakeOcr()).prepare(original)

    assert "Visual OCR (untrusted auxiliary text)" in prepared.working_question.context
    assert prepared.working_question.attachments == original.attachments
    assert original.context is None
