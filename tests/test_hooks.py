"""Tests for kon hook scripts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import mio_output, run_hook

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / "hooks"

sys.path.insert(0, str(HOOKS))
from _hook_io import format_payload  # noqa: E402
from _session_paths import SESSION_JSON  # noqa: E402
from no_git_write import is_git_write_blocked  # noqa: E402
from on_subagent_stop import _infer_role  # noqa: E402


def _session_json_path(data_root: Path, sid: str) -> Path:
    return data_root / "projects" / "repo" / "sessions" / sid / SESSION_JSON


def _list_session_files(sessions_dir: Path) -> list[Path]:
    if not sessions_dir.is_dir():
        return []
    files = list(sessions_dir.glob(f"*/{SESSION_JSON}"))
    files.extend(sessions_dir.glob("*.json"))
    return files


class TestHookIo:
    def test_shell_deny(self) -> None:
        payload = format_payload("block", "nope", event="beforeShellExecution")
        assert payload["permission"] == "deny"
        assert payload["user_message"] == "nope"

    def test_stop_followup(self) -> None:
        payload = format_payload("block", "retry please", event="stop")
        assert payload == {"followup_message": "retry please"}

    def test_claude_pre_tool_use_deny(self) -> None:
        payload = format_payload("block", "nope", event="PreToolUse")
        assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert payload["hookSpecificOutput"]["permissionDecisionReason"] == "nope"

    def test_claude_subagent_stop_block(self) -> None:
        payload = format_payload("block", "retry please", event="SubagentStop")
        assert payload == {"decision": "block", "reason": "retry please"}

    def test_claude_pre_tool_use_allow(self) -> None:
        assert format_payload("approve", "", event="PreToolUse") == {}

    def test_legacy_approve(self) -> None:
        payload = format_payload("approve", "ok", event=None)
        assert payload["decision"] == "approve"


class TestNoGitWrite:
    def test_blocks_commit(self) -> None:
        result = run_hook(
            "no_git_write.py",
            {
                "hook_event_name": "beforeShellExecution",
                "command": "git commit -m test",
            },
        )
        assert result["permission"] == "deny"

    @pytest.mark.parametrize(
        "command",
        [
            "git -C . commit -m test",
            "git --git-dir=.git push origin main",
            "git -c user.name=x commit -m test",
            "env FOO=1 git -C repo commit -m test",
        ],
    )
    def test_blocks_git_write_variants(self, command: str) -> None:
        assert is_git_write_blocked(command)

    def test_blocks_commit_pre_tool_use(self) -> None:
        result = run_hook(
            "no_git_write.py",
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "git commit -m test"},
            },
        )
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_allows_status(self) -> None:
        result = run_hook(
            "no_git_write.py",
            {
                "hook_event_name": "beforeShellExecution",
                "command": "git status",
            },
        )
        assert result["permission"] == "allow"

    def test_allows_diff(self) -> None:
        assert not is_git_write_blocked("git -C repo diff")
        assert not is_git_write_blocked("git --git-dir=.git log -1")

    @pytest.mark.parametrize(
        "command",
        [
            'bash -c "git commit -m test"',
            "$(which git) commit -m test",
        ],
    )
    def test_blocks_nested_git_write(self, command: str) -> None:
        assert is_git_write_blocked(command)


class TestOnSubagentStop:
    def test_infers_mio(self) -> None:
        role = _infer_role({"task": "You are Mio reviewer agents/Mio.md", "summary": ""})
        assert role == "Mio"

    def test_blocks_missing_verdict(self) -> None:
        result = run_hook(
            "on_subagent_stop.py",
            {
                "hook_event_name": "subagentStop",
                "status": "completed",
                "task": "Mio reviewer agents/Mio.md",
                "summary": "## Loaded memory entries\n(no relevant entries)\n\nNo verdict here.",
            },
        )
        assert "followup_message" in result
        assert "verdict" in result["followup_message"].lower()

    def test_forwards_usage_from_transcript(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = tmp_path / "repo"
        project.mkdir()
        data_root = tmp_path / "kon-data"
        monkeypatch.setenv("KON_DATA_DIR", str(data_root))
        monkeypatch.setenv("KON_ROOT", str(ROOT))

        sid = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "kon_session.py"),
                "--project",
                str(project),
                "init",
                "--command",
                "/kon:team",
                "--task",
                "usage test",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        azusa_output = (
            "## Loaded memory entries\n(no relevant entries)\n\n"
            "Explored `scripts/kon_session.py` for session usage fields."
        )
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "kon_session.py"),
                "--project",
                str(project),
                "complete-agent",
                "--id",
                sid,
                "--agent",
                "Azusa",
                "--summary",
                azusa_output.splitlines()[0],
            ],
            check=True,
        )

        transcript = tmp_path / "agent.jsonl"
        transcript.write_text(
            json.dumps(
                {
                    "role": "user",
                    "message": {"content": [{"type": "text", "text": "x" * 40}]},
                }
            )
            + "\n"
            + json.dumps(
                {
                    "role": "assistant",
                    "message": {"content": [{"type": "text", "text": azusa_output}]},
                }
            )
            + "\n",
            encoding="utf-8",
        )

        run_hook(
            "on_subagent_stop.py",
            {
                "hook_event_name": "subagentStop",
                "status": "completed",
                "cwd": str(project),
                "task": "Azusa explorer agents/Azusa.md",
                "summary": azusa_output,
                "agent_transcript_path": str(transcript),
            },
        )

        session = json.loads(_session_json_path(data_root, sid).read_text(encoding="utf-8"))
        usage = session["log"][-1]["usage"]
        assert usage["input_tokens"] == 10
        assert usage["output_tokens"] >= 20
        assert usage["total_tokens"] == usage["input_tokens"] + usage["output_tokens"]
        assert session["usage_totals"]["total_tokens"] == usage["total_tokens"]

    def test_hook_records_usage_without_prior_complete_agent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """subagentStop runs before orchestrator — hook must write log + usage itself."""
        project = tmp_path / "repo"
        project.mkdir()
        data_root = tmp_path / "kon-data"
        monkeypatch.setenv("KON_DATA_DIR", str(data_root))
        monkeypatch.setenv("KON_ROOT", str(ROOT))

        sid = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "kon_session.py"),
                "--project",
                str(project),
                "init",
                "--command",
                "/kon:team",
                "--task",
                "yui impl usage",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        yui_output = "🎶 Yui: Milestone 1 complete — changed auth.py, acceptance: ✅"
        transcript = tmp_path / "yui.jsonl"
        transcript.write_text(
            json.dumps(
                {
                    "role": "user",
                    "message": {"content": [{"type": "text", "text": "implement step 1"}]},
                }
            )
            + "\n"
            + json.dumps(
                {
                    "role": "assistant",
                    "message": {"content": [{"type": "text", "text": yui_output}]},
                }
            )
            + "\n",
            encoding="utf-8",
        )

        run_hook(
            "on_subagent_stop.py",
            {
                "hook_event_name": "subagentStop",
                "status": "completed",
                "cwd": str(project),
                "task": "Yui implementer agents/Yui.md",
                "summary": yui_output,
                "agent_transcript_path": str(transcript),
            },
        )

        session = json.loads(_session_json_path(data_root, sid).read_text(encoding="utf-8"))
        assert session["log"][-1]["agent"] == "Yui"
        assert session["log"][-1]["usage"]["total_tokens"] > 0
        assert "Yui" in session["steps_completed"]

        # Orchestrator complete-agent after hook should not duplicate log row
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "kon_session.py"),
                "--project",
                str(project),
                "complete-agent",
                "--id",
                sid,
                "--agent",
                "Yui",
                "--summary",
                "Milestone 1 complete — longer orchestrator summary",
            ],
            check=True,
        )
        session2 = json.loads(_session_json_path(data_root, sid).read_text(encoding="utf-8"))
        assert len(session2["log"]) == 1
        assert "orchestrator summary" in session2["log"][0]["summary"]


class TestTeammateQualityCheck:
    def test_mio_approved(self) -> None:
        result = run_hook(
            "teammate_quality_check.py",
            {"teammate_role": "Mio", "teammate_output": mio_output("APPROVED")},
        )
        assert result["decision"] == "approve"

    def test_mio_rejects_partial_checklist(self) -> None:
        output = (
            "## Loaded memory entries\n(no relevant entries)\n\n"
            "## Verdict\nAPPROVED\n\n"
            "## Checklist\n- [x] item 1\n- [x] item 2\n"
        )
        result = run_hook(
            "teammate_quality_check.py",
            {"teammate_role": "Mio", "teammate_output": output},
        )
        assert result["decision"] == "block"
        assert "checklist" in result["reason"].lower()

    def test_mio_rejects_approved_with_unchecked_item(self) -> None:
        marks = ["x"] * 6 + [" "]
        result = run_hook(
            "teammate_quality_check.py",
            {
                "teammate_role": "Mio",
                "teammate_output": mio_output("APPROVED", checklist_marks=marks),
            },
        )
        assert result["decision"] == "block"
        assert "unchecked" in result["reason"].lower() or "[ ]" in result["reason"]

    def test_mio_rejects_approved_with_must_fix_section(self) -> None:
        result = run_hook(
            "teammate_quality_check.py",
            {
                "teammate_role": "Mio",
                "teammate_output": mio_output(
                    "APPROVED",
                    extra="## Must-fix\n- `foo.py:1` — problem\n",
                ),
            },
        )
        assert result["decision"] == "block"

    def test_jun_with_sources(self) -> None:
        output = (
            "## Loaded memory entries\n(no relevant entries)\n\n"
            "## Research summary\n- `.kon/research.md` — Cursor stop hook docs\n\n"
            "## Sources\n- https://cursor.com/docs/hooks — hook events\n"
        )
        result = run_hook(
            "teammate_quality_check.py",
            {"teammate_role": "Jun", "teammate_output": output},
        )
        assert result["decision"] == "approve"

    def test_mio_review_pr_approves_holistic_sections(self) -> None:
        output = (
            "## Loaded memory entries\n(no relevant entries)\n\n"
            "## Verdict\nNEEDS_CHANGES\n\n"
            "## PR overview\nAuth email validation PR.\n\n"
            "## Code review\n- [ ] edge case missing\n\n"
            "## PR description review\nTest plan is thin.\n\n"
            "## Existing review comments\n- reviewer: add test — partial\n\n"
            "## Linked issues\nFixes #42 — requirements met partially.\n\n"
            "## Must-fix\n- Add empty-email test\n"
        )
        result = run_hook(
            "teammate_quality_check.py",
            {"teammate_role": "Mio", "teammate_output": output},
        )
        assert result["decision"] == "approve"

    def test_mio_review_pr_blocks_missing_section(self) -> None:
        output = (
            "## Loaded memory entries\n(no relevant entries)\n\n"
            "## Verdict\nBLOCKED\n\n"
            "## PR overview\nAuth email validation PR.\n\n"
            "## Code review\n- [ ] edge case missing\n"
        )
        result = run_hook(
            "teammate_quality_check.py",
            {"teammate_role": "Mio", "teammate_output": output},
        )
        assert result["decision"] == "block"
        assert "PR description review" in result["reason"]

    def test_jun_describe_issue_approves(self) -> None:
        output = (
            "## Loaded memory entries\n(no relevant entries)\n\n"
            "## Issue summary\n"
            "- sessions/abc-123/issue-summary.md — signup bug triage\n\n"
            "## Discussion summary\n- reporter sees 500 on empty email\n\n"
            "## Open questions\n- (none)\n"
        )
        result = run_hook(
            "teammate_quality_check.py",
            {"teammate_role": "Jun", "teammate_output": output},
        )
        assert result["decision"] == "approve"

    def test_jun_describe_issue_blocks_missing_path(self) -> None:
        output = (
            "## Loaded memory entries\n(no relevant entries)\n\n"
            "## Issue summary\n- signup bug triage\n\n"
            "## Discussion summary\n- reporter sees 500\n\n"
            "## Open questions\n- (none)\n"
        )
        result = run_hook(
            "teammate_quality_check.py",
            {"teammate_role": "Jun", "teammate_output": output},
        )
        assert result["decision"] == "block"
        assert "issue-summary.md" in result["reason"]

    @pytest.mark.parametrize(
        ("role", "output"),
        [
            pytest.param(
                "Mugi",
                (
                    "## Loaded memory entries\n(no relevant entries)\n\n"
                    "## Goal\nImplement session-scoped tracking.\n\n"
                    "## Steps\n1. Do this\n2. Do that\n\n"
                    "Written plan to `.kon/plan-abc123.md`."
                ),
                id="mugi_session_plan_file",
            ),
            pytest.param(
                "Azusa-challenge",
                (
                    "## Loaded memory entries\n(no relevant entries)\n\n"
                    "Reviewing `.kon/plan-abc123.md` for design challenges.\n\n"
                    "### C1: First challenge\nDetails about C1.\n\n"
                    "### C2: Second challenge\nDetails about C2.\n\n"
                    "### C3: Third challenge\nDetails about C3.\n\n"
                    "Written challenges to `.kon/design-debate-abc123.md`."
                ),
                id="azusa_challenge_session_plan_file",
            ),
            pytest.param(
                "Mugi-revise",
                (
                    "## Loaded memory entries\n(no relevant entries)\n\n"
                    "Updated `.kon/plan-some-id.md` with revisions addressing each challenge.\n\n"
                    "Filled response table in `.kon/design-debate-abc123.md`.\n\n"
                    "| C1 | First challenge | Accepted |\n"
                    "| C2 | Second challenge | Revised |\n"
                ),
                id="mugi_revise_session_plan_file",
            ),
            pytest.param(
                "Azusa-challenge",
                (
                    "## Loaded memory entries\n(no relevant entries)\n\n"
                    "Reviewing `.kon/plan-abc123.md` for design challenges.\n\n"
                    "### C1: First challenge\nDetails about C1.\n\n"
                    "### C2: Second challenge\nDetails about C2.\n\n"
                    "### C3: Third challenge\nDetails about C3.\n\n"
                    "Written challenges to `.kon/design-debate.md`."
                ),
                id="azusa_challenge_legacy_debate_file",
            ),
            pytest.param(
                "Mugi-revise",
                (
                    "## Loaded memory entries\n(no relevant entries)\n\n"
                    "Updated `.kon/plan-some-id.md` with revisions addressing each challenge.\n\n"
                    "Filled response table in `.kon/design-debate.md`.\n\n"
                    "| C1 | First challenge | Accepted |\n"
                    "| C2 | Second challenge | Revised |\n"
                ),
                id="mugi_revise_legacy_debate_file",
            ),
        ],
    )
    def test_session_plan_patterns_approve(self, role: str, output: str) -> None:
        result = run_hook(
            "teammate_quality_check.py",
            {"teammate_role": role, "teammate_output": output},
        )
        assert result["decision"] == "approve"


class TestOnSubagentStopRole:
    def test_infers_jun(self) -> None:
        role = _infer_role({"task": "Jun researcher agents/Jun.md", "summary": ""})
        assert role == "Jun"

    def test_jun_not_june(self) -> None:
        role = _infer_role({"task": "Review schedule for June release", "summary": ""})
        assert role is None


class TestInitKonSession:
    def test_creates_session_on_review_command(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = tmp_path / "repo"
        project.mkdir()
        data_root = tmp_path / "kon-data"
        monkeypatch.setenv("KON_DATA_DIR", str(data_root))
        monkeypatch.setenv("KON_ROOT", str(ROOT))

        result = run_hook(
            "init_kon_session.py",
            {
                "prompt": "/kon:review check dashboard session tracking",
                "cwd": str(project),
            },
        )
        assert result == {"continue": True}

        sessions_dir = data_root / "projects" / "repo" / "sessions"
        files = _list_session_files(sessions_dir)
        assert len(files) == 1
        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert data["command"] == "/kon:review"
        assert data["status"] == "in_progress"
        assert data["steps_pending"] == ["Mio"]

    def test_skips_plain_prompt(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        project = tmp_path / "repo"
        project.mkdir()
        data_root = tmp_path / "kon-data"
        monkeypatch.setenv("KON_DATA_DIR", str(data_root))
        monkeypatch.setenv("KON_ROOT", str(ROOT))

        result = run_hook(
            "init_kon_session.py",
            {"prompt": "fix the bug in dashboard.py", "cwd": str(project)},
        )
        assert result == {"continue": True}
        sessions_dir = data_root / "projects" / "repo" / "sessions"
        assert not sessions_dir.exists() or not _list_session_files(sessions_dir)

    def test_skips_todo_command(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        project = tmp_path / "repo"
        project.mkdir()
        data_root = tmp_path / "kon-data"
        monkeypatch.setenv("KON_DATA_DIR", str(data_root))
        monkeypatch.setenv("KON_ROOT", str(ROOT))

        result = run_hook(
            "init_kon_session.py",
            {"prompt": "/kon:todo add rate limiting", "cwd": str(project)},
        )
        assert result == {"continue": True}
        sessions_dir = data_root / "projects" / "repo" / "sessions"
        assert not sessions_dir.exists() or not _list_session_files(sessions_dir)

    def test_uses_last_workspace_when_stdin_has_no_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Reproduces the real Cursor case: beforeSubmitPrompt stdin only has
        # `prompt` and `attachments`; the resolver must fall back to
        # ~/.kon/last_workspace.json (written by sessionStart).
        project = tmp_path / "myrepo"
        project.mkdir()
        data_root = tmp_path / "kon-data"
        monkeypatch.setenv("KON_DATA_DIR", str(data_root))
        monkeypatch.setenv("KON_ROOT", str(ROOT))

        data_root.mkdir()
        (data_root / "last_workspace.json").write_text(
            json.dumps({"project_path": str(project), "repo_name": "myrepo"}),
            encoding="utf-8",
        )

        result = run_hook(
            "init_kon_session.py",
            {"prompt": "/kon:review just diff", "attachments": []},
        )
        assert result == {"continue": True}

        sessions_dir = data_root / "projects" / "myrepo" / "sessions"
        files = _list_session_files(sessions_dir)
        assert len(files) == 1, f"expected 1 session, got {files}"
        session = json.loads(files[0].read_text(encoding="utf-8"))
        assert session["command"] == "/kon:review"
        assert session["project_path"] == str(project.resolve())

    def test_skips_init_when_begin_session_open(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = tmp_path / "repo"
        project.mkdir()
        data_root = tmp_path / "kon-data"
        monkeypatch.setenv("KON_DATA_DIR", str(data_root))
        monkeypatch.setenv("KON_ROOT", str(ROOT))

        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "kon_session.py"),
                "--project",
                str(project),
                "init",
                "--command",
                "/kon:begin",
                "--task",
                "interactive",
            ],
            check=True,
        )

        result = run_hook(
            "init_kon_session.py",
            {
                "prompt": "/kon:team implement feature",
                "cwd": str(project),
            },
        )
        assert result == {"continue": True}

        sessions_dir = data_root / "projects" / "repo" / "sessions"
        files = _list_session_files(sessions_dir)
        assert len(files) == 1
        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert data["command"] == "/kon:begin"
        assert data["status"] == "in_progress"

    def test_ensure_project_dir_writes_last_workspace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = tmp_path / "myrepo"
        project.mkdir()
        data_root = tmp_path / "kon-data"
        monkeypatch.setenv("KON_DATA_DIR", str(data_root))
        monkeypatch.setenv("KON_ROOT", str(ROOT))

        result = run_hook(
            "ensure_project_dir.py",
            {"cwd": str(project)},
        )
        assert result["ok"] is True

        last = data_root / "last_workspace.json"
        assert last.is_file()
        payload = json.loads(last.read_text(encoding="utf-8"))
        assert payload["project_path"] == str(project.resolve())


class TestBeginAutoLog:
    def _init_begin(self, project: Path, data_root: Path) -> str:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "kon_session.py"),
                "--project",
                str(project),
                "init",
                "--command",
                "/kon:begin",
                "--task",
                "interactive session",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return proc.stdout.strip()

    def test_log_begin_prompt_records_plain_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = tmp_path / "repo"
        project.mkdir()
        data_root = tmp_path / "kon-data"
        monkeypatch.setenv("KON_DATA_DIR", str(data_root))
        monkeypatch.setenv("KON_ROOT", str(ROOT))
        sid = self._init_begin(project, data_root)

        result = run_hook(
            "log_begin_prompt.py",
            {"prompt": "can you check the failing test?", "cwd": str(project)},
        )
        assert result == {"continue": True}

        data = json.loads(_session_json_path(data_root, sid).read_text())
        last = data["log"][-1]
        assert last["agent"] == "User"
        assert last["summary"] == "can you check the failing test?"
        assert "ts" in last
        assert data["turns"] == [{"n": 1, "summary": "can you check the failing test?"}]

    def test_log_begin_prompt_skips_without_begin_session(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = tmp_path / "repo"
        project.mkdir()
        data_root = tmp_path / "kon-data"
        monkeypatch.setenv("KON_DATA_DIR", str(data_root))
        monkeypatch.setenv("KON_ROOT", str(ROOT))

        result = run_hook(
            "log_begin_prompt.py",
            {"prompt": "plain chat", "cwd": str(project)},
        )
        assert result == {"continue": True}
        sessions_dir = data_root / "projects" / "repo" / "sessions"
        assert not sessions_dir.exists() or not _list_session_files(sessions_dir)

    def test_log_begin_response_records_assistant_reply(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = tmp_path / "repo"
        project.mkdir()
        data_root = tmp_path / "kon-data"
        monkeypatch.setenv("KON_DATA_DIR", str(data_root))
        monkeypatch.setenv("KON_ROOT", str(ROOT))
        sid = self._init_begin(project, data_root)

        result = run_hook(
            "log_begin_response.py",
            {
                "text": "The test fails because KUBECONFIG is unset in CI.\n\nNext steps: …",
                "cwd": str(project),
            },
        )
        assert result == {}

        data = json.loads(_session_json_path(data_root, sid).read_text())
        assert data["log"][-1]["agent"] == "Assistant"
        assert data["log"][-1]["summary"] == "The test fails because KUBECONFIG is unset in CI."


class TestPreCompactHook:
    def test_records_context_profile(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        data_root = tmp_path / "kon-data"
        monkeypatch.setenv("KON_DATA_DIR", str(data_root))
        monkeypatch.setenv("KON_ROOT", str(ROOT))

        result = run_hook(
            "on_pre_compact.py",
            {
                "hook_event_name": "preCompact",
                "context_window_size": 128000,
                "context_tokens": 110000,
                "context_usage_percent": 85.9,
                "trigger": "auto",
            },
        )
        assert result.get("decision") == "approve"

        profile = json.loads((data_root / "context_profile.json").read_text())
        assert profile["context_window_size"] == 128000
        assert profile["context_tokens"] == 110000
        assert profile["source"] == "preCompact"


class TestRecordOrchestratorModelHook:
    def test_records_model_on_profile(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        data_root = tmp_path / "kon-data"
        monkeypatch.setenv("KON_DATA_DIR", str(data_root))
        monkeypatch.setenv("KON_ROOT", str(ROOT))

        result = run_hook(
            "record_orchestrator_model.py",
            {
                "hook_event_name": "beforeSubmitPrompt",
                "prompt": "hello",
                "model": "claude-opus-4-8-thinking-high",
                "model_id": "claude-opus-4-8",
                "model_params": [{"id": "thinking", "value": "true"}],
            },
        )
        assert result.get("continue") is True

        profile = json.loads((data_root / "context_profile.json").read_text())
        assert profile["orchestrator_model"] == "claude-opus-4-8-thinking-high"
        assert profile["orchestrator_model_id"] == "claude-opus-4-8"
