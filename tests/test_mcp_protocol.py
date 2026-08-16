from quaestio.mcp_server import _handle_message


def test_initialize_and_list_tools_follow_mcp_shape():
    initialized = _handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert initialized["result"]["serverInfo"]["name"] == "quaestio"

    listed = _handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    assert {tool["name"] for tool in listed["result"]["tools"]} == {
        "solve_question",
        "solve_questions_batch",
        "verify_answer",
        "server_capabilities",
        "classify_question",
        "add_study_material",
        "search_study_material",
        "analyze_code",
        "evaluate_questions",
        "parse_questions",
        "solve_text",
        "extract_questions_from_image",
        "compile_code",
        "ocr_image",
        "ocr_parse_image",
        "extract_pdf_text",
        "extract_questions_from_pdf",
        "run_code",
        "verify_answer_semantically",
    }


def test_tool_call_returns_structured_content():
    response = _handle_message({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "solve_question",
            "arguments": {"question": "Calcule: 3 * 3", "options": ["6", "9"]},
        },
    })
    assert response["result"]["isError"] is False
    assert response["result"]["structuredContent"]["answer"] == "9"
    assert response["result"]["structuredContent"]["status"] == "verified"


def test_classification_tool_is_exposed():
    response = _handle_message({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "classify_question",
            "arguments": {"question": "Qual a complexidade Big O deste algoritmo?"},
        },
    })
    assert response["result"]["structuredContent"]["subject"] == "software_engineering"


def test_code_analysis_tool_is_read_only_and_structured():
    response = _handle_message({
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "analyze_code",
            "arguments": {"language": "java", "code": "static Singleton instance; if (instance == null) instance = new Singleton();"},
        },
    })
    result = response["result"]["structuredContent"]
    assert result["language"] == "java"
    assert any(issue["code"] == "CONCURRENCY-SINGLETON" for issue in result["issues"])


def test_evaluation_tool_returns_accuracy_metrics():
    response = _handle_message({
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "evaluate_questions",
            "arguments": {
                "questions": [
                    {"id": "q1", "question": "Calcule: 2 + 2", "options": ["3", "4"], "expected_answer": "B"},
                    {"id": "q2", "question": "Calcule: 3 + 3", "options": ["5", "6"], "expected_option_index": 1},
                ],
            },
        },
    })
    result = response["result"]["structuredContent"]
    assert result["evaluated"] == 2
    assert result["correct"] == 2
    assert result["accuracy"] == 1.0


def test_parse_tool_returns_canonical_questions():
    response = _handle_message({
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {
            "name": "parse_questions",
            "arguments": {"text": "1) Quanto é 2 + 2?\nA) 3\nB) 4"},
        },
    })
    result = response["result"]["structuredContent"]
    assert result["count"] == 1
    assert result["questions"][0]["options"] == ["3", "4"]


def test_solve_text_parses_and_solves_in_one_call():
    response = _handle_message({
        "jsonrpc": "2.0",
        "id": 8,
        "method": "tools/call",
        "params": {
            "name": "solve_text",
            "arguments": {"text": "1) Quanto é 2 + 2?\nA) 3\nB) 4"},
        },
    })
    result = response["result"]["structuredContent"]
    assert result["total"] == 1
    assert result["answers"][0]["answer"] == "4"


def test_image_extraction_tool_reports_missing_backend():
    response = _handle_message({
        "jsonrpc": "2.0",
        "id": 9,
        "method": "tools/call",
        "params": {
            "name": "extract_questions_from_image",
            "arguments": {"attachments": [{"mime_type": "image/png", "data_base64": "aW1hZ2U="}]},
        },
    })
    result = response["result"]["structuredContent"]
    assert result["questions"] == []
    assert result["method"] in {"no_backend", "vision_llm"}


def test_compile_tool_never_executes_code():
    response = _handle_message({
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {"name": "compile_code", "arguments": {"language": "python", "code": "value = 2"}},
    })
    result = response["result"]["structuredContent"]
    assert result["success"] is True
    assert "not executed" in result["policy"]


def test_ocr_tool_rejects_invalid_image_without_crashing():
    response = _handle_message({
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "ocr_image",
            "arguments": {"attachment": {"mime_type": "image/png", "data_base64": "not-base64"}},
        },
    })
    result = response["result"]["structuredContent"]
    assert result["text"] == ""
    assert result["method"] == "invalid_image"


def test_ocr_parse_tool_preserves_explicit_ocr_failure():
    response = _handle_message({
        "jsonrpc": "2.0",
        "id": 14,
        "method": "tools/call",
        "params": {
            "name": "ocr_parse_image",
            "arguments": {"attachment": {"mime_type": "image/png", "data_base64": "not-base64"}},
        },
    })
    result = response["result"]["structuredContent"]
    assert result["count"] == 0
    assert result["method"] == "invalid_image"


def test_pdf_tools_report_missing_optional_backend():
    response = _handle_message({
        "jsonrpc": "2.0",
        "id": 15,
        "method": "tools/call",
        "params": {
            "name": "extract_questions_from_pdf",
            "arguments": {"attachment": {"mime_type": "application/pdf", "data_base64": "JVBERi0="}},
        },
    })
    result = response["result"]["structuredContent"]
    assert result["questions"] == []
    assert result["method"] in {"no_backend", "pdf_failed", "pdf_empty"}


def test_run_code_reports_unavailable_without_executing_on_host():
    response = _handle_message({
        "jsonrpc": "2.0",
        "id": 12,
        "method": "tools/call",
        "params": {"name": "run_code", "arguments": {"language": "python", "code": "print(2 + 2)"}},
    })
    result = response["result"]["structuredContent"]
    assert result["status"] in {"unavailable", "completed", "error"}
    assert "Docker" in result["policy"]


def test_semantic_verification_is_explicit_when_not_configured():
    response = _handle_message({
        "jsonrpc": "2.0",
        "id": 13,
        "method": "tools/call",
        "params": {
            "name": "verify_answer_semantically",
            "arguments": {"question": "Escolha", "options": ["A", "B"], "proposed_answer": "A"},
        },
    })
    result = response["result"]["structuredContent"]
    assert result["status"] == "not_configured"
