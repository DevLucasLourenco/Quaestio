"""Process configuration helpers."""

from __future__ import annotations


def load_environment() -> None:
    """Load a project-local .env file when python-dotenv is available."""

    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()
