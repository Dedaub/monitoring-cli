from __future__ import annotations

import time
from pathlib import PurePosixPath
from typing import Any

import httpx

from monitoring_cli.auth import SessionExpiredError, get_access_token
from monitoring_cli.config import Profile


class MonitoringClient:
    def __init__(self, profile: Profile) -> None:
        self._profile = profile
        self._base = profile.base_url

    def _headers(self) -> dict[str, str]:
        token = get_access_token(self._profile)
        return {"Authorization": f"Bearer {token}"}

    def _get(self, path: str, _timeout: float | None = 30.0, **params: Any) -> Any:
        resp = httpx.get(
            f"{self._base}{path}",
            headers=self._headers(),
            params=params,
            timeout=_timeout,
        )
        _raise_for_status(resp, path)
        return resp.json()

    def _post(
        self,
        path: str,
        json: Any = None,
        params: dict | None = None,
        timeout: float | None = None,
    ) -> Any:
        resp = httpx.post(
            f"{self._base}{path}",
            headers=self._headers(),
            json=json,
            params=params,
            timeout=timeout,
        )
        _raise_for_status(resp, path)
        return resp.json()

    def _put(self, path: str, json: object = None, params: dict | None = None) -> None:
        resp = httpx.put(
            f"{self._base}{path}", headers=self._headers(), json=json, params=params
        )
        _raise_for_status(resp, path)

    def _delete(self, path: str, params: dict | None = None) -> None:
        resp = httpx.delete(
            f"{self._base}{path}", headers=self._headers(), params=params
        )
        _raise_for_status(resp, path)

    # --- auth ---

    def get_me(self) -> dict:
        return self._get("/api/auth/me")

    # --- folders ---

    def get_folders_by_entity(self, entity_id: int) -> list[dict]:
        return self._get("/api/folder/entity/{entity_id: int}", entity_id=entity_id)

    def create_folder(self, entity_id: int, path: str) -> list[dict]:
        return self._post(
            "/api/folder/entity/{entity_id: int}",
            json=path,
            params={"entity_id": entity_id},
        )

    def rename_folder(self, folder_id: int, new_path: str) -> None:
        self._put(
            "/api/folder/{folder_id: int}",
            json=new_path,
            params={"folder_id": folder_id},
        )

    def delete_folder(self, folder_id: int) -> None:
        self._delete("/api/folder/{folder_id: int}", params={"folder_id": folder_id})

    # --- queries ---

    def get_queries(self, entity_id: int | None = None) -> list[dict]:
        params: dict[str, Any] = {}
        if entity_id is not None:
            params["entity_id"] = entity_id
        return self._get("/api/profile/tsql/query", **params)

    def get_query(self, query_id: int) -> dict:
        return self._get(f"/api/profile/tsql/query/{query_id}")

    def create_query(self, entity_id: int, folder_id: int, query_name: str) -> int:
        return self._post(
            "/api/profile/tsql/query",
            json={
                "folder_id": folder_id,
                "query_name": query_name,
                "query_text": "",
                "alert_template": "",
                "visibility": "PRIVATE",
                "is_unlisted": False,
                "is_template": False,
            },
            params={"entity_id": entity_id},
        )

    def update_query_text(self, query_id: int, query_text: str) -> None:
        current = self.get_query(query_id)
        current["query_text"] = query_text
        self._put(f"/api/profile/tsql/query/{query_id}", json=current)

    def update_query_alert_settings(
        self,
        query_id: int,
        alert_template: str,
        unique_key: list[str] | None,
    ) -> None:
        current = self.get_query(query_id)
        current["alert_template"] = alert_template
        if unique_key is not None:
            current["unique_key"] = unique_key
        self._put(f"/api/profile/tsql/query/{query_id}", json=current)

    def reset_materialization(self, query_id: int) -> None:
        self._put(f"/api/profile/tsql/query/{query_id}", params={"reset_table": "true"})

    def preview_query(
        self,
        query: str,
        query_id: int,
        entity_id: int,
        network: str | None = None,
    ) -> str:
        return self._post(
            "/api/tsql/query/preview",
            json={
                "query": query,
                "query_id": query_id,
                "query_entity_id": entity_id,
                "network": network,
            },
        )

    def explain_query(
        self,
        query: str,
        query_id: int,
        entity_id: int,
        network: str | None = None,
    ) -> list[str]:
        return self._post(
            "/api/tsql/query/explain",
            json={
                "query": query,
                "query_id": query_id,
                "query_entity_id": entity_id,
                "network": network,
            },
        )

    def execute_query(
        self,
        query: str,
        query_id: int,
        entity_id: int,
        network: str | None = None,
        default_duration: str = "5m",
        default_start_time: str | None = None,
        limit: int = 25,
        offset: int = 0,
        poll_interval: float = 2.0,
        poll_timeout: float = 1800.0,
    ) -> list[dict]:
        task_id = self._post(
            "/api/tsql/query/execute_async",
            json={
                "query": query,
                "query_id": query_id,
                "query_entity_id": entity_id,
                "network": network,
                "default_duration": default_duration,
                "default_start_time": default_start_time,
                "limit": limit,
                "offset": offset,
            },
        )
        deadline = time.monotonic() + poll_timeout
        while time.monotonic() < deadline:
            result = self._get(f"/api/tsql/query/execute_async/{task_id}")
            status = result.get("status")
            if status == "SUCCESS":
                return result.get("result") or []
            if status == "FAILURE":
                raise RuntimeError(result.get("error") or "Query execution failed")
            if status in ("REVOKED", "IGNORED"):
                raise RuntimeError(f"Query was {status}")
            time.sleep(poll_interval)
        raise TimeoutError(f"Query did not complete within {int(poll_timeout // 60)}m")

    # --- run config ---

    def get_run_configs(self, query_id: int) -> dict:
        return self._get(f"/api/profile/tsql/query/{query_id}/config")

    def get_run_config(self, query_id: int, network: str) -> dict:
        return self._get(f"/api/profile/tsql/query/{query_id}/{network}/config")

    def set_run_config(self, query_id: int, network: str, config: dict) -> None:
        self._put(f"/api/profile/tsql/query/{query_id}/{network}/config", json=config)

    def delete_run_config(self, query_id: int, network: str) -> None:
        self._delete(f"/api/profile/tsql/query/{query_id}/{network}/config")

    # --- schema ---

    def get_schema(self) -> dict:
        return self._get("/api/tsql/schema")

    def get_macros(self) -> dict:
        return self._get("/api/tsql/macros")

    # --- logs ---

    def get_logs(
        self,
        query_ids: list[int] | None = None,
        status: str | None = None,
        time_start: float | None = None,
        time_end: float | None = None,
        limit: int = 25,
    ) -> list[dict]:
        params: dict[str, Any] = {"limit": limit}
        if query_ids:
            params["query_ids"] = query_ids
        if status:
            params["status"] = status
        if time_start is not None:
            params["time_start"] = time_start
        if time_end is not None:
            params["time_end"] = time_end
        return self._get("/api/profile/tsql/logs", _timeout=60.0, **params)

    def get_fired_alerts(
        self,
        query_ids: list[int] | None = None,
        time_start: float | None = None,
        time_end: float | None = None,
        after_id: int | None = None,
        limit: int = 25,
    ) -> list[dict]:
        params: dict[str, Any] = {"limit": limit}
        if query_ids:
            params["query_ids"] = query_ids
        if time_start is not None:
            params["time_start"] = time_start
        if time_end is not None:
            params["time_end"] = time_end
        if after_id is not None:
            params["alert_id"] = after_id
        return self._get("/api/profile/tsql/alerts", _timeout=120.0, **params)

    # --- notify ---

    def get_notify_config(self, query_id: int, network: str) -> dict:
        return self._get(f"/api/profile/tsql/query/{query_id}/{network}/notify")

    def set_notify_config(self, query_id: int, network: str, config: dict) -> None:
        self._put(f"/api/profile/tsql/query/{query_id}/{network}/notify", json=config)


def _raise_for_status(resp: httpx.Response, path: str) -> None:
    if resp.status_code == 401:
        raise SessionExpiredError()
    if resp.status_code == 403:
        raise PermissionError(f"Permission denied on {path}")
    if resp.status_code == 404:
        raise NotFoundError(path)
    if resp.status_code == 409:
        raise ConflictError(path)
    if resp.is_error:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise httpx.HTTPStatusError(str(detail), request=resp.request, response=resp)


def resolve_folder_id(folders: list[dict], path: str) -> int:
    for f in folders:
        if f["path"] == path:
            return f["folder_id"]
    raise NotFoundError(f"No folder found at {path}")


def resolve_query_id(folders: list[dict], queries: list[dict], path: str) -> int:
    folder_path = str(PurePosixPath(path).parent)
    query_name = PurePosixPath(path).name
    folder_id = resolve_folder_id(folders, folder_path)
    for q in queries:
        if q["folder_id"] == folder_id and q["query_name"] == query_name:
            return q["query_id"]
    raise NotFoundError(f"No query found at {path}")


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass
