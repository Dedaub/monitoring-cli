"""Unit/regression tests for the CLI stdin handling and install-skill.

These are hermetic — no network, no real auth. They pin the behaviour the
session's changes introduced: the idle-stdin hang guard (_read_ready_stdin),
write-query's fail-fast on no input, _resolve_query_text_and_owner's
single-fetch stored fallback, and install-skill shipping the whole
references/ tree (and pruning orphans on re-install).
"""

import contextlib
import io
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from monitoring_cli import cli
from monitoring_cli.cli import app

runner = CliRunner()


class _FakeStdin(io.StringIO):
    def __init__(self, data: str = "", *, tty: bool = False) -> None:
        super().__init__(data)
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


@pytest.fixture
def fake_stdin(monkeypatch):
    """Install a fake stdin + a controllable select() on the cli module."""

    def _install(data="", *, tty=False, ready=True, select_error=None):
        monkeypatch.setattr(cli.sys, "stdin", _FakeStdin(data, tty=tty))

        def _fake_select(rlist, wlist, xlist, timeout):
            if select_error is not None:
                raise select_error
            return ([cli.sys.stdin], [], []) if ready else ([], [], [])

        monkeypatch.setattr(cli.select, "select", _fake_select)

    return _install


# --- _read_ready_stdin: the idle-stdin hang guard -------------------------


def test_read_ready_stdin_empty_for_tty(fake_stdin):
    fake_stdin("ignored", tty=True)
    assert cli._read_ready_stdin() == ""


def test_read_ready_stdin_empty_for_idle_pipe(fake_stdin):
    # data is buffered but select reports not-ready -> no hang, no read
    fake_stdin("buffered but not ready", ready=False)
    assert cli._read_ready_stdin() == ""


def test_read_ready_stdin_reads_when_data_ready(fake_stdin):
    fake_stdin("SELECT 1", ready=True)
    assert cli._read_ready_stdin() == "SELECT 1"


def test_read_ready_stdin_empty_on_eof(fake_stdin):
    fake_stdin("", ready=True)
    assert cli._read_ready_stdin() == ""


@pytest.mark.parametrize(
    "exc", [OSError("win pipe"), ValueError("closed")], ids=["oserror", "valueerror"]
)
def test_read_ready_stdin_blocking_fallback_when_select_unsupported(fake_stdin, exc):
    # platforms where select() can't poll stdin fall back to a blocking read
    fake_stdin("WINPIPE", select_error=exc)
    assert cli._read_ready_stdin() == "WINPIPE"


# --- write-query: fail fast instead of blocking/empty-write ---------------


def test_write_query_fails_fast_on_empty_stdin(fake_stdin):
    fake_stdin("", ready=False)  # idle, non-tty pipe; no positional SQL
    result = runner.invoke(app, ["write-query", "--id", "42"])
    assert result.exit_code == 1
    out = result.output
    with contextlib.suppress(ValueError, AttributeError):
        out += result.stderr
    assert "No query text provided" in out


# --- _resolve_query_text_and_owner: single-fetch stored fallback ----------


def _client(text="SELECT stored", entity_id=7):
    client = MagicMock()
    client.get_query.return_value = {
        "query_text": text,
        "owner": {"entity_id": entity_id},
    }
    return client


def test_resolve_falls_back_to_stored_when_stdin_blank(fake_stdin):
    fake_stdin("   \n  ", ready=True)  # whitespace-only piped -> stored fallback
    client = _client()
    text, eid = cli._resolve_query_text_and_owner(client, 42, None, None)
    assert (text, eid) == ("SELECT stored", 7)
    assert client.get_query.call_count == 1  # fetched once, not twice


def test_resolve_prefers_piped_stdin(fake_stdin):
    fake_stdin("SELECT piped", ready=True)
    client = _client()
    text, eid = cli._resolve_query_text_and_owner(client, 42, None, None)
    assert (text, eid) == ("SELECT piped", 7)
    assert client.get_query.call_count == 1  # only for the entity id


def test_resolve_explicit_arg_skips_stdin(fake_stdin):
    fake_stdin("SELECT piped ignored", ready=True)
    client = _client()
    text, eid = cli._resolve_query_text_and_owner(client, 42, "SELECT explicit", None)
    assert (text, eid) == ("SELECT explicit", 7)
    assert client.get_query.call_count == 1  # only for the entity id


def test_resolve_no_fetch_when_text_and_entity_supplied(fake_stdin):
    fake_stdin("ignored", ready=True)
    client = MagicMock()
    text, eid = cli._resolve_query_text_and_owner(client, 42, "SELECT explicit", 9)
    assert (text, eid) == ("SELECT explicit", 9)
    assert client.get_query.call_count == 0


# --- validate-query: fail-fast gate exit codes ----------------------------


def _patch_client(monkeypatch, client):
    monkeypatch.setattr(cli, "_load_client", lambda profile: (client, MagicMock()))


def test_validate_query_ok_exits_zero(monkeypatch):
    client = MagicMock()
    client.validate_query.return_value = True
    _patch_client(monkeypatch, client)
    # positional SQL + --entity-id => no stored-query fetch needed
    result = runner.invoke(
        app, ["validate-query", "--id", "9", "--entity-id", "7", "SELECT 1"]
    )
    assert result.exit_code == 0, result.output
    assert "valid" in result.output


def test_validate_query_bad_exits_one(monkeypatch):
    import httpx

    client = MagicMock()
    req = httpx.Request("POST", "https://x/api/tsql/query/validate")
    client.validate_query.side_effect = httpx.HTTPStatusError(
        "syntax error at or near SELEKT",
        request=req,
        response=httpx.Response(400, request=req),
    )
    _patch_client(monkeypatch, client)
    result = runner.invoke(
        app, ["validate-query", "--id", "9", "--entity-id", "7", "SELEKT 1"]
    )
    assert result.exit_code == 1


def test_generate_query_failed_exits_clean(monkeypatch):
    # A "failed" job must surface its own message and exit 1 — NOT get re-wrapped
    # by the generic except-Exception handler (typer.Exit subclasses Exception).
    client = MagicMock()
    client.generate_query.return_value = {"job_id": "j1", "status": "running"}
    client.get_generation_job.return_value = {
        "job_id": "j1",
        "status": "failed",
        "error": "boom",
    }
    _patch_client(monkeypatch, client)
    result = runner.invoke(app, ["generate-query", "test"])
    assert result.exit_code == 1
    out = result.output
    with contextlib.suppress(ValueError, AttributeError):
        out += result.stderr
    assert "boom" in out
    assert "Error: " not in out  # the generic handler must not have re-wrapped it


def test_query_columns_renders_table(monkeypatch):
    client = MagicMock()
    client.query_columns.return_value = [
        {"column_name": "chain_id", "column_type": "int4"},
    ]
    _patch_client(monkeypatch, client)
    result = runner.invoke(
        app, ["query-columns", "--id", "9", "--entity-id", "7", "SELECT 1 AS chain_id"]
    )
    assert result.exit_code == 0, result.output
    assert "chain_id" in result.output


# --- install-skill: ships SKILL.md + the whole references/ tree -----------


def test_install_skill_copies_skill_and_references(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(app, ["install-skill"])
    assert result.exit_code == 0, result.output
    dest = tmp_path / ".claude" / "skills" / "dedaub-monitoring"
    assert (dest / "SKILL.md").read_text(encoding="utf-8").strip()
    refs = dest / "references"
    assert refs.is_dir()
    assert (refs / "database").is_dir()
    assert any(refs.rglob("*.md"))


def test_install_skill_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert runner.invoke(app, ["install-skill"]).exit_code == 0
    assert runner.invoke(app, ["install-skill"]).exit_code == 0


def test_install_skill_prunes_orphaned_references(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    dest = tmp_path / ".claude" / "skills" / "dedaub-monitoring"
    assert runner.invoke(app, ["install-skill"]).exit_code == 0
    orphan = dest / "references" / "_stale_orphan.md"
    orphan.write_text("stale", encoding="utf-8")
    assert runner.invoke(app, ["install-skill"]).exit_code == 0
    assert not orphan.exists(), "re-install should prune orphaned reference files"


# --- install-skill: multi-agent targets -----------------------------------


def test_install_skill_default_is_claude_only(tmp_path, monkeypatch):
    """No flags, no other agent dirs present -> claude only (backward compat)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    assert runner.invoke(app, ["install-skill"]).exit_code == 0
    assert (tmp_path / ".claude" / "skills" / "dedaub-monitoring" / "SKILL.md").exists()
    assert not (tmp_path / ".codex" / "skills" / "dedaub-monitoring").exists()


def test_install_skill_default_adds_detected_agents(tmp_path, monkeypatch):
    """No flags: claude + any other agent whose home dir already exists."""
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".codex").mkdir()  # pretend Codex is installed
    assert runner.invoke(app, ["install-skill"]).exit_code == 0
    assert (tmp_path / ".claude" / "skills" / "dedaub-monitoring" / "SKILL.md").exists()
    assert (tmp_path / ".codex" / "skills" / "dedaub-monitoring" / "SKILL.md").exists()


def test_install_skill_explicit_agent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(app, ["install-skill", "--agent", "cursor"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".cursor" / "skills" / "dedaub-monitoring" / "SKILL.md").exists()
    # an explicit choice should NOT also install to claude
    assert not (tmp_path / ".claude" / "skills" / "dedaub-monitoring").exists()


def test_install_skill_all_targets(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert runner.invoke(app, ["install-skill", "--all"]).exit_code == 0
    for sub in (".claude", ".codex", ".cursor", ".agents"):
        assert (tmp_path / sub / "skills" / "dedaub-monitoring" / "SKILL.md").exists()


def test_install_skill_unknown_agent_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(app, ["install-skill", "--agent", "bogus"])
    assert result.exit_code == 1


def test_install_skill_empty_selection_installs_nothing(tmp_path, monkeypatch):
    """An empty picker selection installs nothing and exits non-zero."""
    monkeypatch.setenv("HOME", str(tmp_path))
    # Resolve to no targets (as an empty picker selection would).
    monkeypatch.setattr(cli, "_resolve_skill_targets", lambda agent, all_agents: [])
    result = runner.invoke(app, ["install-skill"])
    assert result.exit_code == 1
    assert not (tmp_path / ".claude" / "skills" / "dedaub-monitoring").exists()
