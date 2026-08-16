from quaestio.parser import QuestionParser


def test_parser_extracts_multiple_choice_and_open_questions():
    text = """
    1) Qual é o resultado de 2 + 2?
    A) 3
    B) 4
    C) 5

    2. Explique o princípio da inércia.
    """
    questions, warnings = QuestionParser().parse(text)
    assert warnings == []
    assert len(questions) == 2
    assert questions[0].id == "1"
    assert questions[0].options == ["3", "4", "5"]
    assert questions[1].options is None


def test_parser_keeps_multiline_option_text():
    questions, _ = QuestionParser().parse("""
    7: Escolha a alternativa correta.
    A) Primeira parte da alternativa
       continuação da alternativa.
    B) Segunda alternativa.
    """)
    assert questions[0].options[0] == "Primeira parte da alternativa continuação da alternativa."


def test_parser_warns_when_text_is_not_numbered():
    questions, warnings = QuestionParser().parse("Explique a fotossíntese.")
    assert len(questions) == 1
    assert questions[0].question == "Explique a fotossíntese."
    assert warnings
