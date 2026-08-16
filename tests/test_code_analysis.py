from quaestio.code_analysis import CodeAnalyzer


def test_python_syntax_and_dangerous_calls_are_reported():
    result = CodeAnalyzer().analyze("python", "value = eval(user_input)")
    assert result.syntax_valid is True
    assert any(issue.code == "PY-EVAL" for issue in result.issues)


def test_python_syntax_error_is_reported():
    result = CodeAnalyzer().analyze("python", "def broken(:")
    assert result.syntax_valid is False
    assert any(issue.code == "PY-SYNTAX" for issue in result.issues)


def test_compile_code_checks_python_without_execution():
    result = CodeAnalyzer().compile("python", "value = 1 + 1")
    assert result.supported is True
    assert result.success is True
    assert "not executed" in result.policy


def test_compile_code_is_explicit_when_compiler_is_unavailable():
    result = CodeAnalyzer().compile("java", "class Example {}")
    assert result.supported is False
    assert result.success is None
