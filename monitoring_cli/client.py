from __future__ import annotations

import contextlib
import time
from collections.abc import Callable
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
        timeout: float | None = 30.0,
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

    def _put(
        self,
        path: str,
        json: object = None,
        params: dict | None = None,
        timeout: float | None = 30.0,
    ) -> Any:
        resp = httpx.put(
            f"{self._base}{path}",
            headers=self._headers(),
            json=json,
            params=params,
            timeout=timeout,
        )
        _raise_for_status(resp, path)
        # Most PUTs return an empty body; parse one only when present so callers
        # that need the response (e.g. move_folder) get it without breaking the
        # many callers that ignore the return value.
        if resp.content:
            try:
                return resp.json()
            except ValueError:
                return None
        return None

    def _delete(
        self, path: str, params: dict | None = None, timeout: float | None = 30.0
    ) -> None:
        resp = httpx.delete(
            f"{self._base}{path}",
            headers=self._headers(),
            params=params,
            timeout=timeout,
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

    def move_folder(self, folder_id: int, entity_id: int, new_folder_id: int) -> dict:
        return self._put(
            "/api/folder/move/{folder_id: int}",
            params={
                "folder_id": folder_id,
                "entity_id": entity_id,
                "new_folder_id": new_folder_id,
            },
        )

    def get_subfolders(self, folder_id: int) -> list[dict]:
        return self._get("/api/folder/subfolders/{folder_id: int}", folder_id=folder_id)

    def get_all_folders(self) -> list[dict]:
        return self._get("/api/folder/")

    # --- entities ---

    def get_entity(self, username: str) -> dict | None:
        return self._get(f"/api/entity/{username}")

    def get_entities_with_public_query(self) -> list[dict] | None:
        return self._get("/api/entity/with_public_query")

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

    def validate_query(
        self,
        query: str,
        query_id: int,
        entity_id: int,
        network: str | None = None,
    ) -> bool:
        """Fast fail-fast compile check. Returns True on valid SQL; the backend
        raises 400 with the exact PG error (line + 'syntax error at or near …')
        on invalid SQL, surfaced as an HTTPStatusError carrying that detail."""
        return self._post(
            "/api/tsql/query/validate",
            json={
                "query": query,
                "query_id": query_id,
                "query_entity_id": entity_id,
                "network": network,
            },
        )

    def query_columns(
        self,
        query: str,
        query_id: int,
        entity_id: int,
        network: str | None = None,
    ) -> list[dict]:
        """Return the query's output columns (name + type) WITHOUT running it.
        Compiles the SQL, so it also validates (400 + detail on bad SQL)."""
        return self._post(
            "/api/tsql/query/metadata",
            json={
                "query": query,
                "query_id": query_id,
                "query_entity_id": entity_id,
                "network": network,
            },
        )

    def format_query(self, query: str) -> str:
        """Pretty-print SQL. Returns the input unchanged when it can't parse."""
        return self._post("/api/tsql/format", json={"query": query})

    def query_dependencies(
        self, query: str, query_id: int, entity_id: int
    ) -> dict[str, list[int]]:
        """Return the {{ref()}} dependencies a query references."""
        return self._post(
            "/api/tsql/query/dependencies",
            json={
                "query": query,
                "query_id": query_id,
                "query_entity_id": entity_id,
            },
        )

    def query_diff(
        self,
        saved_query_id: int,
        new_query: str,
        entity_id: int,
        new_unique_key: list[str] | None = None,
        network: str = "ethereum",
    ) -> dict:
        """Diff a candidate query's output metadata against the saved version."""
        return self._post(
            "/api/tsql/query/diff",
            json={
                "saved_query_id": saved_query_id,
                "new_query": new_query,
                "query_entity_id": entity_id,
                "new_query_unique_key": new_unique_key,
                "network": network,
            },
        )

    def materialize_query(self, query_id: int) -> str:
        """Trigger a materialization run for a query; returns the task uuid."""
        return self._post(f"/api/tsql/query/materialize/{query_id}")

    def get_active_queries(self) -> list[str]:
        """List the task uuids of currently-running async queries."""
        return self._get("/api/tsql/query/execute_async")

    def download_results(self, task_id: str, delimiter: str = ",") -> str:
        """Download a completed async query's results as CSV text."""
        resp = httpx.get(
            f"{self._base}/api/tsql/query/download_async/{task_id}",
            headers=self._headers(),
            params={"delimiter": delimiter},
            timeout=120.0,
        )
        _raise_for_status(resp, "/api/tsql/query/download_async")
        return resp.text

    # --- query status / history ---

    def get_query_status(self, query_id: int) -> dict | None:
        return self._get("/api/profile/tsql/status", query_id=query_id)

    def get_query_history(self, query_id: int, limit: int = 100) -> list[dict]:
        return self._get("/api/profile/tsql/history", query_id=query_id, limit=limit)

    # --- query organization ---

    def move_query(self, query_id: int, new_folder_id: int) -> None:
        self._put(
            f"/api/profile/tsql/query/move/{query_id}",
            params={"new_folder_id": new_folder_id},
        )

    def star_query(self, query_id: int) -> None:
        self._put(f"/api/profile/tsql/{query_id}/star")

    def unstar_query(self, query_id: int) -> None:
        self._delete(f"/api/profile/tsql/{query_id}/star")

    def share_query(self, query_id: int, team_id: int, perm: str) -> None:
        self._put(
            f"/api/profile/tsql/{query_id}/share/{team_id}", params={"perm": perm}
        )

    def unshare_query(self, query_id: int, team_id: int) -> None:
        self._delete(f"/api/profile/tsql/{query_id}/share/{team_id}")

    def get_query_by_key(self, key: str) -> dict:
        return self._get(f"/api/profile/tsql/query/key/{key}")

    # --- NL → SQL generation ---

    def generate_query(
        self,
        description: str,
        networks: list[str],
        context_hints: list[str] | None = None,
    ) -> dict:
        """Spawn the platform's own NL→SQL generation job."""
        return self._post(
            "/api/profile/tsql/generate",
            json={
                "description": description,
                "networks": networks,
                "context_hints": context_hints,
            },
        )

    def get_generation_job(self, job_id: str) -> dict:
        return self._get(f"/api/profile/tsql/generate/{job_id}")

    def promote_generation_job(
        self,
        job_id: str,
        enable_notifications: bool = True,
        alert_email: str | None = None,
        folder_name: str | None = None,
        webhook_url: str | None = None,
    ) -> dict:
        """Promote a finished generation job into a saved query."""
        return self._post(
            f"/api/profile/tsql/generate/{job_id}/promote",
            json={
                "enable_notifications": enable_notifications,
                "alert_email": alert_email,
                "folder_name": folder_name,
                "webhook_url": webhook_url,
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
        on_start: Callable[[str], None] | None = None,
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
        # task_id now exists server-side, so everything that could interrupt before we
        # finish (the on_start callback, the poll loop) goes inside the try, and every
        # revoke is best-effort — a failed DELETE must never mask the interrupt/timeout
        # we actually want to surface.
        deadline = time.monotonic() + poll_timeout
        try:
            if on_start is not None:
                on_start(task_id)
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
        except KeyboardInterrupt:
            # Local Ctrl-C stops polling but the server task keeps running — revoke it.
            with contextlib.suppress(Exception):
                self.cancel_query(task_id)
            raise
        # Local poll timed out; the server task is still running — revoke it too.
        with contextlib.suppress(Exception):
            self.cancel_query(task_id)
        window = (
            f"{int(poll_timeout)}s"
            if poll_timeout < 60
            else f"{int(poll_timeout // 60)}m"
        )
        raise TimeoutError(f"Query did not complete within {window}")

    def execute_query_sync(
        self,
        query: str,
        query_id: int,
        entity_id: int,
        network: str | None = None,
        default_duration: str = "5m",
        default_start_time: str | None = None,
        limit: int = 100,
        offset: int = 0,
        timeout: float = 120.0,
    ) -> list[dict]:
        """Synchronous execute — returns rows directly, no task polling. Use the
        async execute_query when you need cancel-on-Ctrl-C / server-side revoke."""
        return self._post(
            "/api/tsql/query/execute",
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
            timeout=timeout,
        )

    def cancel_query(self, task_id: str) -> None:
        """Revoke a running async query task by id. Best-effort and idempotent —
        the backend returns 200 even for an unknown/already-finished task."""
        self._delete(f"/api/tsql/query/execute_async/{task_id}")

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

    def get_all_notify_configs(self, query_id: int) -> dict:
        """Notification configs across every network the query is deployed to."""
        return self._get(f"/api/profile/tsql/query/{query_id}/notify")

    def set_notify_config(self, query_id: int, network: str, config: dict) -> None:
        self._put(f"/api/profile/tsql/query/{query_id}/{network}/notify", json=config)

    # --- webhooks ---
    # NOTE: the backend route really does carry a doubled "/api/profile" prefix,
    # and delete doubles "webhook" too — these literal paths are intentional.

    def create_webhook(
        self,
        name: str,
        url: str,
        description: str | None = None,
        secret: str | None = None,
    ) -> dict:
        return self._post(
            "/api/profile/api/profile/webhook",
            json={
                "name": name,
                "url": url,
                "description": description,
                "secret": secret,
            },
        )

    def test_webhook(self, url: str, secret: str | None = None) -> dict:
        return self._post(
            "/api/profile/api/profile/webhook/test",
            json={"url": url, "secret": secret},
        )

    def list_webhooks(self) -> list[dict]:
        return self._get("/api/profile/api/profile/webhooks")

    def get_webhook(self, webhook_id: int) -> dict:
        return self._get(f"/api/profile/api/profile/webhook/{webhook_id}")

    def update_webhook(
        self,
        webhook_id: int,
        name: str,
        url: str,
        description: str | None = None,
        secret: str | None = None,
    ) -> dict:
        return self._put(
            f"/api/profile/api/profile/webhook/{webhook_id}",
            json={
                "name": name,
                "url": url,
                "description": description,
                "secret": secret,
            },
        )

    def delete_webhook(self, webhook_id: int) -> None:
        self._delete(f"/api/profile/api/profile/webhook/webhook/{webhook_id}")

    # --- telegram ---

    def get_telegram_code(self, query_id: int) -> Any:
        """Get the Telegram bot linking code for a query's notifications."""
        return self._get("/api/profile/telegram_bot/code", query_id=query_id)

    # --- alert filters (saved alert searches) ---

    def create_alert_filter(
        self,
        filter_name: str,
        query_ids: list[int] | None = None,
        chain_ids: list[int] | None = None,
        colour: str | None = None,
    ) -> int:
        return self._post(
            "/api/profile/alert-filter",
            json={
                "filter_name": filter_name,
                "query_ids": query_ids,
                "chain_ids": chain_ids,
                "colour": colour,
            },
        )

    def list_alert_filters(self) -> list[dict]:
        return self._get("/api/profile/alert-filters")

    def get_alert_filter(self, search_id: int) -> dict:
        return self._get(f"/api/profile/alert-filter/{search_id}")

    def update_alert_filter(
        self,
        search_id: int,
        filter_name: str,
        query_ids: list[int] | None = None,
        chain_ids: list[int] | None = None,
        colour: str | None = None,
    ) -> None:
        self._put(
            f"/api/profile/alert-filter/{search_id}",
            json={
                "filter_name": filter_name,
                "query_ids": query_ids,
                "chain_ids": chain_ids,
                "colour": colour,
            },
        )

    def delete_alert_filter(self, search_id: int) -> None:
        self._delete(f"/api/profile/alert-filter/{search_id}")


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
