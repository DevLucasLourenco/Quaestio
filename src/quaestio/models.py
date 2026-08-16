from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QuestionType(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    OPEN = "open"
    UNKNOWN = "unknown"


class Classification(BaseModel):
    question_type: QuestionType
    subject: str
    topic: str
    confidence: float = Field(ge=0, le=1)
    signals: list[str] = Field(default_factory=list)


class KnowledgeSearchHit(BaseModel):
    document_id: str
    title: str
    source: str
    snippet: str
    score: float = Field(ge=0, le=1)


class ExtractionResult(BaseModel):
    questions: list[Question] = Field(default_factory=list)
    method: str
    warnings: list[str] = Field(default_factory=list)


class AnswerStatus(StrEnum):
    VERIFIED = "verified"
    ANSWERED = "answered"
    NEEDS_REVIEW = "needs_review"
    ERROR = "error"


class SemanticStatus(StrEnum):
    NOT_CONFIGURED = "not_configured"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    UNCERTAIN = "uncertain"


class SemanticCheck(BaseModel):
    status: SemanticStatus = SemanticStatus.NOT_CONFIGURED
    confidence: float = Field(default=0, ge=0, le=1)
    reason: str | None = None


class TraceStep(BaseModel):
    stage: str
    status: str
    detail: str


class TranslationStatus(StrEnum):
    SKIPPED = "skipped"
    TRANSLATED = "translated"
    FAILED = "failed"


class PreparedQuestion(BaseModel):
    """Original question plus the language-specific solver representation."""

    original_question: Question
    working_question: Question
    source_language: str
    target_language: str
    status: TranslationStatus
    confidence: float = Field(default=1.0, ge=0, le=1)
    translated_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Attachment(BaseModel):
    """An optional inline attachment, normally an image or a document."""

    model_config = ConfigDict(extra="forbid")

    mime_type: str = Field(min_length=1)
    data_base64: str | None = None
    uri: str | None = None

    @field_validator("data_base64", "uri")
    @classmethod
    def non_empty_if_present(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("attachment references cannot be empty")
        return value


class Question(BaseModel):
    """Canonical question contract shared by all future clients."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    question: str = Field(min_length=1)
    options: list[str] | None = None
    context: str | None = None
    attachments: list[Attachment] = Field(default_factory=list)
    subject: str | None = None
    topic: str | None = None
    expected_answer: str | None = None
    expected_option_index: int | None = Field(default=None, ge=0)

    @field_validator("question", "context", "subject", "topic")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @field_validator("options")
    @classmethod
    def validate_options(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [item.strip() for item in value]
        if len(cleaned) < 2:
            raise ValueError("multiple-choice questions need at least two options")
        if any(not item for item in cleaned):
            raise ValueError("options cannot be empty")
        if len(set(item.casefold() for item in cleaned)) != len(cleaned):
            raise ValueError("options must be unique")
        return cleaned

    @property
    def question_type(self) -> QuestionType:
        return QuestionType.MULTIPLE_CHOICE if self.options else QuestionType.OPEN


class Verification(BaseModel):
    status: AnswerStatus
    verified: bool
    checks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    semantic: SemanticCheck = Field(default_factory=SemanticCheck)


class Answer(BaseModel):
    question_id: str | None = None
    question_type: QuestionType
    subject: str | None = None
    topic: str | None = None
    answer: str | None = None
    option_index: int | None = Field(default=None, ge=0)
    explanation: str | None = None
    confidence: float = Field(ge=0, le=1)
    status: AnswerStatus
    method: str
    verification: Verification
    sources: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    correct: bool | None = None
    trace: list[TraceStep] = Field(default_factory=list)


class BatchAnswer(BaseModel):
    answers: list[Answer]
    total: int
    verified: int
    needs_review: int
    failed: int
    evaluated: int
    correct: int
    accuracy: float | None = Field(default=None, ge=0, le=1)


class ProposedAnswer(BaseModel):
    answer: str = Field(min_length=1)
    option_index: int | None = Field(default=None, ge=0)
    explanation: str | None = None
    confidence: float = Field(default=0.5, ge=0, le=1)


def as_jsonable(value: Any) -> Any:
    """Convert public Pydantic results to values accepted by MCP serializers."""

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value
