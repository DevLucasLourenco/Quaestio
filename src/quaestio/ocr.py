from __future__ import annotations

import base64
import binascii
import os
import shutil
import subprocess
from dataclasses import dataclass

from .models import Attachment


@dataclass(frozen=True)
class OcrResult:
    text: str
    method: str
    warnings: list[str]


class TesseractOcr:
    """Run local OCR through stdin without persisting the submitted image."""

    def __init__(self, executable: str | None = None, timeout_seconds: int = 30) -> None:
        self.executable = executable or os.getenv("QUAESTIO_TESSERACT_PATH") or shutil.which("tesseract")
        self.timeout_seconds = timeout_seconds

    def extract(self, attachment: Attachment, language: str = "por+eng") -> OcrResult:
        if not attachment.mime_type.startswith("image/"):
            return OcrResult("", "not_image", ["the attachment is not an image"])
        if not attachment.data_base64:
            return OcrResult("", "no_inline_data", ["local OCR requires inline base64 image data"])
        if not self.executable:
            return OcrResult("", "no_backend", ["Tesseract is not installed or configured"])
        try:
            image = base64.b64decode(attachment.data_base64, validate=True)
            if not image:
                raise ValueError("empty image")
        except (binascii.Error, ValueError) as exc:
            return OcrResult("", "invalid_image", [f"invalid base64 image: {type(exc).__name__}"])

        try:
            process = subprocess.run(
                [self.executable, "stdin", "stdout", "--psm", "6", "-l", language],
                input=image,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return OcrResult("", "ocr_failed", [f"Tesseract failed: {type(exc).__name__}"])
        if process.returncode != 0:
            message = process.stderr.decode("utf-8", errors="replace").strip() or "unknown Tesseract error"
            return OcrResult("", "ocr_failed", [message[:500]])
        text = process.stdout.decode("utf-8", errors="replace").strip()
        if not text:
            return OcrResult("", "ocr_empty", ["Tesseract returned no text"])
        return OcrResult(text, "tesseract", [])
