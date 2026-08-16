"""Offline dataset evaluation and confidence calibration helpers."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .config import load_environment
from .models import Answer, AnswerStatus, BatchAnswer, Question
from .service import QuaestioService


class EvaluationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    question: Question
    language: str = "unknown"
    category: str = "general"
    difficulty: str = "unspecified"
    source: str = "authorized"

    @model_validator(mode="after")
    def require_expected_answer(self) -> "EvaluationItem":
        if self.question.expected_answer is None and self.question.expected_option_index is None:
            raise ValueError("evaluation items require expected_answer or expected_option_index")
        return self


class EvaluationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1)
    items: list[EvaluationItem] = Field(min_length=1, max_length=5000)


class EvaluationRecord(BaseModel):
    id: str
    language: str
    category: str
    difficulty: str
    status: AnswerStatus
    correct: bool | None
    confidence: float = Field(ge=0, le=1)
    method: str
    option_index: int | None = None
    warnings: list[str] = Field(default_factory=list)


class MetricSummary(BaseModel):
    total: int
    evaluated: int
    correct: int
    incorrect: int
    needs_review: int
    failed: int
    accuracy: float | None
    average_confidence: float | None


class ConfidenceBin(BaseModel):
    lower: float
    upper: float
    total: int
    evaluated: int
    correct: int
    accuracy: float | None
    average_confidence: float | None
    overconfidence_gap: float | None


class EvaluationReport(BaseModel):
    dataset_version: str
    summary: MetricSummary
    by_category: dict[str, MetricSummary]
    by_language: dict[str, MetricSummary]
    confidence_bins: list[ConfidenceBin]
    records: list[EvaluationRecord]


def load_dataset(path: str | Path) -> EvaluationDataset:
    """Load a versioned JSONL dataset without accepting unknown fields."""

    source = Path(path)
    items: list[EvaluationItem] = []
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            items.append(EvaluationItem.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"invalid evaluation item at {source}:{line_number}: {exc}") from exc
    if not items:
        raise ValueError(f"evaluation dataset is empty: {source}")
    version = source.stem
    return EvaluationDataset(version=version, items=items)


def evaluate_dataset(dataset: EvaluationDataset, service: QuaestioService | None = None) -> EvaluationReport:
    evaluator = service or QuaestioService()
    answers: list[Answer] = []
    questions = [
        item.question if item.question.id else item.question.model_copy(update={"id": item.id})
        for item in dataset.items
    ]
    for start in range(0, len(questions), 500):
        batch: BatchAnswer = evaluator.solve_batch(questions[start : start + 500])
        answers.extend(batch.answers)

    records = [
        EvaluationRecord(
            id=item.id,
            language=item.language,
            category=item.category,
            difficulty=item.difficulty,
            status=answer.status,
            correct=answer.correct,
            confidence=answer.confidence,
            method=answer.method,
            option_index=answer.option_index,
            warnings=answer.warnings,
        )
        for item, answer in zip(dataset.items, answers, strict=True)
    ]
    return EvaluationReport(
        dataset_version=dataset.version,
        summary=_summarize(records),
        by_category=_grouped_metrics(records, "category"),
        by_language=_grouped_metrics(records, "language"),
        confidence_bins=_confidence_bins(records),
        records=records,
    )


def _summarize(records: list[EvaluationRecord]) -> MetricSummary:
    evaluated = [record for record in records if record.correct is not None]
    correct = sum(record.correct is True for record in evaluated)
    confidence_values = [record.confidence for record in records]
    return MetricSummary(
        total=len(records),
        evaluated=len(evaluated),
        correct=correct,
        incorrect=sum(record.correct is False for record in evaluated),
        needs_review=sum(record.status == AnswerStatus.NEEDS_REVIEW for record in records),
        failed=sum(record.status == AnswerStatus.ERROR for record in records),
        accuracy=correct / len(evaluated) if evaluated else None,
        average_confidence=sum(confidence_values) / len(confidence_values) if confidence_values else None,
    )


def _grouped_metrics(records: list[EvaluationRecord], field: str) -> dict[str, MetricSummary]:
    groups: dict[str, list[EvaluationRecord]] = defaultdict(list)
    for record in records:
        groups[str(getattr(record, field))].append(record)
    return {key: _summarize(value) for key, value in sorted(groups.items())}


def _confidence_bins(records: list[EvaluationRecord]) -> list[ConfidenceBin]:
    bins: list[ConfidenceBin] = []
    for index in range(5):
        lower = index / 5
        upper = (index + 1) / 5
        selected = [
            record for record in records
            if lower <= record.confidence < upper or (index == 4 and record.confidence <= upper)
        ]
        evaluated = [record for record in selected if record.correct is not None]
        correct = sum(record.correct is True for record in evaluated)
        accuracy = correct / len(evaluated) if evaluated else None
        average_confidence = sum(record.confidence for record in selected) / len(selected) if selected else None
        bins.append(ConfidenceBin(
            lower=lower,
            upper=upper,
            total=len(selected),
            evaluated=len(evaluated),
            correct=correct,
            accuracy=accuracy,
            average_confidence=average_confidence,
            overconfidence_gap=(average_confidence - accuracy) if average_confidence is not None and accuracy is not None else None,
        ))
    return bins


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate Quaestio against a versioned JSONL dataset.")
    parser.add_argument("dataset", type=Path, help="path to the evaluation JSONL file")
    parser.add_argument("--output", type=Path, help="optional path for the JSON report")
    args = parser.parse_args(argv)

    load_environment()
    report = evaluate_dataset(load_dataset(args.dataset))
    payload = json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
