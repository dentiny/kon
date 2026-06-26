"""Tests for build_understand_codebase.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_understand_codebase as buc  # noqa: E402


def test_build_study_html_embeds_flashcards_and_quiz(tmp_path: Path) -> None:
    study = {
        "title": "Test repo study",
        "flashcards": [
            {"id": "1", "front": "Q?", "back": "A.", "tags": ["concept"]},
        ],
        "quiz": [
            {
                "id": "q1",
                "question": "Pick one",
                "choices": ["yes", "no"],
                "answer": 0,
                "explanation": "Because yes.",
            }
        ],
    }
    study_path = tmp_path / "understand-study.json"
    study_path.write_text(json.dumps(study), encoding="utf-8")
    out = tmp_path / "understand-study.html"
    buc.build_study_html(study_path, out)
    html = out.read_text(encoding="utf-8")
    assert "Test repo study" in html
    assert "Flashcards" in html
    assert "Quiz" in html
    assert '"front": "Q?"' in html


def test_build_guide_and_study_from_fixtures(tmp_path: Path) -> None:
    guide = ROOT / "templates" / "understand-guide.md"
    study = ROOT / "templates" / "understand-study.json"
    (tmp_path / "understand-guide.md").write_text(
        guide.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "understand-study.json").write_text(
        study.read_text(encoding="utf-8"), encoding="utf-8"
    )

    outputs = buc.build(tmp_path)
    assert outputs["guide_html"].is_file()
    assert outputs["study_html"].is_file()
    assert "Key concepts" in outputs["guide_html"].read_text(encoding="utf-8")
    assert "flashcards" in outputs["study_html"].read_text(encoding="utf-8")
