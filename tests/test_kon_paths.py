"""Tests for hooks/_kon_paths.py (KON_ROOT resolution)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))

from _kon_paths import (  # noqa: E402
    ensure_project_memory_dir,
    ensure_public_memory_dir,
    hook_log_path,
    install_bundled_paths_module,
    kon_root,
    project_memory_dir,
    public_memory_dir,
    read_config_kon_root,
    write_kon_config,
)


def test_kon_root_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        fake = Path(tmp) / "my-kon"
        fake.mkdir()
        monkeypatch.setenv("KON_ROOT", str(fake))
        monkeypatch.delenv("KON_DATA_DIR", raising=False)
        assert kon_root() == fake.resolve()


def test_kon_root_from_config(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        data_dir = tmp_path / "kon-data"
        data_dir.mkdir()
        fake = tmp_path / "clone"
        fake.mkdir()
        monkeypatch.setenv("KON_DATA_DIR", str(data_dir))
        monkeypatch.delenv("KON_ROOT", raising=False)
        write_kon_config(fake)
        assert read_config_kon_root() == fake.resolve()
        assert kon_root() == fake.resolve()


def test_kon_root_from_package(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KON_ROOT", raising=False)
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("KON_DATA_DIR", str(Path(tmp) / "empty-kon-data"))
        assert kon_root() == ROOT.resolve()


def test_install_bundled_paths_module(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp) / "kon-data"
        monkeypatch.setenv("KON_DATA_DIR", str(data_dir))
        dest = install_bundled_paths_module(ROOT / "hooks" / "_kon_paths.py")
        assert dest.is_file()
        assert dest.name == "_kon_paths.py"


def test_public_and_project_memory_dirs(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp) / "kon-data"
        monkeypatch.setenv("KON_DATA_DIR", str(data_dir))
        pub = ensure_public_memory_dir()
        assert pub == public_memory_dir()
        assert (pub / "MEMORY.md").is_file()
        proj = ensure_project_memory_dir()
        assert proj == project_memory_dir()
        assert (proj / "MEMORY.md").is_file()


def test_hook_log_path(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp).resolve() / "kon-data"
        monkeypatch.setenv("KON_DATA_DIR", str(data_dir))
        path = hook_log_path("init_kon_session")
        assert path == data_dir / "logs" / "init_kon_session.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")
        assert path.read_text(encoding="utf-8") == "ok"
