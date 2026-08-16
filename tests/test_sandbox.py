from quaestio.sandbox import DockerSandbox


def test_sandbox_rejects_unsupported_language_before_docker():
    result = DockerSandbox(docker_executable=None).run("java", "class Main {}")
    assert result.status == "unsupported"


def test_sandbox_allowlists_javascript_but_never_falls_back_to_host():
    result = DockerSandbox(docker_executable="does-not-exist").run("javascript", "console.log(2 + 2)")
    assert result.status == "unavailable"
    assert result.language == "javascript"


def test_sandbox_enforces_input_limits():
    sandbox = DockerSandbox(docker_executable="does-not-exist")
    assert sandbox.run("python", "", timeout_seconds=5).status == "invalid"
    assert sandbox.run("python", "x" * 33_000, timeout_seconds=5).status == "invalid"
    assert sandbox.run("python", "print(1)", timeout_seconds=20).status == "invalid"
