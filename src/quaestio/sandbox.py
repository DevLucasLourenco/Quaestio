from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass

from pydantic import BaseModel, Field


class ExecutionResult(BaseModel):
    language: str
    status: str
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int | None = None
    policy: str
    warnings: list[str] = Field(default_factory=list)


@dataclass
class DockerSandbox:
    """Run allowlisted code in a networkless, resource-limited container."""

    docker_executable: str | None = None
    python_image: str = "python:3.12-slim"
    node_image: str = "node:22-slim"
    output_limit: int = 20_000

    def __post_init__(self) -> None:
        self.docker_executable = self.docker_executable or os.getenv("QUAESTIO_DOCKER_PATH") or shutil.which("docker")
        self.python_image = os.getenv("QUAESTIO_SANDBOX_PYTHON_IMAGE", self.python_image)
        self.node_image = os.getenv("QUAESTIO_SANDBOX_NODE_IMAGE", self.node_image)

    def run(self, language: str, code: str, stdin: str = "", timeout_seconds: int = 5) -> ExecutionResult:
        normalized = language.casefold().strip()
        policy = "Docker only; network disabled, read-only root, dropped capabilities, resource limits, no host mounts"
        if normalized in {"python", "py"}:
            normalized = "python"
            image = self.python_image
            interpreter = ["python", "-I", "-S", "-"]
        elif normalized in {"javascript", "js", "node"}:
            normalized = "javascript"
            image = self.node_image
            interpreter = ["node", "-"]
        else:
            return ExecutionResult(language=language, status="unsupported", policy=policy, warnings=["only Python and JavaScript execution are currently allowlisted"])
        if not code.strip():
            return ExecutionResult(language=normalized, status="invalid", policy=policy, warnings=["code cannot be empty"])
        if len(code.encode("utf-8")) > 32_000:
            return ExecutionResult(language=normalized, status="invalid", policy=policy, warnings=["code exceeds the 32 KB limit"])
        if not 1 <= timeout_seconds <= 15:
            return ExecutionResult(language=normalized, status="invalid", policy=policy, warnings=["timeout must be between 1 and 15 seconds"])
        if not self.docker_executable:
            return ExecutionResult(language=normalized, status="unavailable", policy=policy, warnings=["Docker executable was not found"])
        if not self._image_available(image):
            return ExecutionResult(language=normalized, status="unavailable", policy=policy, warnings=[f"Docker image is unavailable: {image}"])

        command = [
            self.docker_executable,
            "run", "--rm",
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit=64",
            "--memory=256m",
            "--cpus=0.5",
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=16m",
            "--user", "65532:65532",
            image,
            *interpreter,
        ]
        try:
            completed = subprocess.run(
                command,
                input=stdin,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return ExecutionResult(
                language=normalized,
                status="timeout",
                stdout=self._truncate(exc.stdout),
                stderr=self._truncate(exc.stderr),
                policy=policy,
                warnings=["execution exceeded the timeout and was terminated"],
            )
        except OSError as exc:
            return ExecutionResult(language=normalized, status="unavailable", policy=policy, warnings=[f"Docker invocation failed: {type(exc).__name__}"])
        return ExecutionResult(
            language=normalized,
            status="completed" if completed.returncode == 0 else "error",
            exit_code=completed.returncode,
            stdout=self._truncate(completed.stdout),
            stderr=self._truncate(completed.stderr),
            policy=policy,
        )

    def _image_available(self, image: str) -> bool:
        try:
            result = subprocess.run(
                [self.docker_executable, "image", "inspect", image],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def _truncate(self, value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        if len(value) <= self.output_limit:
            return value
        return value[: self.output_limit] + "\n[output truncated]"
