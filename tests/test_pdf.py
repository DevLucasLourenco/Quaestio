from quaestio.models import Attachment
from quaestio.pdf import PdfExtractor


def test_pdf_extractor_rejects_non_pdf():
    result = PdfExtractor().extract(Attachment(mime_type="image/png", data_base64="aW1hZ2U="))
    assert result.method == "not_pdf"


def test_pdf_extractor_rejects_invalid_base64():
    result = PdfExtractor().extract(Attachment(mime_type="application/pdf", data_base64="invalid"))
    assert result.method == "invalid_pdf"
