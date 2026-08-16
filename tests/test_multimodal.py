from quaestio.backends import OpenAICompatibleBackend
from quaestio.models import Attachment, Question


def test_multimodal_question_becomes_openai_image_content():
    question = Question(
        question="Interprete o gráfico.",
        attachments=[Attachment(mime_type="image/png", data_base64="aW1hZ2U=")],
    )
    content = OpenAICompatibleBackend._user_content(question, "Leia o gráfico.")
    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert "data:image/png;base64,aW1hZ2U=" in content[1]["image_url"]["url"]
