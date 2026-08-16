"""Process configuration helpers."""

from __future__ import annotations

import os


def load_environment() -> None:
    """Load a project-local .env file when python-dotenv is available."""

    if os.getenv("QUAESTIO_DISABLE_DOTENV", "").casefold() in {"1", "true", "yes"}:
        return

    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()
