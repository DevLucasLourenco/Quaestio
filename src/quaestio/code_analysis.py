from __future__ import annotations

import ast
import re

from pydantic import BaseModel, Field


class CodeIssue(BaseModel):
    code: str
    severity: str
    message: str
    line: int | None = None


class CodeAnalysis(BaseModel):
    language: str
    syntax_valid: bool | None
    lines: int = Field(ge=0)
    issues: list[CodeIssue] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)


class CompilationResult(BaseModel):
    language: str
    supported: bool
    success: bool | None
    diagnostics: list[CodeIssue] = Field(default_factory=list)
    policy: str


class CodeAnalyzer:
    """Read-only static analysis for educational code questions."""

    def analyze(self, language: str, code: str) -> CodeAnalysis:
        if not code.strip():
            raise ValueError("code cannot be empty")
        normalized = language.casefold().strip()
        issues: list[CodeIssue] = []
        signals: list[str] = []
        syntax_valid: bool | None = None
        if normalized in {"python", "py"}:
            normalized = "python"
            try:
                ast.parse(code)
                syntax_valid = True
            except SyntaxError as exc:
                syntax_valid = False
                issues.append(CodeIssue(code="PY-SYNTAX", severity="error", message=exc.msg, line=exc.lineno))
            self._python_patterns(code, issues, signals)
        elif normalized in {"javascript", "js", "typescript", "ts"}:
            normalized = "javascript" if normalized in {"javascript", "js"} else "typescript"
            syntax_valid = None
            self._generic_patterns(code, issues, signals)
        elif normalized in {"java", "csharp", "c#"}:
            normalized = "java" if normalized == "java" else "csharp"
            syntax_valid = None
            self._generic_patterns(code, issues, signals)
        else:
            normalized = language.strip().lower()
            self._generic_patterns(code, issues, signals)
        return CodeAnalysis(
            language=normalized,
            syntax_valid=syntax_valid,
            lines=len(code.splitlines()),
            issues=issues,
            signals=signals,
        )

    def compile(self, language: str, code: str) -> CompilationResult:
        if not code.strip():
            raise ValueError("code cannot be empty")
        normalized = language.casefold().strip()
        if normalized in {"python", "py"}:
            try:
                compile(code, "<quaestio>", "exec")
                return CompilationResult(
                    language="python",
                    supported=True,
                    success=True,
                    policy="syntax compilation only; code was not executed",
                )
            except SyntaxError as exc:
                return CompilationResult(
                    language="python",
                    supported=True,
                    success=False,
                    diagnostics=[CodeIssue(code="PY-SYNTAX", severity="error", message=exc.msg, line=exc.lineno)],
                    policy="syntax compilation only; code was not executed",
                )
        return CompilationResult(
            language=language.strip().lower(),
            supported=False,
            success=None,
            diagnostics=[CodeIssue(code="COMPILER-NOT-CONFIGURED", severity="info", message="nenhum compilador seguro foi configurado para esta linguagem.")],
            policy="no external compiler was invoked and code was not executed",
        )

    @staticmethod
    def _python_patterns(code: str, issues: list[CodeIssue], signals: list[str]) -> None:
        for pattern, issue_code, message, severity in [
            (r"\beval\s*\(", "PY-EVAL", "eval pode executar entrada não confiável.", "warning"),
            (r"\bexec\s*\(", "PY-EXEC", "exec pode executar código arbitrário.", "warning"),
            (r"\bexcept\s*:\s*$", "PY-BARE-EXCEPT", "except genérico pode ocultar erros.", "warning"),
        ]:
            for match in re.finditer(pattern, code, re.MULTILINE):
                issues.append(CodeIssue(code=issue_code, severity=severity, message=message, line=code.count("\n", 0, match.start()) + 1))
        if "threading" in code or "asyncio" in code:
            signals.append("concorrência detectada; revisar sincronização")

    @staticmethod
    def _generic_patterns(code: str, issues: list[CodeIssue], signals: list[str]) -> None:
        if re.search(r"\b(eval|exec|Function)\s*\(", code):
            issues.append(CodeIssue(code="GEN-DYNAMIC-EVAL", severity="warning", message="execução dinâmica pode introduzir risco."))
        if re.search(r"static\s+\w+\s+instance\b|instance\s*=\s*new\s+", code) and re.search(r"instance\s*==\s*null", code):
            signals.append("padrão singleton detectado")
            if not re.search(r"synchronized|lock|mutex|atomic", code, re.IGNORECASE):
                issues.append(CodeIssue(code="CONCURRENCY-SINGLETON", severity="warning", message="singleton pode ter condição de corrida em ambiente multithread."))
        if re.search(r"TODO|FIXME", code, re.IGNORECASE):
            signals.append("marcadores de trabalho pendente detectados")
