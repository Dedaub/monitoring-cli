import os
import pytest
from typer.testing import CliRunner
from monitoring_cli.cli import app
from monitoring_cli.config import Config, Profile

runner = CliRunner()

requires_integration = pytest.mark.skipif(
    not os.environ.get("DEDAUB_TEST_REFRESH_TOKEN"),
    reason="Set DEDAUB_TEST_REFRESH_TOKEN and DEDAUB_TEST_BASE_URL to run integration tests",
)


@pytest.fixture(autouse=True)
def prod_config(tmp_path, monkeypatch):
    config_path = tmp_path / ".config" / "dedaub" / "monitoring.json"
    monkeypatch.setattr("monitoring_cli.config.CONFIG_PATH", config_path)

    profile = Profile(
        base_url=os.environ.get("DEDAUB_TEST_BASE_URL", "https://api.dedaub.com"),
        oidc_host="https://auth.dedaub.com",
        client_id="watchdog-client",
        realm="dedaub",
        refresh_token=os.environ.get("DEDAUB_TEST_REFRESH_TOKEN", ""),
    )
    config = Config(default="prod", profiles={"prod": profile})
    config.save()


@requires_integration
def test_entities_returns_at_least_one_entity():
    result = runner.invoke(app, ["entities", "--profile", "prod"])
    assert result.exit_code == 0, result.output
    assert len(result.output.strip()) > 0


@requires_integration
def test_tree_runs_without_error():
    result = runner.invoke(app, ["tree", "--profile", "prod"])
    assert result.exit_code == 0, result.output


@requires_integration
def test_query_metadata_by_id():
    query_id = os.environ.get("DEDAUB_TEST_QUERY_ID")
    if not query_id:
        pytest.skip("Set DEDAUB_TEST_QUERY_ID to run this test")
    result = runner.invoke(
        app, ["query-metadata", "--id", query_id, "--profile", "prod"]
    )
    assert result.exit_code == 0, result.output
    assert "query_id" in result.output


@requires_integration
def test_get_logs_runs_without_error():
    result = runner.invoke(app, ["get-logs", "--profile", "prod", "--limit", "5"])
    assert result.exit_code == 0, result.output


@requires_integration
def test_get_logs_filtered_by_id():
    query_id = os.environ.get("DEDAUB_TEST_QUERY_ID")
    if not query_id:
        pytest.skip("Set DEDAUB_TEST_QUERY_ID to run this test")
    result = runner.invoke(
        app, ["get-logs", "--profile", "prod", "--id", query_id, "--limit", "5"]
    )
    assert result.exit_code == 0, result.output


@requires_integration
def test_get_logs_filtered_by_status():
    result = runner.invoke(
        app, ["get-logs", "--profile", "prod", "--status", "FAIL", "--limit", "5"]
    )
    assert result.exit_code == 0, result.output


@requires_integration
def test_get_alerts_runs_without_error():
    result = runner.invoke(app, ["get-alerts", "--profile", "prod", "--limit", "5"])
    assert result.exit_code == 0, result.output


@requires_integration
def test_list_alerts_runs_without_error():
    result = runner.invoke(app, ["list-alerts", "--profile", "prod"])
    assert result.exit_code == 0, result.output


@requires_integration
def test_get_config_by_id():
    query_id = os.environ.get("DEDAUB_TEST_QUERY_ID")
    if not query_id:
        pytest.skip("Set DEDAUB_TEST_QUERY_ID to run this test")
    result = runner.invoke(app, ["get-config", "--id", query_id, "--profile", "prod"])
    assert result.exit_code == 0, result.output


@requires_integration
def test_run_query_by_id():
    query_id = os.environ.get("DEDAUB_TEST_QUERY_ID")
    if not query_id:
        pytest.skip("Set DEDAUB_TEST_QUERY_ID to run this test")
    result = runner.invoke(
        app,
        [
            "run-query",
            "--id",
            query_id,
            "--profile",
            "prod",
            "--duration",
            "5m",
            "--limit",
            "5",
        ],
    )
    assert result.exit_code == 0, result.output
