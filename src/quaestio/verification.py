from __future__ import annotations

import re

from .models import AnswerStatus, ProposedAnswer, Question, Verification


class AnswerVerifier:
    """Conservative structural verifier; domain verifiers can be added later."""

    def verify(self, question: Question, proposal: ProposedAnswer | None, trusted: bool = False) -> Verification:
        if proposal is None:
            return Verification(
                status=AnswerStatus.NEEDS_REVIEW,
                verified=False,
                warnings=["no solver backend produced a proposal"],
            )

        checks: list[str] = []
        warnings: list[str] = []
        if question.options:
            valid = self._validate_choice(question, proposal)
            if not valid:
                return Verification(
                    status=AnswerStatus.NEEDS_REVIEW,
                    verified=False,
                    checks=checks,
                    warnings=["proposal does not identify one of the supplied options"],
                )
            checks.append("selected option exists in the question")
        elif not proposal.answer.strip():
            return Verification(
                status=AnswerStatus.NEEDS_REVIEW,
                verified=False,
                warnings=["open answer is empty"],
            )
        else:
            checks.append("open answer is non-empty")

        if proposal.explanation and len(proposal.explanation.strip()) >= 10:
            checks.append("explanation is present")
        else:
            warnings.append("explanation is missing or too short")

        return Verification(
            status=AnswerStatus.VERIFIED if trusted else AnswerStatus.ANSWERED,
            verified=trusted,
            checks=checks,
            warnings=warnings,
        )

    def normalize_proposal(self, question: Question, proposal: ProposedAnswer) -> ProposedAnswer:
        """Normalize option letters/text into the canonical zero-based index."""
        if not question.options or proposal.option_index is not None:
            return proposal
        answer = proposal.answer.strip().casefold()
        if len(answer) == 1 and "a" <= answer <= "z":
            index = ord(answer) - ord("a")
            if index < len(question.options):
                return proposal.model_copy(update={
                    "answer": question.options[index],
                    "option_index": index,
                })
        for index, option in enumerate(question.options):
            if re.sub(r"\W+", " ", answer).strip() == re.sub(r"\W+", " ", option.casefold()).strip():
                return proposal.model_copy(update={"option_index": index})
        return proposal

    @staticmethod
    def _validate_choice(question: Question, proposal: ProposedAnswer) -> bool:
        options = question.options or []
        if proposal.option_index is not None:
            if proposal.option_index >= len(options):
                return False
            answer = proposal.answer.strip().casefold()
            option = options[proposal.option_index].casefold()
            label = chr(ord("a") + proposal.option_index)
            if answer not in {option, str(proposal.option_index), label, f"{label})", f"{label}."}:
                # Allow a model to return the option text even if punctuation differs.
                normalized_answer = re.sub(r"\W+", " ", proposal.answer.casefold()).strip()
                normalized_option = re.sub(r"\W+", " ", options[proposal.option_index].casefold()).strip()
                return normalized_answer == normalized_option
            return True

        normalized = re.sub(r"\W+", " ", proposal.answer.casefold()).strip()
        return any(normalized == re.sub(r"\W+", " ", option.casefold()).strip() for option in options)
