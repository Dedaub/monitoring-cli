"""Unit/regression tests for the CLI stdin handling and install-skill.

These are hermetic — no network, no real auth. They pin the behaviour the
session's changes introduced: the idle-stdin hang guard (_read_ready_stdin),
write-query's fail-fast on no input, _resolve_query_text_and_owner's
single-fetch stored fallback, and install-skill shipping the whole
references/ tree (and pruning orphans on re-install).
"""

import base64
import contextlib
import io
import json
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


def _run_query_client(monkeypatch):
    client = MagicMock()
    client.execute_query.return_value = []
    _patch_client(monkeypatch, client)
    return client


@pytest.mark.parametrize("flag", ["--end-time", "--start-time"])
def test_run_query_end_time_anchors_window_end(monkeypatch, flag):
    # The server's default_start_time is the END of the window ([t - duration, t]);
    # --start-time survives only as a hidden alias that maps to the same field.
    client = _run_query_client(monkeypatch)
    result = runner.invoke(
        app,
        ["run-query", "--id", "9", "--entity-id", "7", flag, "2026-10-01T12:00:00Z"]
        + ["SELECT 1"],
    )
    assert result.exit_code == 0, result.output
    kwargs = client.execute_query.call_args.kwargs
    assert kwargs["default_start_time"] == "2026-10-01T12:00:00Z"


def test_run_query_rejects_both_end_and_start_time(monkeypatch):
    client = _run_query_client(monkeypatch)
    result = runner.invoke(
        app,
        ["run-query", "--id", "9", "--entity-id", "7", "SELECT 1"]
        + ["--end-time", "2026-10-01T12:00:00Z", "--start-time", "2026-10-01T11:00Z"],
    )
    assert result.exit_code == 2
    client.execute_query.assert_not_called()


def test_run_query_help_documents_end_time_not_start_time():
    # Inspect the option metadata, not the rendered help: CI forces Rich colour,
    # and the ANSI codes split "--end-time" in the output.
    import typer.main

    params = {
        p.name: p for p in typer.main.get_command(app).commands["run-query"].params
    }
    assert "--end-time" in params["end_time"].opts
    assert not params["end_time"].hidden
    assert "END of the window" in params["end_time"].help
    assert params["start_time"].hidden


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


# --- headless auth: env token, rotation storage, token command -------------


@pytest.fixture
def config_path(tmp_path, monkeypatch):
    path = tmp_path / "monitoring.json"
    monkeypatch.setattr("monitoring_cli.config.CONFIG_PATH", path)
    monkeypatch.delenv(cli.REFRESH_TOKEN_ENV, raising=False)
    return path


def _save_profile(refresh_token: str = "stored") -> None:
    profile = cli.Profile(
        base_url="https://staging.example.com",
        oidc_host="https://auth.example.com",
        client_id="c",
        refresh_token=refresh_token,
    )
    cli.Config(default="prod", profiles={"prod": profile}).save()


def test_env_token_works_without_config(config_path, monkeypatch):
    monkeypatch.setenv(cli.REFRESH_TOKEN_ENV, "env-tok")
    _, profile = cli._load_client(None)
    assert profile.refresh_token == "env-tok"
    assert profile.base_url == cli.DEFAULT_BASE_URL
    assert not config_path.exists()


def test_env_token_overrides_stored_token(config_path, monkeypatch):
    _save_profile()
    monkeypatch.setenv(cli.REFRESH_TOKEN_ENV, "env-tok")
    _, profile = cli._load_client(None)
    assert profile.refresh_token == "env-tok"
    assert profile.base_url == "https://staging.example.com"
    assert cli.Config.load().get_profile().refresh_token == "stored"


def test_store_refresh_token_persists_rotation(config_path):
    _save_profile()
    cli._store_refresh_token("prod", "rotated")
    assert cli.Config.load().get_profile("prod").refresh_token == "rotated"


def test_store_refresh_token_ignores_missing_profile(config_path):
    cli._store_refresh_token("prod", "rotated")  # no config: no error
    assert not config_path.exists()


def test_token_command_prints_stored_token(config_path):
    _save_profile("secret-tok")
    result = runner.invoke(app, ["token"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "secret-tok"


def test_token_command_fails_when_logged_out(config_path):
    result = runner.invoke(app, ["token"])
    assert result.exit_code == 1


def test_logout_revokes_and_removes_profile(config_path, monkeypatch):
    _save_profile("stored")
    seen = []
    monkeypatch.setattr(
        cli, "revoke_token", lambda profile: seen.append(profile.refresh_token)
    )
    result = runner.invoke(app, ["logout"])
    assert result.exit_code == 0
    assert seen == ["stored"]
    assert cli.Config.load().profiles == {}


def test_logout_removes_profile_when_revoke_fails(config_path, monkeypatch):
    _save_profile()

    def fake(profile):
        raise cli.AuthError("down")

    monkeypatch.setattr(cli, "revoke_token", fake)
    result = runner.invoke(app, ["logout"])
    assert result.exit_code == 0
    out = result.output
    with contextlib.suppress(ValueError, AttributeError):
        out += result.stderr
    assert "could not revoke" in out
    assert cli.Config.load().profiles == {}


def test_logout_local_skips_revoke(config_path, monkeypatch):
    _save_profile()

    def fake(profile):
        raise AssertionError("revoke_token must not be called")

    monkeypatch.setattr(cli, "revoke_token", fake)
    result = runner.invoke(app, ["logout", "--local"])
    assert result.exit_code == 0
    assert cli.Config.load().profiles == {}


def test_session_expired_message_for_login(config_path):
    assert "dedaub-monitoring login" in cli._session_expired_message()


def test_session_expired_message_for_env_token(config_path, monkeypatch):
    monkeypatch.setenv(cli.REFRESH_TOKEN_ENV, "secret-env-tok")
    msg = cli._session_expired_message()
    assert "DEDAUB_MONITORING_REFRESH_TOKEN" in msg
    assert "dedaub-monitoring token" in msg
    assert "secret-env-tok" not in msg


def test_exit_error_uses_env_message(config_path, monkeypatch, capsys):
    monkeypatch.setenv(cli.REFRESH_TOKEN_ENV, "secret-env-tok")
    with pytest.raises(cli.typer.Exit):
        cli._exit_error(cli.SessionExpiredError())
    assert "dedaub-monitoring token" in capsys.readouterr().err


def test_store_refresh_token_warns_on_write_failure(config_path, monkeypatch, capsys):
    _save_profile()

    def boom(self):
        raise OSError("read-only")

    monkeypatch.setattr(cli.Config, "save", boom)
    cli._store_refresh_token("prod", "rotated")
    err_text = capsys.readouterr().err
    assert "could not save" in err_text
    assert "rotated" not in err_text


def test_store_refresh_token_silent_when_logged_out(config_path, capsys):
    cli._store_refresh_token("prod", "rotated")
    assert capsys.readouterr().err == ""


# --- login: offline token warning -------------------------------------------


def _jwt(claims: dict) -> str:
    def seg(obj: dict) -> str:
        raw = json.dumps(obj).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{seg({'alg': 'none'})}.{seg(claims)}.sig"


def _patch_login(monkeypatch, token: str) -> None:
    monkeypatch.setattr(
        cli,
        "start_device_flow",
        lambda p: {"verification_uri_complete": "https://x", "device_code": "d"},
    )
    monkeypatch.setattr(cli, "poll_token", lambda *a, **k: token)


def test_login_warns_without_offline_token(config_path, monkeypatch):
    token = _jwt({"typ": "Refresh"})
    _patch_login(monkeypatch, token)
    result = runner.invoke(app, ["login"])
    assert result.exit_code == 0
    out = result.output
    with contextlib.suppress(ValueError, AttributeError):
        out += result.stderr
    assert "offline_access" in out
    assert token not in out
    assert cli.Config.load().get_profile("prod").refresh_token == token


def test_login_silent_with_offline_token(config_path, monkeypatch):
    _patch_login(monkeypatch, _jwt({"typ": "Offline"}))
    result = runner.invoke(app, ["login"])
    assert result.exit_code == 0
    out = result.output
    with contextlib.suppress(ValueError, AttributeError):
        out += result.stderr
    assert "Warning" not in out


# --- dashboards and widgets ---------------------------------------------------


def _widget_client(monkeypatch, *, scheduled=False, notify=False, columns=None):
    client = MagicMock()
    client.get_query.return_value = {
        "query_id": 9,
        "query_name": "Fees",
        "query_text": "select day, fee from t",
        "owner": {"username": "alice", "entity_id": 7},
        "default_network": "ethereum",
        "is_scheduled": scheduled,
        "key": "k-9",
    }
    client.query_columns.return_value = [
        {"column_name": c, "column_type": t}
        for c, t in (columns or [("day", "timestamp"), ("fee", "numeric")])
    ]
    client.get_notify_config.return_value = {"notify": notify}
    client.create_widget.return_value = {"widget_id": 12, "dashboard_ids": [3]}
    client.update_widget.return_value = {"widget_id": 12}
    profile = cli.Profile(
        base_url="https://api.dedaub.com", oidc_host="https://auth", client_id="c"
    )
    monkeypatch.setattr(cli, "_load_client", lambda name: (client, profile))
    return client


def _all_output(result) -> str:
    out = result.output
    with contextlib.suppress(ValueError, AttributeError):
        out += result.stderr
    return out


def test_create_widget_sends_the_web_apps_body(monkeypatch):
    client = _widget_client(monkeypatch)
    result = runner.invoke(
        app,
        ["create-widget", "--query-id", "9", "--type", "line", "--x", "day"]
        + ["--y", "fee", "--y-label", "Fee $\\mu$", "--dashboard-id", "3"],
    )
    assert result.exit_code == 0, _all_output(result)
    body = client.create_widget.call_args.args[0]
    assert body == {
        "label": "Fees",
        "category": "VIEW",
        "type": "line",
        "query_ids": [9],
        "query_keys": ["k-9"],
        "config": {
            "timeframe": "30d",
            "sorting_order": "ASC",
            "decimals": "2",
            "x_axis_name": "day",
            "y_axis_name": "fee",
            "y_label": "Fee $\\mu$",
        },
        "dashboard_ids": [3],
        "x": 0,
        "y": 0,
        "width": 4,
        "height": 4,
    }
    assert "Created widget (id: 12)" in result.output
    assert "https://app.dedaub.com/widget/12" in result.output
    assert "https://app.dedaub.com/dashboard/3" in result.output


@pytest.mark.parametrize(
    ("scheduled", "notify", "category"),
    [
        (True, False, "MATERIALIZED"),
        (False, True, "MATERIALIZED"),
        (False, False, "VIEW"),
    ],
)
def test_create_widget_category(monkeypatch, scheduled, notify, category):
    client = _widget_client(monkeypatch, scheduled=scheduled, notify=notify)
    result = runner.invoke(app, ["create-widget", "--query-id", "9", "--type", "table"])
    assert result.exit_code == 0, _all_output(result)
    body = client.create_widget.call_args.args[0]
    assert body["category"] == category
    assert (body["width"], body["height"]) == (8, 6)


def test_create_widget_flags_win_over_camel_case_config(monkeypatch, tmp_path):
    client = _widget_client(monkeypatch)
    cfg = tmp_path / "c.json"
    cfg.write_text(
        json.dumps({"xAxisName": "fee", "yAxisName": "fee", "numberFormat": "full"})
    )
    result = runner.invoke(
        app,
        ["create-widget", "--query-id", "9", "--type", "bar", "--x", "day"]
        + ["--config", str(cfg), "--label", "**Fees**"],
    )
    assert result.exit_code == 0, _all_output(result)
    body = client.create_widget.call_args.args[0]
    assert body["label"] == "**Fees**"
    assert body["config"]["x_axis_name"] == "day"
    assert body["config"]["y_axis_name"] == "fee"
    assert body["config"]["number_format"] == "full"


def test_create_widget_reads_config_from_stdin(monkeypatch, fake_stdin):
    client = _widget_client(monkeypatch)
    # CliRunner puts `input` on stdin; the fixture makes select() report it ready.
    fake_stdin(ready=True)
    result = runner.invoke(
        app,
        ["create-widget", "--query-id", "9", "--type", "scatter", "--config", "-"],
        input='{"x_axis_name": "day", "y_axis_name": "fee"}',
    )
    assert result.exit_code == 0, _all_output(result)
    assert client.create_widget.call_args.args[0]["config"]["y_axis_name"] == "fee"


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--type", "line", "--x", "day"], "Choose the Y-axis column"),
        (["--type", "pie"], "Choose the column to count"),
        (["--type", "line", "--x", "day", "--y", "gone"], "no column 'gone'"),
        (
            ["--type", "line", "--x", "day", "--y", "fee", "--timeframe", "1h"],
            "timeframe",
        ),
        (["--type", "donut"], "Unknown widget type"),
        (["--type", "line", "--x", "day", "--y", "fee", "--x-label", "a" * 121], "121"),
    ],
)
def test_create_widget_refuses_a_problem(monkeypatch, args, message):
    client = _widget_client(monkeypatch)
    result = runner.invoke(app, ["create-widget", "--query-id", "9", *args])
    assert result.exit_code == 1
    assert message in _all_output(result)
    client.create_widget.assert_not_called()


def test_create_widget_force_skips_only_the_column_checks(monkeypatch, tmp_path):
    client = _widget_client(monkeypatch)
    result = runner.invoke(
        app,
        ["create-widget", "--query-id", "9", "--type", "line", "--x", "day"]
        + ["--y", "gone", "--force"],
    )
    assert result.exit_code == 0, _all_output(result)
    client.query_columns.assert_not_called()
    cfg = tmp_path / "c.json"
    cfg.write_text('{"colour": "red"}')
    result = runner.invoke(
        app,
        ["create-widget", "--query-id", "9", "--type", "line", "--x", "day"]
        + ["--y", "fee", "--config", str(cfg), "--force"],
    )
    assert result.exit_code == 1
    assert "Unknown config key 'colour'" in _all_output(result)


def test_create_widget_bad_config_json(monkeypatch, tmp_path):
    client = _widget_client(monkeypatch)
    cfg = tmp_path / "c.json"
    cfg.write_text("[1, 2]")
    result = runner.invoke(
        app,
        ["create-widget", "--query-id", "9", "--type", "table", "--config", str(cfg)],
    )
    assert result.exit_code == 1
    assert "JSON object" in _all_output(result)
    client.create_widget.assert_not_called()


def _stored_widget():
    return {
        "widget_id": 12,
        "dashboard_id": 3,
        "label": "Old",
        "category": "MATERIALIZED",
        "type": "line",
        "query_ids": [9],
        "query_keys": ["k-9"],
        "config": {"x_axis_name": "day", "y_axis_name": "fee", "x_label": "Day"},
        "x": 4,
        "y": 6,
        "width": 8,
        "height": 6,
    }


def test_update_widget_merges_the_stored_config(monkeypatch):
    client = _widget_client(monkeypatch)
    client.get_widget.return_value = _stored_widget()
    result = runner.invoke(
        app,
        ["update-widget", "--id", "12", "--type", "bar", "--y-label", "Fee"]
        + ["--clear", "xLabel"],
    )
    assert result.exit_code == 0, _all_output(result)
    widget_id, body = client.update_widget.call_args.args
    assert widget_id == 12
    assert body["dashboard_id"] is None  # no place changes
    assert body == {
        "dashboard_id": None,
        "label": "Old",
        "category": "MATERIALIZED",
        "type": "bar",
        "query_ids": [9],
        "query_keys": ["k-9"],
        "config": {"x_axis_name": "day", "y_axis_name": "fee", "y_label": "Fee"},
        "x": 0,
        "y": 0,
        "width": 6,
        "height": 4,
    }
    assert "https://app.dedaub.com/widget/12" in result.output


def test_update_widget_refuses_a_problem(monkeypatch):
    client = _widget_client(monkeypatch)
    client.get_widget.return_value = _stored_widget()
    result = runner.invoke(
        app, ["update-widget", "--id", "12", "--clear", "y_axis_name"]
    )
    assert result.exit_code == 1
    client.update_widget.assert_not_called()


def test_check_widget_exit_codes(monkeypatch):
    _widget_client(monkeypatch)
    ok = runner.invoke(
        app,
        ["check-widget", "--query-id", "9", "--type", "histogram", "--x", "fee"],
    )
    assert ok.exit_code == 0, _all_output(ok)
    assert '"x_axis_name": "fee"' in ok.output
    bad = runner.invoke(app, ["check-widget", "--query-id", "9", "--type", "value"])
    assert bad.exit_code == 1
    assert "Choose the column to show (--y)" in _all_output(bad)


def test_check_widget_needs_an_id_or_a_query_and_type(monkeypatch):
    client = _widget_client(monkeypatch)
    result = runner.invoke(app, ["check-widget", "--query-id", "9"])
    assert result.exit_code == 2
    client.get_query.assert_not_called()


def test_check_widget_reports_unreadable_columns(monkeypatch):
    import httpx

    client = _widget_client(monkeypatch)
    req = httpx.Request("POST", "https://x/api/tsql/query/metadata")
    client.query_columns.side_effect = httpx.HTTPStatusError(
        "syntax error", request=req, response=httpx.Response(400, request=req)
    )
    result = runner.invoke(
        app, ["check-widget", "--query-id", "9", "--type", "pie", "--x", "day"]
    )
    assert result.exit_code == 1
    assert "Cannot read the query columns" in _all_output(result)


def test_preview_widget_sql_does_not_run(monkeypatch):
    client = _widget_client(monkeypatch)
    result = runner.invoke(
        app,
        ["preview-widget", "--query-id", "9", "--type", "line", "--x", "day"]
        + ["--y", "fee", "--sql"],
    )
    assert result.exit_code == 0, _all_output(result)
    assert '{{ ref(table="alice::Fees") }}' in result.output
    assert "select day, fee from t" in result.output
    client.execute_query.assert_not_called()


def test_preview_widget_falls_back_to_the_query_text(monkeypatch):
    client = _widget_client(monkeypatch)
    client.execute_query.side_effect = [
        RuntimeError(
            "The query you requested does not exist, or has not been shared with you"
        ),
        [{"day": "2026-10-01", "fee": 1}],
    ]
    result = runner.invoke(
        app,
        [
            "preview-widget",
            "--query-id",
            "9",
            "--type",
            "line",
            "--x",
            "day",
            "--y",
            "fee",
        ],
    )
    assert result.exit_code == 0, _all_output(result)
    first, second = client.execute_query.call_args_list
    assert "ref(table=" in first.args[0]
    assert "select day, fee from t" in second.args[0]
    assert first.args[1:] == (9, 7)
    assert first.kwargs["limit"] == 500
    assert "2026-10-01" in result.output


def test_preview_widget_other_errors_do_not_fall_back(monkeypatch):
    client = _widget_client(monkeypatch)
    client.execute_query.side_effect = RuntimeError("division by zero")
    result = runner.invoke(
        app, ["preview-widget", "--query-id", "9", "--type", "table"]
    )
    assert result.exit_code == 1
    assert client.execute_query.call_count == 1
    assert client.execute_query.call_args.kwargs["limit"] == 25


def test_preview_widget_ctrl_c_exits_130(monkeypatch):
    client = _widget_client(monkeypatch)
    client.execute_query.side_effect = KeyboardInterrupt
    result = runner.invoke(
        app, ["preview-widget", "--query-id", "9", "--type", "pie", "--x", "day"]
    )
    assert result.exit_code == 130


def test_preview_widget_refuses_a_missing_axis(monkeypatch):
    client = _widget_client(monkeypatch)
    result = runner.invoke(app, ["preview-widget", "--query-id", "9", "--type", "bar"])
    assert result.exit_code == 1
    client.execute_query.assert_not_called()


def test_set_layout_validates_before_it_sends(monkeypatch, tmp_path):
    client = _widget_client(monkeypatch)
    bad = tmp_path / "bad.json"
    bad.write_text('[{"widget_id": 1, "x": 10, "y": 0, "width": 4, "height": 4}]')
    result = runner.invoke(app, ["set-layout", "--id", "3", "--layout", str(bad)])
    assert result.exit_code == 1
    client.set_dashboard_layout.assert_not_called()
    good = tmp_path / "good.json"
    good.write_text('[{"widget_id": 1, "x": 8, "y": 0, "width": 4, "height": 4}]')
    result = runner.invoke(app, ["set-layout", "--id", "3", "--layout", str(good)])
    assert result.exit_code == 0, _all_output(result)
    client.set_dashboard_layout.assert_called_once_with(
        3, [{"widget_id": 1, "x": 8, "y": 0, "width": 4, "height": 4}]
    )


def test_create_dashboard(monkeypatch):
    client = _widget_client(monkeypatch)
    client.get_me.return_value = {"entity_id": 45}
    client.create_dashboard.return_value = {"dashboard_id": 8}
    result = runner.invoke(
        app,
        ["create-dashboard", "Fees", "--public", "--unlisted", "--description", "d"],
    )
    assert result.exit_code == 0, _all_output(result)
    client.create_dashboard.assert_called_once_with(
        "Fees", 45, "d", is_public=True, is_unlisted=True
    )
    assert "https://app.dedaub.com/dashboard/8" in result.output


def test_create_dashboard_unlisted_needs_public(monkeypatch):
    client = _widget_client(monkeypatch)
    result = runner.invoke(app, ["create-dashboard", "Fees", "--unlisted"])
    assert result.exit_code == 2
    client.create_dashboard.assert_not_called()


def test_update_dashboard_merges_and_private_clears_unlisted(monkeypatch):
    client = _widget_client(monkeypatch)
    client.get_dashboard.return_value = {
        "name": "Fees",
        "description": "d",
        "is_public": True,
        "is_unlisted": True,
        "entity_id": 45,
    }
    result = runner.invoke(app, ["update-dashboard", "--id", "8", "--private"])
    assert result.exit_code == 0, _all_output(result)
    client.update_dashboard.assert_called_once_with(
        8,
        {
            "name": "Fees",
            "description": "d",
            "is_public": False,
            "is_unlisted": False,
            "entity_id": 45,
        },
    )


def test_update_dashboard_needs_a_change(monkeypatch):
    _widget_client(monkeypatch)
    assert runner.invoke(app, ["update-dashboard", "--id", "8"]).exit_code == 2


def test_delete_dashboard_flag(monkeypatch):
    client = _widget_client(monkeypatch)
    client.delete_dashboard.return_value = {"deleted_widgets": 2}
    result = runner.invoke(app, ["delete-dashboard", "--id", "8", "--delete-widgets"])
    assert result.exit_code == 0, _all_output(result)
    client.delete_dashboard.assert_called_once_with(8, delete_widgets=True)
    assert "2 widget(s)" in result.output
    runner.invoke(app, ["delete-dashboard", "--id", "8"])
    client.delete_dashboard.assert_called_with(8, delete_widgets=False)


@pytest.mark.parametrize(
    ("args", "code", "sent"),
    [
        (["--id", "5"], 0, 5),
        (["--clear"], 0, None),
        ([], 2, "none"),
        (["--id", "5", "--clear"], 2, "none"),
    ],
)
def test_set_default_dashboard(monkeypatch, args, code, sent):
    client = _widget_client(monkeypatch)
    result = runner.invoke(app, ["set-default-dashboard", *args])
    assert result.exit_code == code
    if sent == "none":
        client.set_default_dashboard.assert_not_called()
    else:
        client.set_default_dashboard.assert_called_once_with(sent)


def test_add_and_remove_widget(monkeypatch):
    client = _widget_client(monkeypatch)
    result = runner.invoke(
        app,
        ["add-widget", "--id", "12", "--dashboard-id", "3", "--dashboard-id", "4"]
        + ["--dashboard-id", "3"],
    )
    assert result.exit_code == 0, _all_output(result)
    client.add_widget_to_dashboards.assert_called_once_with(12, [3, 4])
    result = runner.invoke(app, ["remove-widget", "--id", "12", "--dashboard-id", "3"])
    assert result.exit_code == 0, _all_output(result)
    client.remove_dashboard_widget.assert_called_once_with(3, 12)


def test_delete_widget(monkeypatch):
    client = _widget_client(monkeypatch)
    result = runner.invoke(app, ["delete-widget", "--id", "12"])
    assert result.exit_code == 0
    client.delete_widget.assert_called_once_with(12)


def test_get_widget_not_found_exits_one(monkeypatch):
    client = _widget_client(monkeypatch)
    client.get_widget.side_effect = cli.NotFoundError("/api/profile/widget/99")
    assert runner.invoke(app, ["get-widget", "--id", "99"]).exit_code == 1


def test_list_dashboards_marks_the_default(monkeypatch):
    client = _widget_client(monkeypatch)
    client.list_dashboards.return_value = [
        {"dashboard_id": 3, "name": "Fees", "is_public": False, "widget_count": 2},
        {"dashboard_id": 4, "name": "Gas", "is_public": True, "is_unlisted": True},
    ]
    client.get_default_dashboard.return_value = 4
    result = runner.invoke(app, ["list-dashboards"])
    assert result.exit_code == 0, _all_output(result)
    assert "Gas (default)" in result.output
    assert "public, unlisted" in result.output


def test_get_dashboard_includes_its_widgets(monkeypatch):
    client = _widget_client(monkeypatch)
    client.get_dashboard.return_value = {"dashboard_id": 3, "name": "Fees"}
    client.list_widgets.return_value = [{"widget_id": 12}]
    result = runner.invoke(app, ["get-dashboard", "--id", "3"])
    assert result.exit_code == 0, _all_output(result)
    client.list_widgets.assert_called_once_with(dashboard_id=3)
    assert json.loads(result.output)["widgets"] == [{"widget_id": 12}]


def _alert_widget():
    return {**_stored_widget(), "category": "ALERT", "type": "table", "config": {}}


@pytest.mark.parametrize(
    "command",
    [
        ["check-widget", "--id", "12"],
        ["preview-widget", "--id", "12"],
        ["update-widget", "--id", "12", "--label", "New"],
    ],
)
def test_an_alerts_widget_is_not_a_chart(monkeypatch, command):
    client = _widget_client(monkeypatch)
    client.get_widget.return_value = _alert_widget()
    result = runner.invoke(app, command)
    assert result.exit_code == 1
    out = _all_output(result)
    assert "An alerts widget shows the alerts of its query" in out
    assert "Error: " not in out
    client.execute_query.assert_not_called()
    client.update_widget.assert_not_called()
    client.query_columns.assert_not_called()
