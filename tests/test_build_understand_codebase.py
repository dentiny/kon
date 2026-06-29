"""Tests for code refs and snippets in understand-codebase build."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_understand_codebase as buc  # noqa: E402


def test_enrich_inserts_snippet_when_source_cited(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    source = project / "foo.py"
    source.write_text("line1\nline2\nline3\n", encoding="utf-8")

    md = """### Widget

| **Source** | `foo.py:2` |
"""
    enriched = buc.enrich_markdown_snippets(md, project)
    assert "```2:2:foo.py" in enriched
    assert "line2" in enriched


def test_linkify_markdown_refs_uses_vscode_url(tmp_path: Path) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    md = "See [`foo.py:10`](foo.py:10) for details."
    out = buc.linkify_markdown_refs(md, project)
    assert "vscode://file/" in out
    assert "foo.py:10" in out


def test_build_study_html_injects_project_path(tmp_path: Path) -> None:
    study = {
        "title": "Study",
        "flashcards": [{"id": "1", "front": "Q", "back": "A", "tags": ["concept"]}],
        "quiz": [
            {
                "id": "q1",
                "question": "Q?",
                "choices": ["a", "b"],
                "answer": 0,
                "explanation": "ok",
            }
        ],
    }
    study_path = tmp_path / "understand-study.json"
    study_path.write_text(json.dumps(study), encoding="utf-8")
    project = tmp_path / "proj"
    project.mkdir()
    out = tmp_path / "understand-study.html"
    buc.build_study_html(study_path, out, project)
    assert str(project) in out.read_text(encoding="utf-8")


def test_build_guide_and_study_from_fixtures(tmp_path: Path) -> None:
    guide = ROOT / "templates" / "understand-guide.md"
    study = ROOT / "templates" / "understand-study.json"
    (tmp_path / "understand-guide.md").write_text(
        guide.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "understand-study.json").write_text(
        study.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "session.json").write_text(
        json.dumps({"project_path": str(tmp_path)}),
        encoding="utf-8",
    )

    outputs = buc.build(tmp_path)
    assert outputs["guide_html"].is_file()
    assert outputs["study_html"].is_file()
    guide_html = outputs["guide_html"].read_text(encoding="utf-8")
    assert "Key concepts" in guide_html
    assert "vscode://file/" in guide_html or "Reference code" in guide_html
