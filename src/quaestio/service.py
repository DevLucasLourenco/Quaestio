from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
import re

from .backends import SolverBackend, SolverOutcome, configured_backend
from .classifier import QuestionClassifier
from .knowledge import KnowledgeBase
from .models import Answer, AnswerStatus, BatchAnswer, Classification, KnowledgeSearchHit, ProposedAnswer, Question, TraceStep
from .models import SemanticCheck, SemanticStatus
from .semantic_verifier import SemanticVerifier, configured_semantic_verifier
from .verification import AnswerVerifier


class QuaestioService:
    def __init__(self, backend: SolverBackend | None = None, verifier: AnswerVerifier | None = None, classifier: QuestionClassifier | None = None, knowledge_base: KnowledgeBase | None = None, semantic_verifier: SemanticVerifier | None = None) -> None:
        self.backend = backend or configured_backend()
        self.verifier = verifier or AnswerVerifier()
        self.classifier = classifier or QuestionClassifier()
        self.knowledge_base = knowledge_base or KnowledgeBase(os.getenv("QUAESTIO_KNOWLEDGE_BASE_PATH"))
        self.semantic_verifier = semantic_verifier if semantic_verifier is not None else configured_semantic_verifier()

    def solve(self, question: Question) -> Answer:
        trace: list[TraceStep] = []
        try:
            classification = self.classifier.classify(question)
            trace.append(TraceStep(stage="classification", status="completed", detail=f"{classification.subject}/{classification.topic}"))
            if not question.subject or not question.topic:
                question = question.model_copy(update={
                    "subject": question.subject or classification.subject,
                    "topic": question.topic or classification.topic,
                })
            hits = self.knowledge_base.search(question.question, top_k=3)
            sources = [hit.source for hit in hits]
            trace.append(TraceStep(
                stage="material_retrieval",
                status="completed" if hits else "skipped",
                detail=f"{len(hits)} relevant source(s) retrieved",
            ))
            if hits:
                evidence = "\n\n".join(f"[{hit.source}] {hit.snippet}" for hit in hits)
                question = question.model_copy(update={
                    "context": f"{question.context or ''}\n\nRelevant study material:\n{evidence}".strip(),
                })
            raw_outcome = self.backend.solve(question)
            outcome = raw_outcome if isinstance(raw_outcome, SolverOutcome) else SolverOutcome(
                proposal=raw_outcome,
                method=str(getattr(self.backend, "name", type(self.backend).__name__)),
            )
            proposal = outcome.proposal
            if proposal is not None:
                proposal = self.verifier.normalize_proposal(question, proposal)
            trusted = outcome.trusted
            method = outcome.method
            trace.extend(outcome.trace)
            trace.append(TraceStep(
                stage="solver",
                status="completed" if proposal is not None else "needs_review",
                detail=method,
            ))
            verification = self.verifier.verify(question, proposal, trusted=trusted)
            if proposal is not None and not verification.verified and self.semantic_verifier is not None:
                semantic = self.semantic_verifier.verify(question, proposal)
                verification = self._merge_semantic_verification(verification, semantic)
                trace.append(TraceStep(stage="semantic_verification", status=semantic.status.value, detail=semantic.reason or "semantic review completed"))
            else:
                trace.append(TraceStep(
                    stage="semantic_verification",
                    status="deterministic" if verification.verified else "not_configured",
                    detail="semantic review skipped for deterministic evidence or missing verifier",
                ))
            trace.append(TraceStep(
                stage="structural_verification",
                status=verification.status.value,
                detail="; ".join(verification.checks) or "; ".join(verification.warnings) or "no structural evidence",
            ))
            if proposal is None:
                return self._evaluate_answer(question, Answer(
                    question_id=question.id,
                    question_type=question.question_type,
                    subject=classification.subject,
                    topic=classification.topic,
                    sources=sources,
                    confidence=0,
                    status=AnswerStatus.NEEDS_REVIEW,
                    method=method,
                    verification=verification,
                    warnings=verification.warnings + list(outcome.warnings),
                    trace=trace,
                ))

            status = verification.status
            confidence = self._calibrate_confidence(proposal, outcome, verification)
            return self._evaluate_answer(question, Answer(
                question_id=question.id,
                question_type=question.question_type,
                subject=classification.subject,
                topic=classification.topic,
                sources=sources,
                answer=proposal.answer,
                option_index=proposal.option_index,
                explanation=proposal.explanation,
                confidence=confidence,
                status=status,
                method=method,
                verification=verification,
                warnings=verification.warnings + list(outcome.warnings),
                trace=trace,
            ))
        except Exception as exc:  # the MCP boundary must return a structured failure
            verification = self.verifier.verify(question, None)
            return self._evaluate_answer(question, Answer(
                question_id=question.id,
                question_type=question.question_type,
                subject=question.subject,
                topic=question.topic,
                sources=[],
                confidence=0,
                status=AnswerStatus.ERROR,
                method=str(getattr(self.backend, "name", type(self.backend).__name__)),
                verification=verification,
                warnings=[f"solver failure: {type(exc).__name__}"],
                trace=trace + [TraceStep(stage="pipeline", status="error", detail=f"{type(exc).__name__}")],
            ))

    def solve_batch(self, questions: list[Question]) -> BatchAnswer:
        if len(questions) > 500:
            raise ValueError("a batch cannot contain more than 500 questions")
        with ThreadPoolExecutor(max_workers=min(8, max(1, len(questions)))) as executor:
            answers = list(executor.map(self.solve, questions))
        evaluated = [answer for answer in answers if answer.correct is not None]
        correct = sum(answer.correct is True for answer in evaluated)
        return BatchAnswer(
            answers=answers,
            total=len(answers),
            verified=sum(answer.status == AnswerStatus.VERIFIED for answer in answers),
            needs_review=sum(answer.status == AnswerStatus.NEEDS_REVIEW for answer in answers),
            failed=sum(answer.status == AnswerStatus.ERROR for answer in answers),
            evaluated=len(evaluated),
            correct=correct,
            accuracy=correct / len(evaluated) if evaluated else None,
        )

    def _evaluate_answer(self, question: Question, answer: Answer) -> Answer:
        if question.expected_option_index is None and question.expected_answer is None:
            return answer
        if answer.answer is None:
            return answer.model_copy(update={
                "correct": False,
                "trace": answer.trace + [TraceStep(stage="expected_answer_evaluation", status="incorrect", detail="no answer was produced")],
            })
        if question.expected_option_index is not None:
            correct = answer.option_index == question.expected_option_index
            return answer.model_copy(update={
                "correct": correct,
                "trace": answer.trace + [TraceStep(stage="expected_answer_evaluation", status="correct" if correct else "incorrect", detail="option index compared with supplied key")],
            })

        expected = ProposedAnswer(answer=question.expected_answer or "")
        expected = self.verifier.normalize_proposal(question, expected)
        if expected.option_index is not None:
            correct = answer.option_index == expected.option_index
        else:
            normalize = lambda value: re.sub(r"\s+", " ", value.casefold()).strip()
            correct = normalize(answer.answer) == normalize(expected.answer)
        return answer.model_copy(update={
            "correct": correct,
            "trace": answer.trace + [TraceStep(stage="expected_answer_evaluation", status="correct" if correct else "incorrect", detail="normalized answer compared with supplied key")],
        })

    @staticmethod
    def _calibrate_confidence(proposal: ProposedAnswer, outcome: SolverOutcome, verification) -> float:
        if verification.status == AnswerStatus.NEEDS_REVIEW:
            return 0.0
        if verification.verified:
            return proposal.confidence
        # A model's self-reported confidence is not proof. Cap it according to
        # the evidence path so the client cannot mistake an unverified answer
        # for a deterministic result.
        cap = 0.85 if outcome.method == "consensus" else 0.65
        if outcome.warnings:
            cap = min(cap, 0.4)
        if verification.semantic.status == SemanticStatus.SUPPORTS:
            cap = 0.75 if not outcome.warnings else min(cap, 0.4)
        elif verification.semantic.status == SemanticStatus.UNCERTAIN:
            cap = min(cap, 0.5)
        return min(proposal.confidence, cap)

    @staticmethod
    def _merge_semantic_verification(verification, semantic: SemanticCheck):
        checks = list(verification.checks)
        warnings = list(verification.warnings)
        if semantic.status == SemanticStatus.SUPPORTS:
            checks.append("independent semantic verifier supports the proposal")
        elif semantic.status == SemanticStatus.CONTRADICTS:
            warnings.append("independent semantic verifier contradicts the proposal")
            verification = verification.model_copy(update={"status": AnswerStatus.NEEDS_REVIEW, "verified": False})
        elif semantic.status == SemanticStatus.UNCERTAIN:
            warnings.append("independent semantic verifier is uncertain")
        return verification.model_copy(update={"checks": checks, "warnings": warnings, "semantic": semantic})

    def verify_proposal(self, question: Question, proposal: ProposedAnswer):
        return self.verifier.verify(question, self.verifier.normalize_proposal(question, proposal))

    def verify_semantically(self, question: Question, proposal: ProposedAnswer) -> SemanticCheck:
        if self.semantic_verifier is None:
            return SemanticCheck(reason="semantic verifier is not configured")
        return self.semantic_verifier.verify(question, self.verifier.normalize_proposal(question, proposal))

    def classify(self, question: Question) -> Classification:
        return self.classifier.classify(question)

    def add_material(self, document_id: str, title: str, content: str, source: str | None = None) -> dict[str, str]:
        return self.knowledge_base.add_document(document_id, title, content, source)

    def search_material(self, query: str, top_k: int = 5) -> list[KnowledgeSearchHit]:
        return [KnowledgeSearchHit.model_validate(hit.__dict__) for hit in self.knowledge_base.search(query, top_k)]
