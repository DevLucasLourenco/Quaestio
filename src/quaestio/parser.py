from __future__ import annotations

import re

from .models import Question


class QuestionParser:
    """Parse common plain-text exam layouts into the canonical Question model."""

    _question = re.compile(
        r"(?ms)^\s*(?P<number>\d+)\s*[).:\-]\s*(?P<body>.*?)(?=^\s*\d+\s*[).:\-]|\Z)"
    )
    _option = re.compile(r"^\s*(?P<label>[A-Ha-h])\s*[).:\-]\s*(?P<text>.*)$")

    def parse(self, text: str) -> tuple[list[Question], list[str]]:
        if not text.strip():
            raise ValueError("text cannot be empty")
        matches = list(self._question.finditer(text))
        warnings: list[str] = []
        if not matches:
            warnings.append("no numbered question headers detected; treating the text as one question")
            return [Question(question=text.strip())], warnings

        questions: list[Question] = []
        for match in matches:
            question_id = match.group("number")
            question_text, options = self._parse_block(match.group("body"))
            if not question_text:
                warnings.append(f"question {question_id} has no statement")
                continue
            questions.append(Question(
                id=question_id,
                question=question_text,
                options=options if len(options) >= 2 else None,
            ))
            if len(options) == 1:
                warnings.append(f"question {question_id} has only one detected option; treated as open")
        return questions, warnings

    def _parse_block(self, block: str) -> tuple[str, list[str]]:
        statement: list[str] = []
        options: list[str] = []
        current_option: int | None = None
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            option_match = self._option.match(line)
            if option_match:
                options.append(option_match.group("text").strip())
                current_option = len(options) - 1
                continue
            if current_option is None:
                statement.append(line)
            else:
                options[current_option] = f"{options[current_option]} {line}".strip()
        return " ".join(statement).strip(), options
