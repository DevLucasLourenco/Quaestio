from quaestio.backends import OpenAICompatibleBackend
from quaestio.models import Question
from quaestio.semantic_verifier import OpenAICompatibleSemanticVerifier
from quaestio.translation import OpenAICompatibleTranslator


def test_solver_recovers_exact_option_index_from_answer_text():
    question = Question(question="Escolha", options=["A", "Brasília"])
    proposal = OpenAICompatibleBackend._parse_content(
        "internal reasoning\n{\"answer\": \"Brasília\", \"option_index\": null, \"explanation\": \"capital\"}",
        question,
    )
    assert proposal.option_index == 1


def test_solver_message_content_accepts_reasoning_endpoint_shapes():
    assert OpenAICompatibleBackend._message_content({"content": [{"text": "json"}]}) == "json"
    assert OpenAICompatibleBackend._message_content({"content": "", "reasoning_content": "json"}) == "json"


def test_translation_and_verifier_accept_reasoning_endpoint_shapes():
    assert OpenAICompatibleTranslator._message_content({"content": [{"text": "json"}]}) == "json"
    assert OpenAICompatibleSemanticVerifier._message_content({"content": "", "reasoning_content": "json"}) == "json"
