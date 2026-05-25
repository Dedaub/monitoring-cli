from io import StringIO
from rich.console import Console
from monitoring_cli.output import (
    format_entities,
    format_tree,
    format_query_text,
    format_logs,
    format_fired_alerts,
    format_query_results,
    format_alert_queries,
)


def _capture(fn, *args, **kwargs) -> str:
    buf = StringIO()
    console = Console(file=buf, highlight=False)
    fn(*args, console=console, **kwargs)
    return buf.getvalue()


def test_format_entities_shows_name_and_id():
    entities = [
        {"username": "Dedaub", "entity_id": 452},
        {"username": "vasilis", "entity_id": 45},
    ]
    output = _capture(format_entities, entities)
    assert "Dedaub" in output
    assert "452" in output
    assert "vasilis" in output
    assert "45" in output


def test_format_tree_shows_folder_and_query():
    folders = [
        {"folder_id": 10, "path": "/Alpha"},
        {"folder_id": 11, "path": "/Alpha/Beta"},
    ]
    queries = [
        {"query_id": 55, "query_name": "MyQuery", "folder_id": 11},
    ]
    output = _capture(format_tree, folders, queries, "Dedaub")
    assert "Dedaub" in output
    assert "Alpha" in output
    assert "Beta" in output
    assert "MyQuery" in output
    assert "55" in output


def test_format_tree_no_mutation_on_repeated_call():
    folders = [
        {"folder_id": 10, "path": "/Alpha"},
        {"folder_id": 11, "path": "/Alpha/Beta"},
    ]
    queries = [{"query_id": 55, "query_name": "MyQuery", "folder_id": 11}]
    output1 = _capture(format_tree, folders, queries, "Dedaub")
    output2 = _capture(format_tree, folders, queries, "Dedaub")
    assert output1 == output2
    # verify no _node keys leaked into the input dicts
    assert "_node" not in folders[0]
    assert "_node" not in folders[1]


def test_format_query_text_prints_sql():
    sql = "select * from ethereum.transactions"
    output = _capture(format_query_text, sql)
    assert "select" in output
    assert "ethereum.transactions" in output


def test_format_logs_shows_status_and_query():
    logs = [
        {
            "status": "SUCCESS",
            "query": {"query_name": "MyQuery"},
            "start_ts": "2026-05-07T10:00:00Z",
            "message": None,
        },
        {
            "status": "FAIL",
            "query": {"query_name": "OtherQuery"},
            "start_ts": "2026-05-07T09:00:00Z",
            "message": "column not found",
        },
    ]
    out = _capture(format_logs, logs)
    assert "SUCCESS" in out
    assert "MyQuery" in out
    assert "FAIL" in out
    assert "column not found" in out


def test_format_logs_shows_next_page_hint():
    logs = [
        {
            "status": "SUCCESS",
            "query": {"query_name": "Q"},
            "start_ts": "2026-05-07T10:00:00Z",
            "message": None,
        }
    ]
    out = _capture(format_logs, logs)
    assert "--before" in out
    assert "2026-05-07T10:00:00Z" in out


def test_format_logs_empty():
    out = _capture(format_logs, [])
    assert "No logs" in out


def test_format_fired_alerts_shows_entries():
    alerts = [
        {
            "alert_id": 42,
            "query": {"query_name": "Alert1"},
            "_ts": "2026-05-07T10:00:00Z",
            "query_message": "suspicious tx detected",
        },
    ]
    out = _capture(format_fired_alerts, alerts)
    assert "42" in out
    assert "Alert1" in out
    assert "suspicious tx detected" in out


def test_format_fired_alerts_shows_next_page_hint():
    alerts = [
        {
            "alert_id": 42,
            "query": {"query_name": "Q"},
            "_ts": "2026-05-07T10:00:00Z",
            "query_message": "msg",
        }
    ]
    out = _capture(format_fired_alerts, alerts)
    assert "--after-id 42" in out


def test_format_fired_alerts_empty():
    out = _capture(format_fired_alerts, [])
    assert "No alerts" in out


def test_format_query_results_shows_rows():
    results = [
        {"address": "0x123", "balance": "1000"},
        {"address": "0x456", "balance": "2000"},
    ]
    out = _capture(format_query_results, results)
    assert "0x123" in out
    assert "1000" in out
    assert "address" in out
    assert "balance" in out


def test_format_query_results_empty():
    out = _capture(format_query_results, [])
    assert "No results" in out


def test_format_alert_queries_shows_path():
    folders = [{"folder_id": 10, "path": "/Alpha"}]
    queries = [{"query_id": 55, "query_name": "MyQuery", "folder_id": 10}]
    out = _capture(format_alert_queries, queries, folders)
    assert "55" in out
    assert "/Alpha/MyQuery" in out
