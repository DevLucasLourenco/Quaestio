from quaestio.models import Attachment
from quaestio.ocr import OcrResult, TesseractOcr


def test_ocr_requires_an_image_attachment():
    result = TesseractOcr(executable="does-not-exist").extract(Attachment(mime_type="application/pdf", uri="file.pdf"))
    assert result.method == "not_image"


def test_ocr_rejects_invalid_base64_before_calling_tesseract():
    result = TesseractOcr(executable="does-not-exist").extract(
        Attachment(mime_type="image/png", data_base64="invalid")
    )
    assert result.method == "invalid_image"


def test_ocr_parse_workflow_connects_text_to_question_parser(monkeypatch):
    import quaestio.mcp_server as server

    monkeypatch.setattr(server.ocr, "extract", lambda attachment, language: OcrResult(
        "1) Quanto é 2 + 2?\nA) 3\nB) 4", "fake_ocr", []
    ))
    result = server.ocr_parse_image({"mime_type": "image/png", "data_base64": "aW1hZ2U="})
    assert result["method"] == "fake_ocr"
    assert result["questions"][0]["options"] == ["3", "4"]
