import json

import httpx
import pytest
import respx

from monitoring_cli.auth import SessionExpiredError
from monitoring_cli.client import (
    ConflictError,
    MonitoringClient,
    NotFoundError,
    resolve_folder_id,
    resolve_query_id,
)
from monitoring_cli.config import Profile

BASE = "https://api.dedaub.com"

PROFILE = Profile(
    base_url=BASE,
    oidc_host="https://auth.dedaub.com",
    client_id="watchdog-client",
    realm="dedaub",
    refresh_token="tok",
)

TOKEN_URL = "https://auth.dedaub.com/realms/dedaub/protocol/openid-connect/token"


def mock_token(respx_mock):
    respx_mock.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "test-access-token"})
    )


@respx.mock
def test_get_me():
    mock_token(respx)
    respx.get(f"{BASE}/api/auth/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "user_id": 1,
                "username": "vasilis",
                "entity_id": 45,
                "subscriptions": [{"entity_id": 452, "organization_name": "Dedaub"}],
            },
        )
    )
    client = MonitoringClient(PROFILE)
    me = client.get_me()
    assert me["username"] == "vasilis"
    assert me["entity_id"] == 45


@respx.mock
def test_get_folders_by_entity():
    mock_token(respx)
    # The client uses the literal broken Starlette path as a workaround (see client.py)
    respx.get(f"{BASE}/api/folder/entity/{{entity_id: int}}").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"folder_id": 10, "path": "/Alpha", "entity_id": 45},
                {"folder_id": 11, "path": "/Alpha/Beta", "entity_id": 45},
            ],
        )
    )
    client = MonitoringClient(PROFILE)
    folders = client.get_folders_by_entity(45)
    assert len(folders) == 2
    assert folders[0]["path"] == "/Alpha"


@respx.mock
def test_get_query():
    mock_token(respx)
    respx.get(f"{BASE}/api/profile/tsql/query/99").mock(
        return_value=httpx.Response(
            200,
            json={"query_id": 99, "query_name": "MyQuery", "query_text": "select 1"},
        )
    )
    client = MonitoringClient(PROFILE)
    q = client.get_query(99)
    assert q["query_text"] == "select 1"


@respx.mock
def test_404_raises_not_found_error():
    mock_token(respx)
    respx.get(f"{BASE}/api/profile/tsql/query/999").mock(
        return_value=httpx.Response(404, json={"detail": "not found"})
    )
    client = MonitoringClient(PROFILE)
    with pytest.raises(NotFoundError):
        client.get_query(999)


@respx.mock
def test_409_raises_conflict_error():
    mock_token(respx)
    # Same Starlette path workaround as get_folders_by_entity
    respx.post(f"{BASE}/api/folder/entity/{{entity_id: int}}").mock(
        return_value=httpx.Response(409, json={"detail": "already exists"})
    )
    client = MonitoringClient(PROFILE)
    with pytest.raises(ConflictError):
        client.create_folder(45, "/NewFolder")


def test_resolve_folder_id_found():
    folders = [
        {"folder_id": 10, "path": "/Alpha"},
        {"folder_id": 11, "path": "/Alpha/Beta"},
    ]
    assert resolve_folder_id(folders, "/Alpha/Beta") == 11


def test_resolve_folder_id_not_found():
    folders = [{"folder_id": 10, "path": "/Alpha"}]
    with pytest.raises(NotFoundError):
        resolve_folder_id(folders, "/Missing")


def test_resolve_query_id_found():
    queries = [
        {"query_id": 55, "query_name": "MyQuery", "folder_id": 10},
        {"query_id": 56, "query_name": "OtherQuery", "folder_id": 10},
    ]
    folders = [{"folder_id": 10, "path": "/Alpha"}]
    assert resolve_query_id(folders, queries, "/Alpha/MyQuery") == 55


def test_resolve_query_id_not_found():
    queries = [{"query_id": 55, "query_name": "MyQuery", "folder_id": 10}]
    folders = [{"folder_id": 10, "path": "/Alpha"}]
    with pytest.raises(NotFoundError):
        resolve_query_id(folders, queries, "/Alpha/Missing")


@respx.mock
def test_401_raises_session_expired_error():
    mock_token(respx)
    respx.get(f"{BASE}/api/auth/me").mock(
        return_value=httpx.Response(401, json={"detail": "unauthorized"})
    )
    client = MonitoringClient(PROFILE)
    with pytest.raises(SessionExpiredError):
        client.get_me()


@respx.mock
def test_update_query_text():
    mock_token(respx)
    respx.get(f"{BASE}/api/profile/tsql/query/99").mock(
        return_value=httpx.Response(
            200,
            json={"query_id": 99, "query_name": "MyQuery", "query_text": "select 1"},
        )
    )
    put_route = respx.put(f"{BASE}/api/profile/tsql/query/99").mock(
        return_value=httpx.Response(200, json={})
    )
    client = MonitoringClient(PROFILE)
    client.update_query_text(99, "select 2")
    assert put_route.called
    sent_body = put_route.calls[0].request
    body = json.loads(sent_body.content)
    assert body["query_text"] == "select 2"


@respx.mock
def test_execute_query_returns_rows():
    mock_token(respx)
    task_id = "550e8400-e29b-41d4-a716-446655440000"
    respx.post(f"{BASE}/api/tsql/query/execute_async").mock(
        return_value=httpx.Response(200, json=task_id)
    )
    respx.get(f"{BASE}/api/tsql/query/execute_async/{task_id}").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "SUCCESS",
                "result": [{"address": "0x123", "balance": "1000"}],
                "error": None,
            },
        )
    )
    client = MonitoringClient(PROFILE)
    results = client.execute_query(
        "select 1",
        query_id=99,
        entity_id=45,
        network="ethereum",
        default_duration="24h",
    )
    assert len(results) == 1
    assert results[0]["address"] == "0x123"


@respx.mock
def test_execute_query_sends_correct_body():
    mock_token(respx)
    task_id = "550e8400-e29b-41d4-a716-446655440000"
    route = respx.post(f"{BASE}/api/tsql/query/execute_async").mock(
        return_value=httpx.Response(200, json=task_id)
    )
    respx.get(f"{BASE}/api/tsql/query/execute_async/{task_id}").mock(
        return_value=httpx.Response(
            200, json={"status": "SUCCESS", "result": [], "error": None}
        )
    )
    client = MonitoringClient(PROFILE)
    client.execute_query(
        "select 1",
        query_id=99,
        entity_id=45,
        network="ethereum",
        default_duration="7d",
        limit=10,
    )
    body = json.loads(route.calls[0].request.content)
    assert body["query"] == "select 1"
    assert body["query_id"] == 99
    assert body["query_entity_id"] == 45
    assert body["default_duration"] == "7d"
    assert body["limit"] == 10


@respx.mock
def test_execute_query_raises_on_failure():
    mock_token(respx)
    task_id = "550e8400-e29b-41d4-a716-446655440001"
    respx.post(f"{BASE}/api/tsql/query/execute_async").mock(
        return_value=httpx.Response(200, json=task_id)
    )
    respx.get(f"{BASE}/api/tsql/query/execute_async/{task_id}").mock(
        return_value=httpx.Response(
            200, json={"status": "FAILURE", "result": None, "error": "column not found"}
        )
    )
    client = MonitoringClient(PROFILE)
    with pytest.raises(RuntimeError, match="column not found"):
        client.execute_query("select bad", query_id=99, entity_id=45)


@respx.mock
def test_get_logs():
    mock_token(respx)
    respx.get(f"{BASE}/api/profile/tsql/logs").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "run_id": "abc",
                    "query_id": 99,
                    "status": "SUCCESS",
                    "start_ts": "2026-05-07T10:00:00Z",
                    "message": None,
                }
            ],
        )
    )
    client = MonitoringClient(PROFILE)
    logs = client.get_logs(query_ids=[99], limit=10)
    assert len(logs) == 1
    assert logs[0]["status"] == "SUCCESS"


@respx.mock
def test_get_fired_alerts():
    mock_token(respx)
    respx.get(f"{BASE}/api/profile/tsql/alerts").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "alert_id": 1,
                    "query_id": 99,
                    "_ts": "2026-05-07T10:00:00Z",
                    "query_message": "suspicious tx",
                }
            ],
        )
    )
    client = MonitoringClient(PROFILE)
    alerts = client.get_fired_alerts(query_ids=[99], limit=10)
    assert alerts[0]["alert_id"] == 1
    assert alerts[0]["query_message"] == "suspicious tx"


@respx.mock
def test_get_run_config():
    mock_token(respx)
    respx.get(f"{BASE}/api/profile/tsql/query/99/ethereum/config").mock(
        return_value=httpx.Response(
            200,
            json={
                "materialize": "INCREMENTAL",
                "frequency": 3600,
                "incrementalization": "IGNORE",
            },
        )
    )
    client = MonitoringClient(PROFILE)
    cfg = client.get_run_config(99, "ethereum")
    assert cfg["materialize"] == "INCREMENTAL"
    assert cfg["frequency"] == 3600


@respx.mock
def test_set_run_config_sends_body():
    mock_token(respx)
    route = respx.put(f"{BASE}/api/profile/tsql/query/99/ethereum/config").mock(
        return_value=httpx.Response(200)
    )
    client = MonitoringClient(PROFILE)
    client.set_run_config(99, "ethereum", {"materialize": "TABLE", "frequency": 3600})
    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body["materialize"] == "TABLE"


@respx.mock
def test_get_notify_config():
    mock_token(respx)
    respx.get(f"{BASE}/api/profile/tsql/query/99/ethereum/notify").mock(
        return_value=httpx.Response(
            200, json={"notify": True, "alert_email": False, "webhook_id": None}
        )
    )
    client = MonitoringClient(PROFILE)
    cfg = client.get_notify_config(99, "ethereum")
    assert cfg["notify"] is True


@respx.mock
def test_set_notify_config():
    mock_token(respx)
    route = respx.put(f"{BASE}/api/profile/tsql/query/99/ethereum/notify").mock(
        return_value=httpx.Response(200)
    )
    client = MonitoringClient(PROFILE)
    client.set_notify_config(
        99, "ethereum", {"notify": True, "alert_email": False, "webhook_id": None}
    )
    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body["notify"] is True


@respx.mock
def test_validate_query_true():
    mock_token(respx)
    route = respx.post(f"{BASE}/api/tsql/query/validate").mock(
        return_value=httpx.Response(200, json=True)
    )
    client = MonitoringClient(PROFILE)
    assert client.validate_query("select 1", query_id=9, entity_id=7) is True
    body = json.loads(route.calls[0].request.content)
    assert body["query"] == "select 1"
    assert body["query_entity_id"] == 7


@respx.mock
def test_validate_query_bad_raises_with_detail():
    mock_token(respx)
    respx.post(f"{BASE}/api/tsql/query/validate").mock(
        return_value=httpx.Response(
            400, json={"detail": "syntax error at or near SELEKT"}
        )
    )
    client = MonitoringClient(PROFILE)
    with pytest.raises(httpx.HTTPStatusError, match="syntax error"):
        client.validate_query("selekt 1", query_id=9, entity_id=7)


@respx.mock
def test_query_columns():
    mock_token(respx)
    respx.post(f"{BASE}/api/tsql/query/metadata").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"column_name": "chain_id", "column_type": "int4"},
                {"column_name": "amount", "column_type": "int4"},
            ],
        )
    )
    client = MonitoringClient(PROFILE)
    cols = client.query_columns("select 1 as chain_id", query_id=9, entity_id=7)
    assert [c["column_name"] for c in cols] == ["chain_id", "amount"]


@respx.mock
def test_format_query():
    mock_token(respx)
    respx.post(f"{BASE}/api/tsql/format").mock(
        return_value=httpx.Response(200, json="select 1 as a")
    )
    client = MonitoringClient(PROFILE)
    assert client.format_query("select 1 as a") == "select 1 as a"


@respx.mock
def test_get_query_status():
    mock_token(respx)
    respx.get(f"{BASE}/api/profile/tsql/status").mock(
        return_value=httpx.Response(200, json={"query_id": 9, "is_materialized": True})
    )
    client = MonitoringClient(PROFILE)
    status = client.get_query_status(9)
    assert status["is_materialized"] is True


@respx.mock
def test_materialize_query():
    mock_token(respx)
    respx.post(f"{BASE}/api/tsql/query/materialize/9").mock(
        return_value=httpx.Response(200, json="task-uuid")
    )
    client = MonitoringClient(PROFILE)
    assert client.materialize_query(9) == "task-uuid"


@respx.mock
def test_create_webhook_uses_doubled_prefix_path():
    mock_token(respx)
    route = respx.post(f"{BASE}/api/profile/api/profile/webhook").mock(
        return_value=httpx.Response(
            200, json={"webhook_id": 3, "name": "n", "url": "u"}
        )
    )
    client = MonitoringClient(PROFILE)
    result = client.create_webhook("n", "https://example.com/hook")
    assert result["webhook_id"] == 3
    body = json.loads(route.calls[0].request.content)
    assert body["url"] == "https://example.com/hook"


@respx.mock
def test_delete_webhook_uses_doubled_webhook_path():
    mock_token(respx)
    route = respx.delete(f"{BASE}/api/profile/api/profile/webhook/webhook/3").mock(
        return_value=httpx.Response(200, json={})
    )
    client = MonitoringClient(PROFILE)
    client.delete_webhook(3)
    assert route.called


@respx.mock
def test_move_folder_returns_response_body():
    mock_token(respx)
    respx.put(f"{BASE}/api/folder/move/{{folder_id: int}}").mock(
        return_value=httpx.Response(200, json={"folder_id": 5, "new_parent": 2})
    )
    client = MonitoringClient(PROFILE)
    result = client.move_folder(5, entity_id=7, new_folder_id=2)
    assert result["folder_id"] == 5


@respx.mock
def test_create_alert_filter_returns_id():
    mock_token(respx)
    respx.post(f"{BASE}/api/profile/alert-filter").mock(
        return_value=httpx.Response(200, json=42)
    )
    client = MonitoringClient(PROFILE)
    assert client.create_alert_filter("my filter", query_ids=[1, 2]) == 42


@respx.mock
def test_update_query_alert_settings():
    mock_token(respx)
    respx.get(f"{BASE}/api/profile/tsql/query/99").mock(
        return_value=httpx.Response(
            200,
            json={
                "query_id": 99,
                "query_name": "MyQuery",
                "query_text": "select 1",
                "alert_template": "",
                "unique_key": None,
            },
        )
    )
    route = respx.put(f"{BASE}/api/profile/tsql/query/99").mock(
        return_value=httpx.Response(200, json={})
    )
    client = MonitoringClient(PROFILE)
    client.update_query_alert_settings(99, "{{from_a}} sent to {{to_a}}", ["tx_hash"])
    body = json.loads(route.calls[0].request.content)
    assert body["alert_template"] == "{{from_a}} sent to {{to_a}}"
    assert body["unique_key"] == ["tx_hash"]


@respx.mock
def test_access_token_is_reused_until_expiry():
    token_route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json={"access_token": "acc", "expires_in": 300}
        )
    )
    respx.get(f"{BASE}/api/auth/me").mock(
        return_value=httpx.Response(200, json={"username": "u", "entity_id": 1})
    )
    client = MonitoringClient(PROFILE)
    client.get_me()
    client.get_me()
    assert token_route.call_count == 1


@respx.mock
def test_access_token_is_refreshed_after_expiry(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr("monitoring_cli.client.time.monotonic", lambda: now[0])
    token_route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json={"access_token": "acc", "expires_in": 300}
        )
    )
    respx.get(f"{BASE}/api/auth/me").mock(
        return_value=httpx.Response(200, json={"username": "u", "entity_id": 1})
    )
    client = MonitoringClient(PROFILE)
    client.get_me()
    now[0] += 300
    client.get_me()
    assert token_route.call_count == 2


@respx.mock
def test_rotated_refresh_token_is_reported_and_used():
    profile = Profile(
        base_url=BASE,
        oidc_host="https://auth.dedaub.com",
        client_id="watchdog-client",
        refresh_token="old",
    )
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={"access_token": "acc", "refresh_token": "new", "expires_in": 300},
        )
    )
    respx.get(f"{BASE}/api/auth/me").mock(
        return_value=httpx.Response(200, json={"username": "u", "entity_id": 1})
    )
    seen: list[str] = []
    MonitoringClient(profile, on_refresh_token=seen.append).get_me()
    assert seen == ["new"]
    assert profile.refresh_token == "new"


# --- dashboards and widgets: method, path, params and body of each call ------


def _json_body(route) -> object:
    return json.loads(route.calls.last.request.content)


@respx.mock
def test_list_dashboards():
    mock_token(respx)
    route = respx.get(f"{BASE}/api/profile/dashboards").mock(
        return_value=httpx.Response(200, json=[{"dashboard_id": 3}])
    )
    assert MonitoringClient(PROFILE).list_dashboards() == [{"dashboard_id": 3}]
    assert route.called


@respx.mock
def test_get_dashboard():
    mock_token(respx)
    respx.get(f"{BASE}/api/profile/dashboard/3").mock(
        return_value=httpx.Response(200, json={"dashboard_id": 3})
    )
    assert MonitoringClient(PROFILE).get_dashboard(3) == {"dashboard_id": 3}


@respx.mock
def test_create_dashboard_body():
    mock_token(respx)
    route = respx.post(f"{BASE}/api/profile/dashboard").mock(
        return_value=httpx.Response(200, json={"dashboard_id": 8})
    )
    MonitoringClient(PROFILE).create_dashboard(
        "Fees", 45, "desc", is_public=True, is_unlisted=True
    )
    assert _json_body(route) == {
        "name": "Fees",
        "description": "desc",
        "is_public": True,
        "is_unlisted": True,
        "entity_id": 45,
    }


@respx.mock
def test_update_dashboard_sends_the_whole_dashboard():
    mock_token(respx)
    route = respx.put(f"{BASE}/api/profile/dashboard/8").mock(
        return_value=httpx.Response(200, content=b"null")
    )
    body = {
        "name": "N",
        "description": None,
        "is_public": False,
        "is_unlisted": False,
        "entity_id": 45,
    }
    MonitoringClient(PROFILE).update_dashboard(8, body)
    assert _json_body(route) == body


@respx.mock
def test_delete_dashboard_keeps_widgets_by_default():
    mock_token(respx)
    route = respx.delete(f"{BASE}/api/profile/dashboard/8").mock(
        return_value=httpx.Response(200, json={"deleted_widgets": 0})
    )
    assert MonitoringClient(PROFILE).delete_dashboard(8) == {"deleted_widgets": 0}
    assert "delete_widgets" not in route.calls.last.request.url.params


@respx.mock
def test_delete_dashboard_with_widgets():
    mock_token(respx)
    route = respx.delete(f"{BASE}/api/profile/dashboard/8").mock(
        return_value=httpx.Response(200, json={"deleted_widgets": 2})
    )
    result = MonitoringClient(PROFILE).delete_dashboard(8, delete_widgets=True)
    assert result == {"deleted_widgets": 2}
    assert route.calls.last.request.url.params["delete_widgets"] == "true"


@respx.mock
def test_default_dashboard_get_set_and_clear():
    mock_token(respx)
    respx.get(f"{BASE}/api/profile/dashboard/default").mock(
        return_value=httpx.Response(200, json={"dashboard_id": 5})
    )
    route = respx.put(f"{BASE}/api/profile/dashboard/default").mock(
        return_value=httpx.Response(200, json={"dashboard_id": None})
    )
    client = MonitoringClient(PROFILE)
    assert client.get_default_dashboard() == 5
    client.set_default_dashboard(7)
    assert _json_body(route) == {"dashboard_id": 7}
    client.set_default_dashboard(None)
    assert _json_body(route) == {"dashboard_id": None}


@respx.mock
def test_set_dashboard_layout():
    mock_token(respx)
    route = respx.put(f"{BASE}/api/profile/dashboard/8/layout").mock(
        return_value=httpx.Response(200, json=[])
    )
    layout = [{"widget_id": 1, "x": 0, "y": 0, "width": 4, "height": 4}]
    MonitoringClient(PROFILE).set_dashboard_layout(8, layout)
    assert _json_body(route) == layout


@respx.mock
def test_remove_dashboard_widget():
    mock_token(respx)
    route = respx.delete(f"{BASE}/api/profile/dashboard/8/widget/12").mock(
        return_value=httpx.Response(200, content=b"null")
    )
    MonitoringClient(PROFILE).remove_dashboard_widget(8, 12)
    assert route.called


@respx.mock
def test_list_widgets_filters():
    mock_token(respx)
    route = respx.get(f"{BASE}/api/profile/widgets").mock(
        return_value=httpx.Response(200, json=[])
    )
    client = MonitoringClient(PROFILE)
    client.list_widgets()
    assert dict(route.calls.last.request.url.params) == {}
    client.list_widgets(query_id=9, dashboard_id=3)
    assert dict(route.calls.last.request.url.params) == {
        "query_id": "9",
        "dashboard_id": "3",
    }


@respx.mock
def test_get_widget():
    mock_token(respx)
    respx.get(f"{BASE}/api/profile/widget/12").mock(
        return_value=httpx.Response(200, json={"widget_id": 12})
    )
    assert MonitoringClient(PROFILE).get_widget(12) == {"widget_id": 12}


@respx.mock
def test_create_and_update_widget_send_the_body():
    mock_token(respx)
    create = respx.post(f"{BASE}/api/profile/widget").mock(
        return_value=httpx.Response(200, json={"widget_id": 12})
    )
    update = respx.put(f"{BASE}/api/profile/widget/12").mock(
        return_value=httpx.Response(200, json={"widget_id": 12})
    )
    body = {"type": "line", "config": {"x_axis_name": "day"}}
    client = MonitoringClient(PROFILE)
    assert client.create_widget(body) == {"widget_id": 12}
    assert _json_body(create) == body
    client.update_widget(12, body)
    assert _json_body(update) == body


@respx.mock
def test_delete_widget():
    mock_token(respx)
    route = respx.delete(f"{BASE}/api/profile/widget/12").mock(
        return_value=httpx.Response(200, content=b"null")
    )
    MonitoringClient(PROFILE).delete_widget(12)
    assert route.called


@respx.mock
def test_add_widget_to_dashboards():
    mock_token(respx)
    route = respx.post(f"{BASE}/api/profile/widget/12/dashboards").mock(
        return_value=httpx.Response(200, json={"widget_id": 12})
    )
    MonitoringClient(PROFILE).add_widget_to_dashboards(12, [3, 4])
    assert _json_body(route) == {"dashboard_ids": [3, 4]}


# --- GET retry and server errors ---------------------------------------------------


@pytest.fixture
def no_sleep(monkeypatch):
    waits: list[float] = []
    monkeypatch.setattr("monitoring_cli.client._sleep", waits.append)
    return waits


@respx.mock
def test_get_retries_a_gateway_timeout(no_sleep):
    mock_token(respx)
    route = respx.get(f"{BASE}/api/auth/me").mock(
        side_effect=[
            httpx.Response(504, json={"detail": "Request Timeout"}),
            httpx.Response(200, json={"user_id": 1}),
        ]
    )
    assert MonitoringClient(PROFILE).get_me() == {"user_id": 1}
    assert route.call_count == 2
    assert no_sleep == [1.0]


@respx.mock
def test_get_retries_a_read_timeout(no_sleep):
    mock_token(respx)
    route = respx.get(f"{BASE}/api/auth/me").mock(
        side_effect=[
            httpx.ReadTimeout("slow"),
            httpx.Response(200, json={"user_id": 1}),
        ]
    )
    assert MonitoringClient(PROFILE).get_me() == {"user_id": 1}
    assert route.call_count == 2


@respx.mock
def test_get_stops_after_three_attempts(no_sleep):
    mock_token(respx)
    route = respx.get(f"{BASE}/api/auth/me").mock(
        return_value=httpx.Response(503, json={"detail": "busy"})
    )
    with pytest.raises(httpx.HTTPStatusError):
        MonitoringClient(PROFILE).get_me()
    assert route.call_count == 3
    assert no_sleep == [1.0, 2.0]


@respx.mock
def test_get_does_not_retry_a_500(no_sleep):
    mock_token(respx)
    route = respx.get(f"{BASE}/api/auth/me").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    with pytest.raises(httpx.HTTPStatusError) as caught:
        MonitoringClient(PROFILE).get_me()
    assert route.call_count == 1
    assert no_sleep == []
    message = str(caught.value)
    assert "HTTP 500 on /api/auth/me" in message
    assert "the server may not have it yet" in message
    assert "this CLI is v" in message


@respx.mock
def test_post_is_never_retried(no_sleep):
    mock_token(respx)
    route = respx.post(f"{BASE}/api/profile/widget").mock(
        return_value=httpx.Response(504, json={"detail": "Request Timeout"})
    )
    with pytest.raises(httpx.HTTPStatusError):
        MonitoringClient(PROFILE).create_widget({"type": "table"})
    assert route.call_count == 1
