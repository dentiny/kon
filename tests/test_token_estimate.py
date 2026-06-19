"""Tests for transcript token estimation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))

from _token_estimate import estimate_tokens_from_output_text, estimate_tokens_from_transcript  # noqa: E402


def test_estimate_from_transcript(tmp_path: Path) -> None:
    transcript = tmp_path / "agent.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps(
                    {"role": "user", "message": {"content": [{"type": "text", "text": "a" * 40}]}}
                ),
                json.dumps(
                    {
                        "role": "assistant",
                        "message": {"content": [{"type": "text", "text": "b" * 80}]},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    usage = estimate_tokens_from_transcript(transcript)
    assert usage is not None
    assert usage["input_tokens"] == 10
    assert usage["output_tokens"] == 20
    assert usage["total_tokens"] == 30
    assert usage["source"] == "transcript_estimate"


def test_missing_transcript_returns_none(tmp_path: Path) -> None:
    assert estimate_tokens_from_transcript(tmp_path / "missing.jsonl") is None


def test_empty_transcript_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    assert estimate_tokens_from_transcript(path) is None


def test_estimate_tokens_from_output_text() -> None:
    usage = estimate_tokens_from_output_text("x" * 80)
    assert usage is not None
    assert usage["output_tokens"] == 20
    assert usage["source"] == "output_estimate"
