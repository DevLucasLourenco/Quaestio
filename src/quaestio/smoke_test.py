"""Opt-in smoke tests for configured external providers."""

from __future__ import annotations

import argparse
from collections import deque
from contextlib import contextmanager
import json
import os
import sys
import threading
import time
import urllib.request
from dataclasses import asdict, dataclass

from .backends import OpenAICompatibleBackend
from .config import load_environment
from .embeddings import OpenAICompatibleEmbeddingProvider
from .knowledge import KnowledgeBase
from .models import ProposedAnswer, Question
from .semantic_verifier import OpenAICompatibleSemanticVerifier
from .service import QuaestioService
from .translation import OpenAICompatibleTranslator


@dataclass(frozen=True)
class SmokeCheck:
    name: str
    status: str
    duration_ms: int
    detail: str


class _SmokeRequestLimiter:
    """Limit provider HTTP calls only while the opt-in smoke command runs."""

    def __init__(self, max_requests: int = 40, window_seconds: float = 60.0) -> None:
        self.max_requests = max(1, min(max_requests, 40))
        self.window_seconds = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            now = time.monotonic()
            with self._lock:
                while self._timestamps and now - self._timestamps[0] >= self.window_seconds:
                    self._timestamps.popleft()
                if len(self._timestamps) < self.max_requests:
                    self._timestamps.append(now)
                    return
                wait_seconds = self.window_seconds - (now - self._timestamps[0])
            time.sleep(max(0.01, wait_seconds))


def _smoke_request_limit() -> int:
    value = os.getenv("QUAESTIO_SMOKE_REQUESTS_PER_MINUTE", "40")
    try:
        return max(1, min(int(value), 40))
    except ValueError:
        return 40


@contextmanager
def _smoke_request_budget():
    """Patch the HTTP boundary for this process, without touching MCP runtime code."""

    limiter = _SmokeRequestLimiter(_smoke_request_limit())
    original_urlopen = urllib.request.urlopen

    def limited_urlopen(*args, **kwargs):
        limiter.acquire()
        return original_urlopen(*args, **kwargs)

    urllib.request.urlopen = limited_urlopen
    try:
        yield
    finally:
        urllib.request.urlopen = original_urlopen


def _timed(name: str, operation) -> SmokeCheck:
    started = time.perf_counter()
    try:
        detail = operation()
        return SmokeCheck(name, "passed", _duration_ms(started), detail)
    except Exception as exc:  # smoke tests report diagnostics instead of crashing
        return SmokeCheck(name, "failed", _duration_ms(started), f"{type(exc).__name__}: {exc}")


def _duration_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


def _required(name: str) -> tuple[str, str, str]:
    base_url = os.getenv(f"{name}_BASE_URL", "")
    api_key = os.getenv(f"{name}_API_KEY", "")
    model = os.getenv(f"{name}_MODEL", "")
    if not all((base_url, api_key, model)):
        raise RuntimeError(f"missing configuration for {name}")
    return base_url, api_key, model


def _configured(name: str) -> bool:
    return all(os.getenv(f"{name}_{suffix}") for suffix in ("BASE_URL", "API_KEY", "MODEL"))


def _chat_check(name: str, prefix: str, model_name: str) -> SmokeCheck:
    def operation() -> str:
        base_url, api_key, model = _required(prefix)
        timeout_value = os.getenv(f"{prefix}_TIMEOUT_SECONDS") or os.getenv("QUAESTIO_LLM_TIMEOUT_SECONDS", "45")
        max_tokens_value = os.getenv(f"{prefix}_MAX_TOKENS") or os.getenv("QUAESTIO_LLM_MAX_TOKENS")
        backend = OpenAICompatibleBackend(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=float(timeout_value),
            name=name,
            max_tokens=_optional_int(max_tokens_value),
        )
        outcome = backend.solve(Question(
            question="What is the capital of France? Return the option index in the JSON contract.",
            options=["Madrid", "Paris"],
        ))
        if outcome.proposal is None:
            detail = "; ".join(outcome.warnings) or "provider did not return a parseable proposal"
            raise RuntimeError(detail)
        if outcome.proposal.option_index != 1:
            raise RuntimeError(f"provider returned unexpected option_index: {outcome.proposal.option_index!r}")
        return f"model={model_name}; option_index={outcome.proposal.option_index}"

    return _timed(name, operation)


def _translator_check() -> SmokeCheck:
    def operation() -> str:
        base_url, api_key, model = _required("QUAESTIO_TRANSLATOR")
        translator = OpenAICompatibleTranslator(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=float(os.getenv("QUAESTIO_TRANSLATOR_TIMEOUT_SECONDS", "30")),
            max_tokens=_optional_int(os.getenv("QUAESTIO_TRANSLATOR_MAX_TOKENS")),
        )
        translated = translator.translate_question(
            Question(question="Qual é a capital do Brasil?", options=["Rio de Janeiro", "Brasília"]),
            "pt",
            "en",
        )
        if not translated.question or translated.options is None or len(translated.options) != 2:
            raise RuntimeError("translator response did not preserve the question contract")
        return f"model={model}; options={len(translated.options)}"

    return _timed("translator", operation)


def _embedding_check() -> SmokeCheck:
    def operation() -> str:
        base_url, api_key, model = _required("QUAESTIO_EMBEDDING")
        provider = OpenAICompatibleEmbeddingProvider(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=float(os.getenv("QUAESTIO_EMBEDDING_TIMEOUT_SECONDS", "30")),
        )
        vector = provider.embed("semantic retrieval smoke test")
        if not vector:
            raise RuntimeError("embedding provider returned an empty vector")
        return f"model={model}; dimensions={len(vector)}"

    return _timed("embeddings", operation)


def _verifier_check() -> SmokeCheck:
    def operation() -> str:
        base_url, api_key, model = _required("QUAESTIO_VERIFIER_LLM")
        verifier = OpenAICompatibleSemanticVerifier(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=float(os.getenv("QUAESTIO_VERIFIER_LLM_TIMEOUT_SECONDS", "45")),
            max_tokens=_optional_int(os.getenv("QUAESTIO_VERIFIER_LLM_MAX_TOKENS")),
            supports_images=os.getenv("QUAESTIO_VERIFIER_LLM_SUPPORTS_IMAGES", "true").casefold() in {"1", "true", "yes"},
        )
        result = verifier.verify(
            Question(question="Which option is correct?", options=["Option A", "Option B"]),
            ProposedAnswer(answer="Option A", option_index=0, explanation="The first option is the candidate."),
        )
        if result.reason and result.reason.startswith("semantic verifier failed:"):
            raise RuntimeError(result.reason)
        return f"model={model}; status={result.status.value}"

    return _timed("semantic_verifier", operation)


def _end_to_end_check() -> SmokeCheck:
    def operation() -> str:
        service = QuaestioService(knowledge_base=KnowledgeBase(storage_path=None, embedding_provider=None))
        result = service.solve(Question(
            question="Qual é a capital do Brasil?",
            options=["Rio de Janeiro", "Brasília", "São Paulo"],
        ))
        if result.status.value == "error":
            raise RuntimeError("end-to-end pipeline returned error")
        return f"status={result.status.value}; method={result.method}; trace_steps={len(result.trace)}"

    return _timed("end_to_end", operation)


def run_smoke_tests(require_all: bool = False) -> list[SmokeCheck]:
    checks = [_chat_check("primary_llm", "QUAESTIO_LLM", os.getenv("QUAESTIO_LLM_MODEL", "<unset>"))]
    optional_checks = [
        ("QUAESTIO_SECONDARY_LLM", lambda: _chat_check("secondary_llm", "QUAESTIO_SECONDARY_LLM", os.getenv("QUAESTIO_SECONDARY_LLM_MODEL", "<unset>"))),
        ("QUAESTIO_TRANSLATOR", _translator_check),
        ("QUAESTIO_EMBEDDING", _embedding_check),
        ("QUAESTIO_VERIFIER_LLM", _verifier_check),
    ]
    for prefix, operation in optional_checks:
        if _configured(prefix):
            checks.append(operation())
        elif require_all:
            checks.append(SmokeCheck(prefix, "failed", 0, "missing configuration"))
        else:
            checks.append(SmokeCheck(prefix, "skipped", 0, "not configured"))
    checks.append(_end_to_end_check())
    return checks


def _print_human(checks: list[SmokeCheck]) -> None:
    for check in checks:
        print(f"[{check.status.upper():7}] {check.name:18} {check.duration_ms:>6} ms  {check.detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run opt-in smoke tests against Quaestio providers.")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.add_argument("--require-all", action="store_true", help="fail if any configured check fails")
    args = parser.parse_args(argv)

    load_environment()
    with _smoke_request_budget():
        checks = run_smoke_tests(require_all=args.require_all)
    if args.json:
        print(json.dumps([asdict(check) for check in checks], ensure_ascii=False, indent=2))
    else:
        _print_human(checks)
    failed = any(check.status == "failed" for check in checks)
    return 1 if failed else 0


def _optional_int(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


if __name__ == "__main__":
    sys.exit(main())
