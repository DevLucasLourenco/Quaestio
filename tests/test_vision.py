from quaestio.models import Attachment
from quaestio.vision import QuestionImageExtractor


def test_image_extractor_reports_missing_backend_instead_of_guessing(monkeypatch):
    for name in ["QUAESTIO_LLM_BASE_URL", "QUAESTIO_LLM_API_KEY", "QUAESTIO_LLM_MODEL"]:
        monkeypatch.delenv(name, raising=False)
    result = QuestionImageExtractor().extract([
        Attachment(mime_type="image/png", data_base64="aW1hZ2U=")
    ])
    assert result.questions == []
    assert result.method == "no_backend"
    assert result.warnings


def test_image_extractor_requires_an_inline_image():
    result = QuestionImageExtractor().extract([Attachment(mime_type="application/pdf", uri="file:///tmp/prova.pdf")])
    assert result.method == "no_image"
