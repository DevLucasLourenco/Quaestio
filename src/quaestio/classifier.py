from __future__ import annotations

import unicodedata

from .models import Classification, Question, QuestionType


class QuestionClassifier:
    """Deterministic first-pass classifier; an LLM classifier can replace it later."""

    RULES = {
        "mathematics": {
            "calculus": ("derivada", "integral", "limite", "derivative", "integral"),
            "algebra": ("equação", "matriz", "sistema linear", "polinômio", "álgebra"),
            "geometry": ("triângulo", "ângulo", "área", "volume", "geometria"),
            "graph": ("graph", "gráfico", "curva", "eixo", "função"),
            "arithmetic": ("calcule", "quanto é", "soma", "divisão", "percentual"),
        },
        "software_engineering": {
            "design_patterns": ("design pattern", "padrão de projeto", "factory", "singleton", "adapter", "state"),
            "algorithms": ("algoritmo", "complexidade", "big o", "recursão", "árvore", "grafo"),
            "databases": ("sql", "banco de dados", "normalização", "transação", "índice", "database"),
            "networks": ("tcp", "udp", "http", "dns", "protocolo", "rede"),
            "programming": ("código", "classe", "função", "java", "python", "javascript", "compile"),
        },
        "general": {"general": ()},
    }

    def classify(self, question: Question) -> Classification:
        text = self._fold(" ".join(filter(None, [question.question, question.context, question.subject, question.topic])))
        if question.subject:
            subject = question.subject
            topic = question.topic or "general"
            return Classification(
                question_type=question.question_type,
                subject=subject,
                topic=topic,
                confidence=1.0,
                signals=["subject supplied by caller"],
            )

        best_subject, best_topic, best_score = "general", "general", 0
        signals: list[str] = []
        for subject, topics in self.RULES.items():
            for topic, keywords in topics.items():
                matched = [keyword for keyword in keywords if self._fold(keyword) in text]
                if len(matched) > best_score:
                    best_subject, best_topic, best_score = subject, topic, len(matched)
                    signals = matched
        confidence = 0.9 if best_score >= 2 else 0.75 if best_score == 1 else 0.2
        return Classification(
            question_type=question.question_type,
            subject=best_subject,
            topic=best_topic,
            confidence=confidence,
            signals=signals,
        )

    @staticmethod
    def _fold(value: str) -> str:
        return "".join(
            character
            for character in unicodedata.normalize("NFKD", value.casefold())
            if not unicodedata.combining(character)
        )
