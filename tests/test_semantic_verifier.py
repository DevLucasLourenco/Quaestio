import json

from quaestio.models import Attachment, ProposedAnswer, Question, SemanticStatus
from quaestio.semantic_verifier import OpenAICompatibleSemanticVerifier


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({
            "choices": [{"message": {"content": '{"status":"supports","confidence":0.9,"reason":"image supports candidate"}'}}]
        }).encode()


def test_semantic_verifier_sends_inline_images(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode())
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    verifier = OpenAICompatibleSemanticVerifier("https://example.test/v1", "secret", "vision-model")
    result = verifier.verify(
        Question(
            question="Which shape is shown?",
            options=["circle", "square"],
            attachments=[Attachment(mime_type="image/png", data_base64="aW1hZ2U=")],
        ),
        ProposedAnswer(answer="circle", option_index=0),
    )

    assert result.status == SemanticStatus.SUPPORTS
    content = captured["payload"]["messages"][1]["content"]
    assert content[0]["type"] == "text"
    assert content[1]["image_url"]["url"] == "data:image/png;base64,aW1hZ2U="
