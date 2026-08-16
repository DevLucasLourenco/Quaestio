from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from io import BytesIO

from .models import Attachment


@dataclass(frozen=True)
class PdfTextResult:
    text: str
    pages: int
    method: str
    warnings: list[str]


class PdfExtractor:
    """Extract text from inline PDFs through optional pypdf."""

    def extract(self, attachment: Attachment) -> PdfTextResult:
        if attachment.mime_type != "application/pdf":
            return PdfTextResult("", 0, "not_pdf", ["the attachment is not a PDF"])
        if not attachment.data_base64:
            return PdfTextResult("", 0, "no_inline_data", ["PDF extraction requires inline base64 data"])
        try:
            raw = base64.b64decode(attachment.data_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            return PdfTextResult("", 0, "invalid_pdf", [f"invalid base64 PDF: {type(exc).__name__}"])
        try:
            from pypdf import PdfReader
        except ImportError:
            return PdfTextResult("", 0, "no_backend", ["install the optional pdf extra to extract PDFs: pip install -e .[pdf]"])
        try:
            reader = PdfReader(BytesIO(raw))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(page.strip() for page in pages if page.strip()).strip()
            if not text:
                return PdfTextResult("", len(pages), "pdf_empty", ["PDF contains no extractable text; OCR may be required"])
            return PdfTextResult(text, len(pages), "pypdf", [])
        except Exception as exc:
            return PdfTextResult("", 0, "pdf_failed", [f"PDF extraction failed: {type(exc).__name__}"])
