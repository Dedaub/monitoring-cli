import json
import pytest
import respx
import httpx

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
