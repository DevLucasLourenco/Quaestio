from __future__ import annotations

import json
import sys
from dataclasses import asdict
from typing import Any, Callable

from .config import load_environment

load_environment()

from .models import Attachment, ProposedAnswer, Question
from .code_analysis import CodeAnalyzer
from .parser import QuestionParser
from .vision import QuestionImageExtractor
from .ocr import TesseractOcr
from .sandbox import DockerSandbox
from .pdf import PdfExtractor
from .service import QuaestioService

service = QuaestioService()
code_analyzer = CodeAnalyzer()
question_parser = QuestionParser()
image_extractor = QuestionImageExtractor()
ocr = TesseractOcr()
sandbox = DockerSandbox()
pdf_extractor = PdfExtractor()


def _question_payload(
    question: str,
    options: list[str] | None,
    question_id: str | None,
    context: str | None,
    attachments: list[dict[str, Any]] | None = None,
    expected_answer: str | None = None,
    expected_option_index: int | None = None,
) -> Question:
    return Question(
        id=question_id,
        question=question,
        options=options,
        context=context,
        attachments=[Attachment.model_validate(item) for item in (attachments or [])],
        expected_answer=expected_answer,
        expected_option_index=expected_option_index,
    )


def solve_question(
    question: str,
    options: list[str] | None = None,
    question_id: str | None = None,
    context: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
    expected_answer: str | None = None,
    expected_option_index: int | None = None,
) -> dict[str, Any]:
    """Solve one question and return an auditable structured answer."""
    return service.solve(_question_payload(question, options, question_id, context, attachments, expected_answer, expected_option_index)).model_dump(mode="json")


def solve_questions_batch(questions: list[dict[str, Any]]) -> dict[str, Any]:
    """Solve a batch of questions while preserving each question id."""
    parsed = [Question.model_validate(item) for item in questions]
    return service.solve_batch(parsed).model_dump(mode="json")


def verify_answer(
    question: str,
    proposed_answer: str,
    options: list[str] | None = None,
    option_index: int | None = None,
    explanation: str | None = None,
) -> dict[str, Any]:
    """Verify the structural consistency of a proposed answer."""
    parsed_question = _question_payload(question, options, None, None)
    proposal = ProposedAnswer(answer=proposed_answer, option_index=option_index, explanation=explanation)
    return service.verify_proposal(parsed_question, proposal).model_dump(mode="json")


def verify_answer_semantically(
    question: str,
    proposed_answer: str,
    options: list[str] | None = None,
    option_index: int | None = None,
    explanation: str | None = None,
    context: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the optional independent semantic verifier on a proposal."""
    parsed_question = _question_payload(question, options, None, context, attachments)
    proposal = ProposedAnswer(answer=proposed_answer, option_index=option_index, explanation=explanation)
    return service.verify_semantically(parsed_question, proposal).model_dump(mode="json")


def classify_question(
    question: str,
    options: list[str] | None = None,
    context: str | None = None,
    subject: str | None = None,
    topic: str | None = None,
) -> dict[str, Any]:
    """Classify a question before selecting specialized resolution tools."""
    parsed = Question(question=question, options=options, context=context, subject=subject, topic=topic)
    return service.classify(parsed).model_dump(mode="json")


def add_study_material(
    document_id: str,
    title: str,
    content: str,
    source: str | None = None,
) -> dict[str, Any]:
    """Add text from an apostila, slide or other authorized study material."""
    return service.add_material(document_id, title, content, source)


def search_study_material(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Search the local study-material knowledge base."""
    return [hit.model_dump(mode="json") for hit in service.search_material(query, top_k)]


def analyze_code(language: str, code: str) -> dict[str, Any]:
    """Perform read-only static analysis without compiling or executing code."""
    return code_analyzer.analyze(language, code).model_dump(mode="json")


def compile_code(language: str, code: str) -> dict[str, Any]:
    """Validate compilation/syntax without executing source code."""
    return code_analyzer.compile(language, code).model_dump(mode="json")


def evaluate_questions(questions: list[dict[str, Any]]) -> dict[str, Any]:
    """Solve questions with expected answers and return accuracy metrics."""
    parsed = [Question.model_validate(item) for item in questions]
    missing = [question.id or str(index) for index, question in enumerate(parsed) if question.expected_answer is None and question.expected_option_index is None]
    if missing:
        raise ValueError(f"expected answer is missing for questions: {', '.join(missing)}")
    return service.solve_batch(parsed).model_dump(mode="json")


def parse_questions(text: str) -> dict[str, Any]:
    """Parse a raw text block into canonical questions and alternatives."""
    questions, warnings = question_parser.parse(text)
    return {
        "questions": [question.model_dump(mode="json") for question in questions],
        "count": len(questions),
        "warnings": warnings,
    }


def solve_text(text: str) -> dict[str, Any]:
    """Parse raw numbered text and solve all detected questions."""
    questions, warnings = question_parser.parse(text)
    result = service.solve_batch(questions).model_dump(mode="json")
    return {"parse_warnings": warnings, **result}


def extract_questions_from_image(
    attachments: list[dict[str, Any]],
    instruction: str | None = None,
) -> dict[str, Any]:
    """Extract questions from image attachments using an optional vision backend."""
    parsed = [Attachment.model_validate(item) for item in attachments]
    return image_extractor.extract(parsed, instruction).model_dump(mode="json")


def ocr_image(attachment: dict[str, Any], language: str = "por+eng") -> dict[str, Any]:
    """Extract text from one image locally without persisting it."""
    return asdict(ocr.extract(Attachment.model_validate(attachment), language))


def ocr_parse_image(attachment: dict[str, Any], language: str = "por+eng") -> dict[str, Any]:
    """OCR one image and parse the extracted text into canonical questions."""
    result = ocr.extract(Attachment.model_validate(attachment), language)
    if not result.text:
        return {"text": "", "questions": [], "count": 0, "method": result.method, "warnings": result.warnings}
    questions, parser_warnings = question_parser.parse(result.text)
    return {
        "text": result.text,
        "questions": [question.model_dump(mode="json") for question in questions],
        "count": len(questions),
        "method": result.method,
        "warnings": result.warnings + parser_warnings,
    }


def extract_pdf_text(attachment: dict[str, Any]) -> dict[str, Any]:
    """Extract text from one inline PDF using optional pypdf."""
    return asdict(pdf_extractor.extract(Attachment.model_validate(attachment)))


def extract_questions_from_pdf(attachment: dict[str, Any]) -> dict[str, Any]:
    """Extract PDF text and parse it into canonical questions."""
    result = pdf_extractor.extract(Attachment.model_validate(attachment))
    if not result.text:
        return {"text": "", "pages": result.pages, "questions": [], "count": 0, "method": result.method, "warnings": result.warnings}
    questions, parser_warnings = question_parser.parse(result.text)
    return {
        "text": result.text,
        "pages": result.pages,
        "questions": [question.model_dump(mode="json") for question in questions],
        "count": len(questions),
        "method": result.method,
        "warnings": result.warnings + parser_warnings,
    }


def run_code(language: str, code: str, stdin: str = "", timeout_seconds: int = 5) -> dict[str, Any]:
    """Run allowlisted code inside the configured Docker sandbox."""
    return sandbox.run(language, code, stdin, timeout_seconds).model_dump(mode="json")


def server_capabilities() -> dict[str, Any]:
    """Describe the current server capabilities and reliability policy."""
    return {
        "name": "quaestio",
        "version": "0.1.0",
        "features": [
            "single-question solving",
            "batch solving",
            "multiple-choice and open questions",
            "structured verification",
            "inline attachments in the canonical contract",
            "OpenAI-compatible backend when configured",
            "deterministic arithmetic subset",
            "optional symbolic math with SymPy",
            "independent LLM consensus when configured",
            "optional multilingual question preparation and answer localization",
            "multimodal consensus with shared image attachments",
            "local study-material retrieval with source tracking",
            "optional semantic embeddings with TF-IDF fallback",
            "read-only static code analysis",
            "safe syntax compilation checks",
            "historical batch evaluation with accuracy metrics",
            "plain-text question parsing",
            "raw-text parse-and-solve workflow",
            "optional multimodal question extraction",
            "optional local Tesseract OCR",
            "OCR-to-question parsing workflow",
            "optional PDF text extraction and parsing",
            "optional Docker sandbox execution",
            "optional independent semantic verification",
            "semantic verification with inline image attachments",
            "per-question audit trace",
        ],
        "policy": "never guess when no reliable proposal is available; return needs_review",
        "future_adapters": ["OCR-to-parser workflow", "additional Docker language runners", "Playwright client"],
    }


TOOL_DEFINITIONS = [
    {
        "name": "solve_question",
        "description": "Solve one study question and return an auditable structured answer.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "options": {"type": ["array", "null"], "items": {"type": "string"}},
                "question_id": {"type": ["string", "null"]},
                "context": {"type": ["string", "null"]},
                "attachments": {"type": ["array", "null"], "items": {"type": "object"}},
                "expected_answer": {"type": ["string", "null"]},
                "expected_option_index": {"type": ["integer", "null"]},
            },
            "required": ["question"],
        },
    },
    {
        "name": "solve_questions_batch",
        "description": "Solve a batch of questions while preserving each question id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "questions": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["questions"],
        },
    },
    {
        "name": "verify_answer",
        "description": "Verify the structural consistency of a proposed answer.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "proposed_answer": {"type": "string"},
                "options": {"type": ["array", "null"], "items": {"type": "string"}},
                "option_index": {"type": ["integer", "null"]},
                "explanation": {"type": ["string", "null"]},
            },
            "required": ["question", "proposed_answer"],
        },
    },
    {
        "name": "verify_answer_semantically",
        "description": "Review a proposal with a separately configured semantic verifier.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "proposed_answer": {"type": "string"},
                "options": {"type": ["array", "null"], "items": {"type": "string"}},
                "option_index": {"type": ["integer", "null"]},
                "explanation": {"type": ["string", "null"]},
                "context": {"type": ["string", "null"]},
                "attachments": {"type": ["array", "null"], "items": {"type": "object"}},
            },
            "required": ["question", "proposed_answer"],
        },
    },
    {
        "name": "server_capabilities",
        "description": "Describe Quaestio capabilities and its no-guess reliability policy.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "classify_question",
        "description": "Classify question type, subject and topic before resolution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "options": {"type": ["array", "null"], "items": {"type": "string"}},
                "context": {"type": ["string", "null"]},
                "subject": {"type": ["string", "null"]},
                "topic": {"type": ["string", "null"]},
            },
            "required": ["question"],
        },
    },
    {
        "name": "add_study_material",
        "description": "Add authorized study-material text to the local knowledge base.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string"},
                "title": {"type": "string"},
                "content": {"type": "string"},
                "source": {"type": ["string", "null"]},
            },
            "required": ["document_id", "title", "content"],
        },
    },
    {
        "name": "search_study_material",
        "description": "Search the local study-material knowledge base.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "top_k": {"type": "integer"}},
            "required": ["query"],
        },
    },
    {
        "name": "analyze_code",
        "description": "Analyze source code statically without executing it.",
        "inputSchema": {
            "type": "object",
            "properties": {"language": {"type": "string"}, "code": {"type": "string"}},
            "required": ["language", "code"],
        },
    },
    {
        "name": "compile_code",
        "description": "Check source compilation/syntax without executing the code.",
        "inputSchema": {
            "type": "object",
            "properties": {"language": {"type": "string"}, "code": {"type": "string"}},
            "required": ["language", "code"],
        },
    },
    {
        "name": "evaluate_questions",
        "description": "Solve a batch with expected answers and calculate accuracy metrics.",
        "inputSchema": {
            "type": "object",
            "properties": {"questions": {"type": "array", "items": {"type": "object"}}},
            "required": ["questions"],
        },
    },
    {
        "name": "parse_questions",
        "description": "Parse numbered raw exam text into canonical questions and options.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "solve_text",
        "description": "Parse raw numbered exam text and solve all detected questions.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "extract_questions_from_image",
        "description": "Extract canonical questions from image attachments using a configured vision model.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "attachments": {"type": "array", "items": {"type": "object"}},
                "instruction": {"type": ["string", "null"]},
            },
            "required": ["attachments"],
        },
    },
    {
        "name": "ocr_image",
        "description": "Extract text from one inline image with local Tesseract OCR.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "attachment": {"type": "object"},
                "language": {"type": "string"},
            },
            "required": ["attachment"],
        },
    },
    {
        "name": "ocr_parse_image",
        "description": "OCR one image and parse its text into canonical questions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "attachment": {"type": "object"},
                "language": {"type": "string"},
            },
            "required": ["attachment"],
        },
    },
    {
        "name": "extract_pdf_text",
        "description": "Extract text from one inline PDF using optional pypdf.",
        "inputSchema": {
            "type": "object",
            "properties": {"attachment": {"type": "object"}},
            "required": ["attachment"],
        },
    },
    {
        "name": "extract_questions_from_pdf",
        "description": "Extract PDF text and parse it into canonical questions.",
        "inputSchema": {
            "type": "object",
            "properties": {"attachment": {"type": "object"}},
            "required": ["attachment"],
        },
    },
    {
        "name": "run_code",
        "description": "Run allowlisted code in a networkless Docker sandbox with resource limits.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "language": {"type": "string"},
                "code": {"type": "string"},
                "stdin": {"type": "string"},
                "timeout_seconds": {"type": "integer"},
            },
            "required": ["language", "code"],
        },
    },
]

TOOL_HANDLERS: dict[str, Callable[..., dict[str, Any]]] = {
    "solve_question": solve_question,
    "solve_questions_batch": solve_questions_batch,
    "verify_answer": verify_answer,
    "verify_answer_semantically": verify_answer_semantically,
    "classify_question": classify_question,
    "add_study_material": add_study_material,
    "search_study_material": search_study_material,
    "analyze_code": analyze_code,
    "compile_code": compile_code,
    "evaluate_questions": evaluate_questions,
    "parse_questions": parse_questions,
    "solve_text": solve_text,
    "extract_questions_from_image": extract_questions_from_image,
    "ocr_image": ocr_image,
    "ocr_parse_image": ocr_parse_image,
    "extract_pdf_text": extract_pdf_text,
    "extract_questions_from_pdf": extract_questions_from_pdf,
    "run_code": run_code,
    "server_capabilities": server_capabilities,
}


def dispatch_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name not in TOOL_HANDLERS:
        raise ValueError(f"unknown tool: {name}")
    return TOOL_HANDLERS[name](**arguments)


def _jsonrpc_response(request_id: Any, result: Any = None, error: dict[str, Any] | None = None) -> dict[str, Any]:
    response: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result
    return response


def _handle_message(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if method in {"notifications/initialized", "notifications/cancelled"}:
        return None
    if method == "ping":
        return _jsonrpc_response(request_id, {})
    if method == "initialize":
        return _jsonrpc_response(request_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "quaestio", "version": "0.1.0"},
        })
    if method == "tools/list":
        return _jsonrpc_response(request_id, {"tools": TOOL_DEFINITIONS})
    if method == "tools/call":
        try:
            params = message.get("params") or {}
            result = dispatch_tool(params["name"], params.get("arguments") or {})
            return _jsonrpc_response(request_id, {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                "structuredContent": result,
                "isError": False,
            })
        except Exception as exc:
            return _jsonrpc_response(request_id, {
                "content": [{"type": "text", "text": f"Quaestio tool error: {exc}"}],
                "isError": True,
            })
    return _jsonrpc_response(request_id, error={"code": -32601, "message": f"Method not found: {method}"})


def _run_fallback_stdio() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            response = _handle_message(message)
        except json.JSONDecodeError as exc:
            response = _jsonrpc_response(None, error={"code": -32700, "message": str(exc)})
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)


def _run_sdk() -> bool:
    """Use the official SDK when installed; otherwise use our stdio fallback."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        return False
    sdk = FastMCP("quaestio")
    for handler in TOOL_HANDLERS.values():
        sdk.tool()(handler)
    sdk.run(transport="stdio")
    return True


def main() -> None:
    print("Quaestio MCP server starting on stdio", file=sys.stderr)
    _run_sdk() or _run_fallback_stdio()


if __name__ == "__main__":
    main()
