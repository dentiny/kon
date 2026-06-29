"""Estimate token usage from Cursor agent transcript JSONL files."""

from __future__ import annotations

import json
from pathlib import Path

from _transcript_text import content_text

CHARS_PER_TOKEN = 4
SOURCE = "transcript_estimate"
OUTPUT_SOURCE = "output_estimate"


def estimate_tokens_from_transcript(path: str | Path) -> dict | None:
    """Return input/output/total token estimates, or None if unavailable."""
    transcript = Path(path)
    if not transcript.is_file():
        return None

    input_chars = 0
    output_chars = 0
    try:
        for line in transcript.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            role = row.get("role")
            message = row.get("message") or {}
            text = content_text(message.get("content"))
            if role == "user":
                input_chars += len(text)
            elif role == "assistant":
                output_chars += len(text)
    except OSError:
        return None

    if input_chars == 0 and output_chars == 0:
        return None

    input_tokens = input_chars // CHARS_PER_TOKEN
    output_tokens = output_chars // CHARS_PER_TOKEN
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "source": SOURCE,
    }


def estimate_tokens_from_output_text(text: str) -> dict | None:
    """Fallback when transcript path is unavailable — count assistant output chars only."""
    chars = len(text.strip())
    if chars == 0:
        return None
    output_tokens = chars // CHARS_PER_TOKEN
    return {
        "input_tokens": 0,
        "output_tokens": output_tokens,
        "total_tokens": output_tokens,
        "source": OUTPUT_SOURCE,
    }
