from quaestio.classifier import QuestionClassifier
from quaestio.models import Question, QuestionType


def test_classifier_detects_software_design_patterns():
    result = QuestionClassifier().classify(Question(
        question="Qual design pattern altera o comportamento conforme o estado?",
        options=["Factory", "State"],
    ))
    assert result.question_type == QuestionType.MULTIPLE_CHOICE
    assert result.subject == "software_engineering"
    assert result.topic == "design_patterns"


def test_classifier_handles_portuguese_accents():
    result = QuestionClassifier().classify(Question(
        question="Qual padrão de projeto altera o comportamento conforme o estado?",
        options=["Factory", "State"],
    ))
    assert result.subject == "software_engineering"
    assert result.topic == "design_patterns"


def test_classifier_respects_explicit_domain_metadata():
    result = QuestionClassifier().classify(Question(
        question="Qual alternativa?",
        subject="physics",
        topic="kinematics",
    ))
    assert result.subject == "physics"
    assert result.topic == "kinematics"
