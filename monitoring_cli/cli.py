from __future__ import annotations

import contextlib
import datetime
import json
import os
import select
import shutil
import sys
import time
from importlib.resources import as_file, files
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, NamedTuple, NoReturn

import httpx
import typer
from rich.console import Console
from rich.markup import escape

from monitoring_cli import output, widgets
from monitoring_cli.auth import (
    AuthError,
    DeviceFlowExpiredError,
    SessionExpiredError,
    poll_token,
    revoke_token,
    start_device_flow,
    token_type,
)
from monitoring_cli.client import (
    ConflictError,
    MonitoringClient,
    NotFoundError,
    resolve_folder_id,
    resolve_query_id,
)
from monitoring_cli.config import (
    DEFAULT_BASE_URL,
    DEFAULT_CLIENT_ID,
    DEFAULT_OIDC_HOST,
    DEFAULT_PROFILE,
    DEFAULT_REALM,
    REFRESH_TOKEN_ENV,
    Config,
    ConfigError,
    NotLoggedInError,
    Profile,
    ProfileNotFoundError,
)
from monitoring_cli.version import cli_version

app = typer.Typer(help="Dedaub Monitoring CLI")
err = Console(stderr=True)
out = Console()


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"dedaub-monitoring {cli_version()}")
        raise typer.Exit()


@app.callback()
def _main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_print_version,
            is_eager=True,
            help="Print the CLI version and exit.",
        ),
    ] = False,
) -> None:
    """Dedaub Monitoring CLI"""


# Single network is currently supported across config/alert commands.
_NETWORK = "ethereum"

ProfileOption = Annotated[
    str | None, typer.Option("--profile", "-p", help="Profile name", hidden=True)
]


def _parse_ts(ts: str | None) -> float | None:
    if ts is None:
        return None
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def _session_expired_message() -> str:
    if os.environ.get(REFRESH_TOKEN_ENV):
        return (
            f"Session expired: the token in {REFRESH_TOKEN_ENV} is no longer valid.\n"
            "Run `dedaub-monitoring token` where you are logged in, "
            f"and set {REFRESH_TOKEN_ENV} to the new value."
        )
    return "Session expired. Run: dedaub-monitoring login"


def _exit_error(e: Exception) -> NoReturn:
    if isinstance(e, SessionExpiredError):
        err.print(_session_expired_message())
    else:
        err.print(f"Error: {e}")
    raise typer.Exit(1)


def _load_client(profile_name: str | None) -> tuple[MonitoringClient, Profile]:
    env_token = os.environ.get(REFRESH_TOKEN_ENV)
    try:
        if env_token:
            return _env_client(profile_name, env_token)
        config = Config.load()
        key = profile_name or config.default
        profile = config.get_profile(key)
        return MonitoringClient(
            profile, on_refresh_token=lambda t: _store_refresh_token(key, t)
        ), profile
    except NotLoggedInError:
        err.print("Not logged in. Run: dedaub-monitoring login")
        raise typer.Exit(1)
    except ProfileNotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except ConfigError as e:
        err.print(f"{e}\nRun: dedaub-monitoring login")
        raise typer.Exit(1)


def _env_client(
    profile_name: str | None, refresh_token: str
) -> tuple[MonitoringClient, Profile]:
    # Headless mode: take the endpoints from a stored profile when one exists,
    # else use the production defaults. The token stays in memory only.
    try:
        profile = Config.load().get_profile(profile_name)
    except NotLoggedInError:
        profile = Profile(
            base_url=DEFAULT_BASE_URL,
            oidc_host=DEFAULT_OIDC_HOST,
            client_id=DEFAULT_CLIENT_ID,
            realm=DEFAULT_REALM,
        )
    profile.refresh_token = refresh_token
    return MonitoringClient(profile), profile


def _store_refresh_token(profile_name: str, refresh_token: str) -> None:
    # Reload first so a concurrent login/logout of another profile is kept.
    # A failed write only costs the rotation, so warn and continue.
    try:
        config = Config.load()
        config.get_profile(profile_name).refresh_token = refresh_token
        config.save()
    except (NotLoggedInError, ProfileNotFoundError):
        pass
    except (ConfigError, OSError) as e:
        err.print(
            f"Warning: could not save the renewed login token ({e}). "
            "The login will expire at its original time."
        )


@app.command()
def login(
    profile: ProfileOption = DEFAULT_PROFILE,
    base_url: Annotated[str, typer.Option(help="Backend base URL")] = DEFAULT_BASE_URL,
    oidc_host: Annotated[str, typer.Option(help="Keycloak host")] = DEFAULT_OIDC_HOST,
    client_id: Annotated[
        str, typer.Option(help="Keycloak client ID")
    ] = DEFAULT_CLIENT_ID,
    realm: Annotated[str, typer.Option(help="Keycloak realm")] = DEFAULT_REALM,
) -> None:
    """Authenticate via browser (OAuth2 Device Flow)."""
    profile = profile or DEFAULT_PROFILE
    p = Profile(
        base_url=base_url, oidc_host=oidc_host, client_id=client_id, realm=realm
    )
    try:
        flow = start_device_flow(p)
    except Exception as e:
        err.print(f"Failed to start device flow: {e}")
        raise typer.Exit(1)

    typer.echo(
        f"\nOpen this URL to authenticate:\n  {flow['verification_uri_complete']}\n"
    )
    typer.echo("Waiting for authentication...")

    try:
        refresh_token = poll_token(
            p,
            flow["device_code"],
            interval=flow.get("interval", 5),
            expires_in=flow.get("expires_in", 600),
        )
    except DeviceFlowExpiredError:
        err.print("Login timed out. Please try again.")
        raise typer.Exit(1)
    except AuthError as e:
        err.print(f"Authentication failed: {e}")
        raise typer.Exit(1)

    p.refresh_token = refresh_token

    typ = token_type(refresh_token)
    if typ != "Offline":
        err.print(
            f"Warning: the server gave a {typ or 'unknown'} token, not an offline "
            "token. This login expires with the normal session, so you must log "
            f"in again sooner. Ask a Dedaub admin to give the {client_id} client "
            "and your user the offline_access scope."
        )

    try:
        config = Config.load()
    except NotLoggedInError:
        config = Config(default=profile, profiles={})

    config.upsert_profile(profile, p)
    config.save()
    typer.echo("Logged in.")


@app.command()
def logout(
    profile: ProfileOption = None,
    local: Annotated[
        bool,
        typer.Option(
            "--local",
            help="Remove only the local copy. Tokens exported with `token` keep working.",
        ),
    ] = False,
) -> None:
    """Remove stored credentials for a profile and revoke them on the server."""
    try:
        config = Config.load()
    except NotLoggedInError:
        typer.echo("Not logged in.")
        return

    key = profile or config.default
    try:
        stored = config.get_profile(key)
    except ProfileNotFoundError:
        typer.echo("Not logged in.")
        return
    if stored.refresh_token and not local:
        try:
            revoke_token(stored)
        except AuthError as e:
            err.print(f"Warning: could not revoke the token on the server: {e}")
    config.remove_profile(key)
    config.save()
    typer.echo("Logged out.")


@app.command()
def token(profile: ProfileOption = None) -> None:
    """Print the stored refresh token, for headless use (CI, containers).

    Export it as DEDAUB_MONITORING_REFRESH_TOKEN where no browser login is
    possible. Treat the value as a password.
    """
    try:
        config = Config.load()
        stored = config.get_profile(profile).refresh_token
    except (NotLoggedInError, ProfileNotFoundError, ConfigError):
        stored = None
    if not stored:
        err.print("Not logged in. Run: dedaub-monitoring login")
        raise typer.Exit(1)
    typer.echo(stored)


@app.command()
def entities(profile: ProfileOption = None) -> None:
    """List entities (user + orgs) available to you."""
    client, _ = _load_client(profile)
    try:
        me = client.get_me()
    except Exception as e:
        _exit_error(e)

    rows = [{"username": me["username"], "entity_id": me["entity_id"]}]
    for sub in me.get("subscriptions") or []:
        rows.append(
            {
                "username": sub.get("organization_name") or sub.get("username", ""),
                "entity_id": sub["entity_id"],
            }
        )
    output.format_entities(rows)


@app.command()
def tree(
    profile: ProfileOption = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (defaults to your own)")
    ] = None,
) -> None:
    """Show the query file tree for an entity. Use --entity-id to view another entity's tree."""
    client, _ = _load_client(profile)
    try:
        if entity_id is None:
            me = client.get_me()
            entity_id = me["entity_id"]
            entity_name = me["username"]
        else:
            entity_name = str(entity_id)

        folders = client.get_folders_by_entity(entity_id)
        queries = client.get_queries(entity_id=entity_id)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)

    output.format_tree(folders, queries, entity_name)


@app.command()
def create_folder(
    path: Annotated[
        str,
        typer.Argument(
            help="Path of the new folder, e.g. /MyDir/NewFolder (last component is the folder name)"
        ),
    ],
    profile: ProfileOption = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (defaults to your own)")
    ] = None,
) -> None:
    """Create a folder. Intermediate directories are created automatically. Use --entity-id to target another entity."""
    client, _ = _load_client(profile)
    try:
        if entity_id is None:
            entity_id = client.get_me()["entity_id"]
        result = client.create_folder(entity_id, path)
    except ConflictError:
        err.print(f"Folder already exists at {path}")
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    if not result:
        typer.echo(f"Folder already exists at {path}.")
    else:
        typer.echo(f"Created {len(result)} folder(s).")


@app.command()
def rename_folder(
    new_path: Annotated[str, typer.Option(help="New folder path")],
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Folder ID")] = None,
    path: Annotated[str | None, typer.Option(help="Current folder path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (defaults to your own)")
    ] = None,
) -> None:
    """Rename a folder. Specify with --id <folder_id>, or --path /Folder [--entity-id]."""
    client, _ = _load_client(profile)
    try:
        folder_id = _resolve_folder(client, id, path, entity_id)
        client.rename_folder(folder_id, new_path)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except ConflictError:
        err.print(f"A folder already exists at {new_path}")
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Renamed to {new_path}.")


@app.command()
def delete_folder(
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Folder ID")] = None,
    path: Annotated[str | None, typer.Option(help="Folder path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (defaults to your own)")
    ] = None,
) -> None:
    """Delete a folder. Specify with --id <folder_id>, or --path /Folder [--entity-id]."""
    client, _ = _load_client(profile)
    try:
        folder_id = _resolve_folder(client, id, path, entity_id)
        client.delete_folder(folder_id)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo("Deleted.")


def _resolve_folder(
    client: MonitoringClient,
    folder_id: int | None,
    path: str | None,
    entity_id: int | None,
) -> int:
    if folder_id is not None:
        return folder_id
    if path is None:
        err.print("Provide either --id or --path.")
        raise typer.Exit(1)
    if entity_id is None:
        entity_id = client.get_me()["entity_id"]
    folders = client.get_folders_by_entity(entity_id)
    return resolve_folder_id(folders, path)


def _resolve_query(
    client: MonitoringClient,
    query_id: int | None,
    path: str | None,
    entity_id: int | None,
) -> int:
    if query_id is not None:
        return query_id
    if path is None:
        err.print("Provide either --id or --path.")
        raise typer.Exit(1)
    if entity_id is None:
        entity_id = client.get_me()["entity_id"]
    folders = client.get_folders_by_entity(entity_id)
    queries = client.get_queries(entity_id=entity_id)
    return resolve_query_id(folders, queries, path)


def _read_ready_stdin() -> str:
    """Return piped stdin text, but only when data is already waiting.

    `isatty()` is False not just for a closed stdin but also for an *open but
    empty* one (e.g. the CLI launched from an agent/subprocess that inherits an
    idle stdin), where a bare `sys.stdin.read()` blocks forever. Gating the read
    on a zero-timeout `select()` means we only read when bytes are ready, so an
    idle stdin returns immediately instead of hanging.

    Contract: this polls once with no wait, so stdin must already hold data.
    Every supported way of piping SQL buffers it up front — a heredoc, `echo |`,
    or `< file` all have the bytes ready before the command runs — so this is
    exact for real usage. A producer that emits its first byte *after* the poll
    (an unusual `slow-generator | cmd` pipe) is treated as no input; pass the SQL
    as an argument in that case. Returns "" when stdin is a TTY or has nothing
    waiting.
    """
    if sys.stdin.isatty():
        return ""
    try:
        readable, _, _ = select.select([sys.stdin], [], [], 0)
    except (OSError, ValueError):
        # Platforms where select() can't poll stdin (e.g. Windows pipes):
        # preserve the prior read-until-EOF behavior.
        readable = [sys.stdin]
    return sys.stdin.read() if readable else ""


def _resolve_query_text_and_owner(
    client: MonitoringClient,
    query_id: int,
    query_text: str | None,
    entity_id: int | None,
) -> tuple[str, int]:
    """Resolve query text (from arg, piped stdin, or stored) and the owning entity id."""
    # Fetch the stored query at most once, even when both the text and the
    # owner entity id have to be read from it.
    stored: dict | None = None
    if query_text is None:
        # Piped SQL if any; otherwise fall back to the stored query text rather
        # than running an empty query.
        stdin_text = _read_ready_stdin()
        if stdin_text.strip():
            query_text = stdin_text
        else:
            stored = client.get_query(query_id)
            query_text = stored.get("query_text", "")
    if entity_id is None:
        if stored is None:
            stored = client.get_query(query_id)
        entity_id = stored["owner"]["entity_id"]
    return query_text, entity_id


@app.command()
def query_metadata(
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Query ID")] = None,
    path: Annotated[str | None, typer.Option(help="Query path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (defaults to your own)")
    ] = None,
) -> None:
    """Print full metadata for a query as JSON. Specify with --id <query_id>, or --path /Folder/QueryName [--entity-id]."""
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        metadata = client.get_query(qid)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_query_metadata(metadata)


@app.command()
def read_query(
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Query ID")] = None,
    path: Annotated[str | None, typer.Option(help="Query path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (defaults to your own)")
    ] = None,
) -> None:
    """Print the SQL text of a query. Specify with --id <query_id>, or --path /Folder/QueryName [--entity-id]."""
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        query = client.get_query(qid)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_query_text(query.get("query_text", ""))


@app.command()
def create_query(
    path: Annotated[
        str,
        typer.Argument(
            help="Full path of the new query, e.g. /MyDir/MyQuery (last component is the query name)"
        ),
    ],
    profile: ProfileOption = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (defaults to your own)")
    ] = None,
) -> None:
    """Create a new empty query. The folder must already exist. Use --entity-id to target another entity."""
    client, _ = _load_client(profile)
    try:
        if entity_id is None:
            entity_id = client.get_me()["entity_id"]
        _ppath = PurePosixPath(path)
        folder_path = str(_ppath.parent)
        query_name = _ppath.name
        folders = client.get_folders_by_entity(entity_id)
        folder_id = resolve_folder_id(folders, folder_path)
        query_id = client.create_query(entity_id, folder_id, query_name)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except ConflictError:
        err.print(f"A query named '{query_name}' already exists in that folder.")
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Created query (id: {query_id}).")


@app.command()
def write_query(
    query_text: Annotated[
        str | None, typer.Argument(help="SQL text (omit to read from stdin)")
    ] = None,
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Query ID")] = None,
    path: Annotated[str | None, typer.Option(help="Query path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (defaults to your own)")
    ] = None,
) -> None:
    """Update the SQL text of a query. Specify with --id <query_id>, or --path /Folder/QueryName [--entity-id]. Pass SQL as argument or pipe via stdin."""
    if query_text is None:
        # write_query has no stored fallback, so require piped SQL — but never
        # block on an idle stdin; fail fast instead.
        query_text = _read_ready_stdin()
        if not query_text.strip():
            err.print("No query text provided. Pass as argument or pipe via stdin.")
            raise typer.Exit(1)
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        client.update_query_text(qid, query_text)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo("Query updated.")


@app.command()
def get_schema(
    profile: ProfileOption = None,
    network: Annotated[
        str | None, typer.Option(help="Filter by network, e.g. ethereum")
    ] = None,
    table: Annotated[
        str | None, typer.Option(help="Filter tables by name substring")
    ] = None,
    macros: Annotated[
        bool, typer.Option(help="Show available macros instead of tables")
    ] = False,
) -> None:
    """Show available tables and columns (or macros with --macros). Filter with --network and --table."""
    client, _ = _load_client(profile)
    try:
        if macros:
            result = client.get_macros()
            output.format_macros(result)
        else:
            result = client.get_schema()
            output.format_schema(result, network=network, table_filter=table)
    except Exception as e:
        _exit_error(e)


@app.command()
def run_query(
    id: Annotated[int, typer.Option(help="Query ID")],
    query_text: Annotated[
        str | None, typer.Argument(help="SQL text (omit to use stored query text)")
    ] = None,
    profile: ProfileOption = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (defaults to query owner)")
    ] = None,
    network: Annotated[
        str | None,
        typer.Option(help="Network name, e.g. ethereum. Omit to load all networks."),
    ] = None,
    duration: Annotated[
        str,
        typer.Option(
            help="Look-back window that ends at --end-time (default: now), e.g. 5m, 24h, 7d"
        ),
    ] = "5m",
    end_time: Annotated[
        str | None,
        typer.Option(
            help="END of the window (ISO 8601), e.g. 2025-01-01T12:00:00Z. The query reads [end-time - duration, end-time]. Omit for now."
        ),
    ] = None,
    start_time: Annotated[
        str | None,
        # Deprecated alias: the server field is `default_start_time`, but it anchors
        # the END of the window, so the old name misled readers into passing a start.
        typer.Option(hidden=True, help="Deprecated alias for --end-time."),
    ] = None,
    limit: Annotated[int, typer.Option(help="Max rows (max 500)")] = 25,
    offset: Annotated[int, typer.Option(help="Row offset for pagination")] = 0,
    timeout: Annotated[
        float,
        typer.Option(
            help="Max seconds to wait before killing the query (the server task is revoked, not just local polling). Tuning budget: ~30 fast, 120 absolute max."
        ),
    ] = 1800.0,
) -> None:
    """Execute a query and print results. Requires --id. Pass SQL as argument or via stdin; omit to run the stored query text. The window is [--end-time - --duration, --end-time]. Ctrl-C (or hitting --timeout) revokes the server-side task."""
    if end_time is not None and start_time is not None:
        err.print(
            "Pass only --end-time. --start-time is a deprecated alias of it, not a window start."
        )
        raise typer.Exit(2)
    end_time = end_time if end_time is not None else start_time
    client, _ = _load_client(profile)
    try:
        query_text, entity_id = _resolve_query_text_and_owner(
            client, id, query_text, entity_id
        )
        results = client.execute_query(
            query_text,
            id,
            entity_id,
            network=network,
            default_duration=duration,
            default_start_time=end_time,
            limit=limit,
            offset=offset,
            poll_timeout=timeout,
            on_start=lambda tid: err.print(f"task {tid} (Ctrl-C to cancel)"),
        )
    except KeyboardInterrupt:
        err.print("Cancelled — server task revoked.")
        raise typer.Exit(130)
    except TimeoutError as e:
        err.print(
            f"{e} — task revoked. Shrink --duration, or raise --timeout (max 120) to widen the look-back."
        )
        raise typer.Exit(1)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_query_results(results)


@app.command()
def cancel_query(
    task_id: Annotated[
        str, typer.Option(help="Async task id (printed by run-query when it starts)")
    ],
    profile: ProfileOption = None,
) -> None:
    """Revoke a running async query task by its id. Idempotent — safe to call on an unknown/finished task."""
    client, _ = _load_client(profile)
    try:
        client.cancel_query(task_id)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Revoked task {task_id}.")


@app.command()
def get_config(
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Query ID")] = None,
    path: Annotated[str | None, typer.Option(help="Query path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (for path lookup)")
    ] = None,
    network: Annotated[
        str, typer.Option(help="Network the config applies to, e.g. ethereum")
    ] = _NETWORK,
) -> None:
    """Show materialization/scheduling config for a query. Specify with --id <query_id> or --path /Folder/QueryName."""
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        cfg = client.get_run_config(qid, network)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_query_metadata(cfg)


@app.command()
def set_config(
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Query ID")] = None,
    path: Annotated[str | None, typer.Option(help="Query path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (for path lookup)")
    ] = None,
    network: Annotated[
        str, typer.Option(help="Network the config applies to, e.g. ethereum")
    ] = _NETWORK,
    materialize: Annotated[
        str, typer.Option(help="Materialization type: TABLE, VIEW, INCREMENTAL")
    ] = "TABLE",
    frequency: Annotated[
        int | None,
        typer.Option(help="Run frequency in seconds, e.g. 3600 for hourly"),
    ] = None,
    incrementalization: Annotated[
        str | None,
        typer.Option(
            help="Incremental strategy: IGNORE or UPSERT (required when --materialize INCREMENTAL)"
        ),
    ] = None,
    backfill: Annotated[bool, typer.Option(help="Backfill from genesis block")] = False,
    immediate: Annotated[
        bool, typer.Option(help="Materialize immediately once")
    ] = False,
) -> None:
    """Set materialization/scheduling config for a query. Specify with --id <query_id> or --path /Folder/QueryName."""
    if materialize == "INCREMENTAL" and incrementalization is None:
        err.print(
            "--incrementalization is required when --materialize is INCREMENTAL (use IGNORE or UPSERT)"
        )
        raise typer.Exit(1)
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        client.set_run_config(
            qid,
            network,
            {
                "materialize": materialize,
                "frequency": frequency,
                "incrementalization": incrementalization,
                "needs_backfilling": backfill,
                "immediate": immediate,
            },
        )
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Config saved for query {qid}.")


@app.command()
def enable_alerts(
    frequency: Annotated[
        int, typer.Option(help="Run frequency in seconds, e.g. 3600 for hourly")
    ],
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Query ID")] = None,
    path: Annotated[str | None, typer.Option(help="Query path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (for path lookup)")
    ] = None,
    network: Annotated[
        str, typer.Option(help="Network the alert runs on, e.g. ethereum")
    ] = _NETWORK,
    incrementalization: Annotated[
        str, typer.Option(help="Incremental strategy: IGNORE or UPSERT")
    ] = "IGNORE",
    alert_template: Annotated[
        str | None,
        typer.Option(
            help="Jinja2 alert message template. Columns from query results are available as variables, e.g. '{{from_a}} sent {{amount}} to {{to_a}}'. Uses stored value if already set."
        ),
    ] = None,
    unique_key: Annotated[
        str | None,
        typer.Option(
            help="Comma-separated column(s) for deduplication, e.g. tx_hash,log_index. Uses stored value if already set."
        ),
    ] = None,
    email: Annotated[bool, typer.Option(help="Send email notifications")] = False,
    webhook_id: Annotated[
        int | None, typer.Option(help="Webhook ID for notifications")
    ] = None,
) -> None:
    """Enable alerts for a query: sets materialization to INCREMENTAL and turns on notifications. Specify with --id <query_id> or --path /Folder/QueryName."""
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        current = client.get_query(qid)
        resolved_template = (
            alert_template
            if alert_template is not None
            else current.get("alert_template") or ""
        )
        stored_key = current.get("unique_key")
        resolved_unique_key: list[str] | None
        if unique_key is not None:
            resolved_unique_key = [k.strip() for k in unique_key.split(",")]
        elif stored_key:
            resolved_unique_key = stored_key
        else:
            resolved_unique_key = None
        if not resolved_template:
            err.print(
                "--alert-template is required (no stored template found for this query)"
            )
            raise typer.Exit(1)
        if not resolved_unique_key:
            err.print(
                "--unique-key is required (no stored unique key found for this query)"
            )
            raise typer.Exit(1)
        client.update_query_alert_settings(qid, resolved_template, resolved_unique_key)
        client.set_run_config(
            qid,
            network,
            {
                "materialize": "INCREMENTAL",
                "frequency": frequency,
                "incrementalization": incrementalization,
                "needs_backfilling": False,
                "immediate": False,
            },
        )
        client.set_notify_config(
            qid,
            network,
            {
                "notify": True,
                "alert_email": email,
                "webhook_id": webhook_id,
            },
        )
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Alerts enabled for query {qid}.")


@app.command()
def get_logs(
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Filter by query ID")] = None,
    status: Annotated[
        str | None,
        typer.Option(help="Filter by status: SUCCESS, FAIL, WARNING, TIMEOUT"),
    ] = None,
    since: Annotated[
        str | None,
        typer.Option(help="Show logs after this time, e.g. 2026-05-07T17:00:00Z"),
    ] = None,
    limit: Annotated[int, typer.Option(help="Number of results")] = 10,
    before: Annotated[
        str | None,
        typer.Option(
            help="Next-page cursor: start_ts of last row from previous result"
        ),
    ] = None,
) -> None:
    """List query execution logs. Filter by --id, --status, --since. Paginate with --before."""
    client, _ = _load_client(profile)
    try:
        results = client.get_logs(
            query_ids=[id] if id is not None else None,
            status=status,
            time_start=_parse_ts(since),
            time_end=_parse_ts(before),
            limit=limit,
        )
    except Exception as e:
        _exit_error(e)
    output.format_logs(results)


@app.command()
def get_alerts(
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Filter by query ID")] = None,
    since: Annotated[
        str | None,
        typer.Option(help="Show alerts after this time, e.g. 2026-05-07T17:00:00Z"),
    ] = None,
    before: Annotated[
        str | None,
        typer.Option(help="Show alerts before this time, e.g. 2026-05-07T18:00:00Z"),
    ] = None,
    limit: Annotated[int, typer.Option(help="Number of results")] = 10,
    after_id: Annotated[
        int | None,
        typer.Option(help="Next-page cursor: last alert ID from previous result"),
    ] = None,
) -> None:
    """List fired alert events. Filter by --id, --since, --before. Paginate with --after-id."""
    client, _ = _load_client(profile)
    try:
        results = client.get_fired_alerts(
            query_ids=[id] if id is not None else None,
            time_start=_parse_ts(since),
            time_end=_parse_ts(before),
            after_id=after_id,
            limit=limit,
        )
    except Exception as e:
        _exit_error(e)
    output.format_fired_alerts(results)


@app.command()
def disable_alerts(
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Query ID")] = None,
    path: Annotated[str | None, typer.Option(help="Query path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (for path lookup)")
    ] = None,
    network: Annotated[
        str, typer.Option(help="Network the alert runs on, e.g. ethereum")
    ] = _NETWORK,
) -> None:
    """Disable notifications for a query (materialization is left unchanged). Specify with --id <query_id> or --path /Folder/QueryName."""
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        client.set_notify_config(
            qid, network, {"notify": False, "alert_email": False, "webhook_id": None}
        )
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Alerts disabled for query {qid}.")


@app.command()
def reset_materialization(
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Query ID")] = None,
    path: Annotated[str | None, typer.Option(help="Query path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (for path lookup)")
    ] = None,
) -> None:
    """Reset the materialized table for a query, forcing a full recompute on next run. Specify with --id <query_id> or --path /Folder/QueryName."""
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        client.reset_materialization(qid)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Materialization reset for query {qid}.")


@app.command()
def list_alerts(
    profile: ProfileOption = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (defaults to your own)")
    ] = None,
    network: Annotated[
        str, typer.Option(help="Network to check for enabled alerts, e.g. ethereum")
    ] = _NETWORK,
) -> None:
    """List all queries that currently have alerts enabled."""
    client, _ = _load_client(profile)
    try:
        if entity_id is None:
            entity_id = client.get_me()["entity_id"]
        queries = client.get_queries(entity_id=entity_id)
        folders = client.get_folders_by_entity(entity_id)
        alerted = [
            q
            for q in queries
            if client.get_notify_config(q["query_id"], network).get("notify")
        ]
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    if not alerted:
        typer.echo("No queries with alerts enabled.")
        return
    output.format_alert_queries(alerted, folders)


@app.command()
def preprocess_query(
    id: Annotated[int, typer.Option(help="Query ID for macro context")],
    query_text: Annotated[
        str | None, typer.Argument(help="SQL text (omit to use stored query text)")
    ] = None,
    profile: ProfileOption = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (defaults to your own)")
    ] = None,
    network: Annotated[
        str | None, typer.Option(help="Network name, e.g. ethereum")
    ] = None,
) -> None:
    """Render DedaubQL macros and print the resulting SQL. Omit SQL to use the stored query text."""
    client, _ = _load_client(profile)
    try:
        query_text, entity_id = _resolve_query_text_and_owner(
            client, id, query_text, entity_id
        )
        result = client.preview_query(query_text, id, entity_id, network)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_query_text(result)


@app.command()
def explain_query(
    id: Annotated[int, typer.Option(help="Query ID for macro context")],
    query_text: Annotated[
        str | None, typer.Argument(help="SQL text (omit to use stored query text)")
    ] = None,
    profile: ProfileOption = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (defaults to your own)")
    ] = None,
    network: Annotated[
        str | None, typer.Option(help="Network name, e.g. ethereum")
    ] = None,
) -> None:
    """Print the query's real PostgreSQL EXPLAIN plan (the same plan app.dedaub.com shows) — it plans but
    does not execute, so it's free. Read it for index choice / Seq-Scan-vs-index-scan; its cost/row
    estimates are inflated (the planner can't prune chunks for get_historical_block_number(), so it assumes
    all chunks). Omit SQL to use the stored query text."""
    client, _ = _load_client(profile)
    try:
        query_text, entity_id = _resolve_query_text_and_owner(
            client, id, query_text, entity_id
        )
        lines = client.explain_query(query_text, id, entity_id, network)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_lines(lines)


@app.command()
def validate_query(
    id: Annotated[int, typer.Option(help="Query ID for macro context")],
    query_text: Annotated[
        str | None, typer.Argument(help="SQL text (omit to use stored query text)")
    ] = None,
    profile: ProfileOption = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (defaults to your own)")
    ] = None,
    network: Annotated[
        str | None, typer.Option(help="Network name, e.g. ethereum")
    ] = None,
) -> None:
    """Fast compile check (no execution): exits 0 if the SQL is valid, else prints the exact PG error and exits 1. Use as a fail-fast gate before run-query. Omit SQL to use the stored query text."""
    client, _ = _load_client(profile)
    try:
        query_text, entity_id = _resolve_query_text_and_owner(
            client, id, query_text, entity_id
        )
        client.validate_query(query_text, id, entity_id, network)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    out.print("[green]✓[/] valid")


@app.command()
def query_columns(
    id: Annotated[int, typer.Option(help="Query ID for macro context")],
    query_text: Annotated[
        str | None, typer.Argument(help="SQL text (omit to use stored query text)")
    ] = None,
    profile: ProfileOption = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (defaults to your own)")
    ] = None,
    network: Annotated[
        str | None, typer.Option(help="Network name, e.g. ethereum")
    ] = None,
) -> None:
    """Print the query's output columns (name + type) WITHOUT running it. Also validates the SQL (errors like validate-query on bad SQL). Use in alert mode to prove unique-key/alert-template columns exist. Omit SQL to use the stored query text."""
    client, _ = _load_client(profile)
    try:
        query_text, entity_id = _resolve_query_text_and_owner(
            client, id, query_text, entity_id
        )
        columns = client.query_columns(query_text, id, entity_id, network)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_columns(columns)


@app.command()
def format_query(
    query_text: Annotated[
        str | None, typer.Argument(help="SQL text (omit to read from stdin)")
    ] = None,
    profile: ProfileOption = None,
) -> None:
    """Pretty-print SQL. Pass SQL as argument or pipe via stdin. Returns input unchanged if it can't parse."""
    if query_text is None:
        query_text = _read_ready_stdin()
        if not query_text.strip():
            err.print("No query text provided. Pass as argument or pipe via stdin.")
            raise typer.Exit(1)
    client, _ = _load_client(profile)
    try:
        formatted = client.format_query(query_text)
    except Exception as e:
        _exit_error(e)
    output.format_query_text(formatted)


@app.command()
def query_status(
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Query ID")] = None,
    path: Annotated[str | None, typer.Option(help="Query path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (for path lookup)")
    ] = None,
) -> None:
    """Show materialization/backfill status for a query as JSON. Specify with --id <query_id> or --path /Folder/QueryName."""
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        status = client.get_query_status(qid)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    if status is None:
        typer.echo("No status (query not materialized).")
        return
    output.format_query_metadata(status)


@app.command()
def query_history(
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Query ID")] = None,
    path: Annotated[str | None, typer.Option(help="Query path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (for path lookup)")
    ] = None,
    limit: Annotated[int, typer.Option(help="Number of versions")] = 25,
) -> None:
    """List a query's saved version history. Specify with --id <query_id> or --path /Folder/QueryName."""
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        history = client.get_query_history(qid, limit=limit)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_query_history(history)


@app.command()
def materialize(
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Query ID")] = None,
    path: Annotated[str | None, typer.Option(help="Query path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (for path lookup)")
    ] = None,
) -> None:
    """Trigger a materialization run for a query (e.g. to populate a TABLE+ref lookup). Specify with --id <query_id> or --path /Folder/QueryName."""
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        task_id = client.materialize_query(qid)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Materialization started for query {qid} (task {task_id}).")


@app.command()
def active_queries(profile: ProfileOption = None) -> None:
    """List the task ids of currently-running async queries."""
    client, _ = _load_client(profile)
    try:
        tasks = client.get_active_queries()
    except Exception as e:
        _exit_error(e)
    if not tasks:
        typer.echo("No active queries.")
        return
    for t in tasks:
        typer.echo(t)


@app.command()
def download_results(
    task_id: Annotated[
        str, typer.Option(help="Async task id (printed by run-query when it starts)")
    ],
    profile: ProfileOption = None,
    delimiter: Annotated[str, typer.Option(help="CSV delimiter")] = ",",
) -> None:
    """Download a completed async query's results as CSV (to stdout)."""
    client, _ = _load_client(profile)
    try:
        csv_text = client.download_results(task_id, delimiter=delimiter)
    except Exception as e:
        _exit_error(e)
    typer.echo(csv_text)


@app.command()
def move_query(
    to_folder_id: Annotated[int, typer.Option(help="Destination folder ID")],
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Query ID")] = None,
    path: Annotated[str | None, typer.Option(help="Query path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (for path lookup)")
    ] = None,
) -> None:
    """Move a query to another folder. Specify with --id <query_id> or --path /Folder/QueryName."""
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        client.move_query(qid, to_folder_id)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Moved query {qid} to folder {to_folder_id}.")


@app.command()
def star_query(
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Query ID")] = None,
    path: Annotated[str | None, typer.Option(help="Query path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (for path lookup)")
    ] = None,
) -> None:
    """Star (favourite) a query. Specify with --id <query_id> or --path /Folder/QueryName."""
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        client.star_query(qid)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Starred query {qid}.")


@app.command()
def unstar_query(
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Query ID")] = None,
    path: Annotated[str | None, typer.Option(help="Query path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (for path lookup)")
    ] = None,
) -> None:
    """Remove a query's star. Specify with --id <query_id> or --path /Folder/QueryName."""
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        client.unstar_query(qid)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Unstarred query {qid}.")


@app.command()
def share_query(
    team_id: Annotated[int, typer.Option(help="Team ID to share with")],
    perm: Annotated[str, typer.Option(help="Permission to grant, e.g. READ or WRITE")],
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Query ID")] = None,
    path: Annotated[str | None, typer.Option(help="Query path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (for path lookup)")
    ] = None,
) -> None:
    """Share a query with a team. Specify with --id <query_id> or --path /Folder/QueryName."""
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        client.share_query(qid, team_id, perm)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Shared query {qid} with team {team_id} ({perm}).")


@app.command()
def unshare_query(
    team_id: Annotated[int, typer.Option(help="Team ID to unshare from")],
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Query ID")] = None,
    path: Annotated[str | None, typer.Option(help="Query path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (for path lookup)")
    ] = None,
) -> None:
    """Stop sharing a query with a team. Specify with --id <query_id> or --path /Folder/QueryName."""
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        client.unshare_query(qid, team_id)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Unshared query {qid} from team {team_id}.")


@app.command()
def query_by_key(
    key: Annotated[str, typer.Option(help="Shared query key")],
    profile: ProfileOption = None,
) -> None:
    """Fetch a query's metadata by its share key (JSON)."""
    client, _ = _load_client(profile)
    try:
        query = client.get_query_by_key(key)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_query_metadata(query)


@app.command()
def move_folder(
    to_folder_id: Annotated[int, typer.Option(help="Destination parent folder ID")],
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Folder ID")] = None,
    path: Annotated[str | None, typer.Option(help="Folder path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (defaults to your own)")
    ] = None,
) -> None:
    """Move a folder under another parent folder. Specify with --id <folder_id> or --path /Folder."""
    client, _ = _load_client(profile)
    try:
        if entity_id is None:
            entity_id = client.get_me()["entity_id"]
        folder_id = _resolve_folder(client, id, path, entity_id)
        client.move_folder(folder_id, entity_id, to_folder_id)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Moved folder {folder_id} under {to_folder_id}.")


@app.command()
def subfolders(
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Folder ID")] = None,
    path: Annotated[str | None, typer.Option(help="Folder path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (for path lookup)")
    ] = None,
) -> None:
    """List the immediate subfolders of a folder (JSON). Specify with --id <folder_id> or --path /Folder."""
    client, _ = _load_client(profile)
    try:
        folder_id = _resolve_folder(client, id, path, entity_id)
        result = client.get_subfolders(folder_id)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_query_metadata(result)


@app.command()
def entity(
    username: Annotated[str, typer.Argument(help="Entity username to look up")],
    profile: ProfileOption = None,
) -> None:
    """Look up an entity by username (JSON)."""
    client, _ = _load_client(profile)
    try:
        result = client.get_entity(username)
    except Exception as e:
        _exit_error(e)
    if not result:
        typer.echo(f"No entity found for '{username}'.")
        return
    output.format_query_metadata(result)


@app.command()
def generate_query(
    description: Annotated[
        str, typer.Argument(help="Natural-language description of the query/alert")
    ],
    profile: ProfileOption = None,
    network: Annotated[
        list[str] | None,
        typer.Option(
            "--network", help="Target network(s), repeatable. Default ethereum."
        ),
    ] = None,
    hint: Annotated[
        list[str] | None,
        typer.Option("--hint", help="Context hint(s), repeatable."),
    ] = None,
    wait: Annotated[
        bool, typer.Option(help="Poll until the generation job finishes")
    ] = True,
) -> None:
    """Generate DedaubQL from natural language via the platform's own generator. Prints the job result. (The dedaub-monitoring skill generates SQL itself — this is for direct/programmatic use.)"""
    client, _ = _load_client(profile)
    networks = network or ["ethereum"]
    try:
        job = client.generate_query(description, networks, hint)
        job_id = job["job_id"]
        if wait:
            deadline = time.monotonic() + 300.0
            while job.get("status") in ("pending", "running"):
                if time.monotonic() > deadline:
                    err.print(f"Generation timed out; check later: job {job_id}")
                    raise typer.Exit(1)
                time.sleep(2.0)
                job = client.get_generation_job(job_id)
            if job.get("status") == "failed":
                err.print(f"Generation failed: {job.get('error') or 'unknown error'}")
                raise typer.Exit(1)
    except typer.Exit:
        # The timeout / failed branches above already printed their message and
        # asked to exit; let that propagate instead of being re-wrapped by the
        # generic handler below (typer.Exit subclasses Exception).
        raise
    except Exception as e:
        _exit_error(e)
    output.format_query_metadata(job)


@app.command()
def telegram_code(
    id: Annotated[
        int, typer.Option(help="Query ID to link Telegram notifications for")
    ],
    profile: ProfileOption = None,
) -> None:
    """Get the Telegram bot linking code for a query's notifications (JSON)."""
    client, _ = _load_client(profile)
    try:
        result = client.get_telegram_code(id)
    except Exception as e:
        _exit_error(e)
    output.format_query_metadata(result)


# --- dashboards and widgets ---
#
# Flat commands, like the query commands above. The widget rules (config keys,
# axis checks, the SQL a widget reads) live in widgets.py, copied from the web
# app, so the CLI gives the same answers as the Visualize tab.

_LINK_INDENT = "  "


def _read_json_input(source: str, flag: str) -> Any:
    """JSON from a file, or from stdin when `source` is "-"."""
    if source == "-":
        text = _read_ready_stdin()
        if not text.strip():
            err.print(f"No JSON on stdin for {flag}. Pipe it in, or pass a file.")
            raise typer.Exit(1)
    else:
        try:
            text = Path(source).read_text(encoding="utf-8")
        except OSError as e:
            err.print(f"Cannot read {flag} file: {e}")
            raise typer.Exit(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        err.print(f"{flag} is not valid JSON: {e}")
        raise typer.Exit(1)


def _config_input(source: str | None) -> dict:
    """The --config object with snake_case keys, or {}."""
    if source is None:
        return {}
    data = _read_json_input(source, "--config")
    if not isinstance(data, dict):
        err.print("--config must be a JSON object of config keys.")
        raise typer.Exit(1)
    return widgets.normalize_config(data)


def _flag_config(
    x: str | None,
    y: str | None,
    y1: str | None,
    series_by: str | None,
    x_label: str | None,
    y_label: str | None,
    timeframe: str | None,
) -> dict:
    """The config keys that the flags set. An empty value clears the key."""
    pairs = {
        "x_axis_name": x,
        "y_axis_name": y,
        "y1_axis_name": y1,
        "series_by": series_by,
        "x_label": x_label,
        "y_label": y_label,
        "timeframe": timeframe,
    }
    return {k: v for k, v in pairs.items() if v is not None}


_ALERT_CATEGORY = "ALERT"


class _Draft(NamedTuple):
    """A widget to check, preview or save: a saved one with changes, or a new one."""

    stored: dict | None
    query: dict | None
    widget_type: str
    label: str | None
    config: dict


def _widget_draft(
    client: MonitoringClient,
    widget_id: int | None,
    query_id: int | None,
    widget_type: str | None,
    label: str | None,
    config_input: dict,
    flags: dict,
    clear: list[str] | None = None,
) -> _Draft:
    """The widget that the flags describe. With `widget_id`, the saved widget
    is the base and the stored config merges with --config, then the flags; a
    new widget starts from the web app's default config. The flags win."""
    if widget_id is not None:
        stored = client.get_widget(widget_id)
        if stored.get("category") == _ALERT_CATEGORY:
            # The dashboard draws the alerts of its query, not a chart (Widget.tsx).
            err.print(
                "An alerts widget shows the alerts of its query; edit it in the web app."
            )
            raise typer.Exit(1)
        base = widgets.normalize_config(stored.get("config") or {})
        for key in clear or []:
            base.pop(widgets.camel_to_snake(key), None)
        query_ids = stored.get("query_ids") or []
        if query_id is None and query_ids:
            query_id = query_ids[0]
        widget_type = widget_type or str(stored.get("type") or "")
        label = label if label is not None else stored.get("label")
    else:
        stored = None
        base = dict(widgets.DEFAULT_CONFIG)
    config = widgets.clean_config({**base, **config_input, **flags})
    query = client.get_query(query_id) if query_id is not None else None
    return _Draft(stored, query, widget_type or "", label, config)


def _require_new_widget_args(query_id: int | None, widget_type: str | None) -> None:
    if query_id is None or widget_type is None:
        err.print(
            "Provide --id <widget_id>, or --query-id and --type for a new widget."
        )
        raise typer.Exit(2)


def _query_network(query: dict) -> str:
    return query.get("default_network") or "ethereum"


def _widget_columns(client: MonitoringClient, query: dict) -> list[dict]:
    """The query's columns as {"name", "type"}, as getQueryColumns reads them."""
    text = query.get("query_text")
    if not text:
        return []
    columns = client.query_columns(
        text, query["query_id"], query["owner"]["entity_id"], _query_network(query)
    )
    return [
        {"name": c.get("column_name", ""), "type": c.get("column_type", "")}
        for c in columns
    ]


def _widget_problems(
    client: MonitoringClient, draft: _Draft, check_columns: bool = True
) -> tuple[list[str], list[str]]:
    """The problems (each one blocks a save) and the notes of a draft."""
    problems = widgets.config_problems(draft.widget_type, draft.config)
    notes = widgets.config_notes(draft.widget_type, draft.config)
    axis = widgets.missing_axis(draft.widget_type, draft.config)
    if axis:
        problems.append(axis)
    if not check_columns:
        return problems, notes
    if draft.query is None:
        notes.append("The widget reads no query, so the column check was skipped.")
        return problems, notes
    try:
        columns = _widget_columns(client, draft.query)
    except (httpx.HTTPStatusError, PermissionError) as e:
        problems.append(f"Cannot read the query columns: {e}")
        return problems, notes
    if not columns:
        notes.append(
            "The query metadata has no columns, so the column check was skipped."
        )
    names = [c["name"] for c in columns]
    for name in widgets.columns_not_in_query(draft.config, names, draft.widget_type):
        problems.append(f"The query has no column {name!r}.")
    return problems, notes


def _print_problems(problems: list[str], notes: list[str]) -> None:
    for note in notes:
        err.print(f"[yellow]Note:[/] {escape(note)}")
    for problem in problems:
        err.print(f"[red]✗[/] {escape(problem)}")


def _widget_category(client: MonitoringClient, query: dict) -> str:
    """The Visualize tab's category: a scheduled query or one with
    notifications reads its materialized table; any other one, a view."""
    notify = False
    if not query.get("is_scheduled"):
        # The web app reads a missing notification config as "no notifications".
        with contextlib.suppress(NotFoundError, httpx.HTTPStatusError, PermissionError):
            config = client.get_notify_config(query["query_id"], _query_network(query))
            notify = bool((config or {}).get("notify"))
    return widgets.chart_category(query, notify)


def _echo_links(base_url: str, widget: dict | None, dashboard_ids: list[int]) -> None:
    if widget is not None and widget.get("widget_id") is not None:
        typer.echo(_LINK_INDENT + widgets.widget_link(base_url, widget["widget_id"]))
    for dashboard_id in dashboard_ids:
        typer.echo(
            f"{_LINK_INDENT}dashboard {dashboard_id}: "
            + widgets.dashboard_link(base_url, dashboard_id)
        )


# Option types that create-widget, update-widget, check-widget and
# preview-widget share.
_WidgetQueryOpt = Annotated[
    int | None, typer.Option("--query-id", help="ID of the query that the widget draws")
]
_WidgetTypeOpt = Annotated[
    str | None,
    typer.Option(
        "--type",
        help="Widget type: line, bar, stackedbar, linebar, scatter, histogram, range, pie, table, value",
    ),
]
_WidgetLabelOpt = Annotated[
    str | None,
    typer.Option(
        "--label",
        help="Widget title (inline Markdown and TeX). Default: the query name",
    ),
]
_XOpt = Annotated[str | None, typer.Option("--x", help="X-axis column (x_axis_name)")]
_YOpt = Annotated[str | None, typer.Option("--y", help="Y-axis column (y_axis_name)")]
_Y1Opt = Annotated[
    str | None, typer.Option("--y1", help="Second Y column (y1_axis_name)")
]
_SeriesByOpt = Annotated[
    str | None,
    typer.Option(
        "--series-by", help="One series for each value of this column (series_by)"
    ),
]
_XLabelOpt = Annotated[
    str | None,
    typer.Option(
        "--x-label",
        help="X-axis label: inline Markdown and TeX, max 120 characters (x_label)",
    ),
]
_YLabelOpt = Annotated[
    str | None,
    typer.Option(
        "--y-label",
        help="Y-axis label: inline Markdown and TeX, max 120 characters (y_label)",
    ),
]
_TimeframeOpt = Annotated[
    str | None,
    typer.Option(
        "--timeframe", help="Time range the widget reads: 24h, 7d, 30d or 60d"
    ),
]
_ConfigOpt = Annotated[
    str | None,
    typer.Option(
        "--config",
        help="JSON object of config keys from a file, or - for stdin. camelCase or snake_case keys. The flags win.",
    ),
]
_ClearOpt = Annotated[
    list[str] | None,
    typer.Option("--clear", help="Remove this key from the saved config. Repeatable."),
]


@app.command()
def list_dashboards(profile: ProfileOption = None) -> None:
    """List the dashboards you can open. The default dashboard is marked."""
    client, _ = _load_client(profile)
    try:
        dashboards = client.list_dashboards()
    except Exception as e:
        _exit_error(e)
    default_id = None
    with contextlib.suppress(Exception):
        default_id = client.get_default_dashboard()
    output.format_dashboards(dashboards, default_id)


@app.command()
def get_dashboard(
    id: Annotated[int, typer.Option(help="Dashboard ID")],
    profile: ProfileOption = None,
) -> None:
    """Show a dashboard and its widgets (JSON)."""
    client, _ = _load_client(profile)
    try:
        dashboard = client.get_dashboard(id)
        dashboard["widgets"] = client.list_widgets(dashboard_id=id)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_query_metadata(dashboard)


@app.command()
def create_dashboard(
    name: Annotated[str, typer.Argument(help="Dashboard name")],
    profile: ProfileOption = None,
    description: Annotated[str | None, typer.Option(help="Description")] = None,
    public: Annotated[
        bool, typer.Option("--public", help="Anyone with the link can open it")
    ] = False,
    unlisted: Annotated[
        bool,
        typer.Option(
            "--unlisted", help="Public, but not in the public list (needs --public)"
        ),
    ] = False,
    entity_id: Annotated[
        int | None,
        typer.Option(
            help="Owner entity ID: you (default) or one of your organisations"
        ),
    ] = None,
) -> None:
    """Create a dashboard. Prints its ID and link."""
    if unlisted and not public:
        err.print("--unlisted needs --public: only a public dashboard can be unlisted.")
        raise typer.Exit(2)
    client, p = _load_client(profile)
    try:
        if entity_id is None:
            entity_id = client.get_me()["entity_id"]
        created = client.create_dashboard(
            name, entity_id, description, is_public=public, is_unlisted=unlisted
        )
    except Exception as e:
        _exit_error(e)
    dashboard_id = created.get("dashboard_id")
    typer.echo(f"Created dashboard (id: {dashboard_id}).")
    if dashboard_id is not None:
        _echo_links(p.base_url, None, [dashboard_id])


@app.command()
def update_dashboard(
    id: Annotated[int, typer.Option(help="Dashboard ID")],
    profile: ProfileOption = None,
    name: Annotated[str | None, typer.Option(help="New name")] = None,
    description: Annotated[
        str | None, typer.Option(help="New description (empty to remove)")
    ] = None,
    public: Annotated[
        bool | None,
        typer.Option("--public/--private", help="Make the dashboard public or private"),
    ] = None,
    unlisted: Annotated[
        bool | None,
        typer.Option(
            "--unlisted/--listed",
            help="Hide a public dashboard from the public list, or show it",
        ),
    ] = None,
) -> None:
    """Change a dashboard's name, description or visibility. The other fields stay."""
    if name is None and description is None and public is None and unlisted is None:
        err.print(
            "Nothing to change. Pass --name, --description, --public/--private or --unlisted/--listed."
        )
        raise typer.Exit(2)
    client, p = _load_client(profile)
    try:
        stored = client.get_dashboard(id)
        is_public = stored.get("is_public", False) if public is None else public
        is_unlisted = stored.get("is_unlisted", False) if unlisted is None else unlisted
        if is_unlisted and not is_public:
            if unlisted:
                err.print("--unlisted needs a public dashboard: add --public.")
                raise typer.Exit(2)
            # A private dashboard cannot stay unlisted.
            is_unlisted = False
        client.update_dashboard(
            id,
            {
                "name": stored.get("name") if name is None else name,
                "description": (
                    stored.get("description")
                    if description is None
                    else description or None
                ),
                "is_public": is_public,
                "is_unlisted": is_unlisted,
                "entity_id": stored.get("entity_id"),
            },
        )
    except typer.Exit:
        raise
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Updated dashboard {id}.")
    _echo_links(p.base_url, None, [id])


@app.command()
def delete_dashboard(
    id: Annotated[int, typer.Option(help="Dashboard ID")],
    profile: ProfileOption = None,
    delete_widgets: Annotated[
        bool,
        typer.Option(
            "--delete-widgets",
            help="Also delete the widgets that only this dashboard has. Default: they stay saved.",
        ),
    ] = False,
) -> None:
    """Delete a dashboard. Its widgets stay saved unless --delete-widgets."""
    client, _ = _load_client(profile)
    try:
        result = client.delete_dashboard(id, delete_widgets=delete_widgets)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    if delete_widgets:
        count = result.get("deleted_widgets", 0)
        typer.echo(f"Deleted dashboard {id} and {count} widget(s).")
    else:
        typer.echo(f"Deleted dashboard {id}. Its widgets stay saved.")


@app.command()
def set_default_dashboard(
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Dashboard ID")] = None,
    clear: Annotated[
        bool, typer.Option("--clear", help="Remove the default dashboard")
    ] = False,
) -> None:
    """Set the dashboard that /dashboard opens for you, or clear it with --clear."""
    if (id is None) == (not clear):
        err.print("Provide either --id or --clear.")
        raise typer.Exit(2)
    client, p = _load_client(profile)
    try:
        client.set_default_dashboard(None if clear else id)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    if id is None:
        typer.echo("Cleared the default dashboard.")
    else:
        typer.echo(f"Default dashboard is now {id}.")
        _echo_links(p.base_url, None, [id])


@app.command()
def set_layout(
    id: Annotated[int, typer.Option(help="Dashboard ID")],
    layout: Annotated[
        str,
        typer.Option(
            help='JSON list of {"widget_id", "x", "y", "width", "height"} from a file, or - for stdin'
        ),
    ],
    profile: ProfileOption = None,
) -> None:
    """Set the place and size of widgets on a dashboard (12-column grid). All or nothing."""
    data = _read_json_input(layout, "--layout")
    problems = widgets.layout_problems(data)
    if problems:
        _print_problems(problems, [])
        raise typer.Exit(1)
    assert isinstance(data, list)
    client, p = _load_client(profile)
    try:
        client.set_dashboard_layout(id, data)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Saved the layout of {len(data)} widget(s) on dashboard {id}.")
    _echo_links(p.base_url, None, [id])


@app.command()
def list_widgets(
    profile: ProfileOption = None,
    query_id: Annotated[
        int | None, typer.Option(help="Only the widgets of this query")
    ] = None,
    dashboard_id: Annotated[
        int | None, typer.Option(help="Only the widgets on this dashboard")
    ] = None,
) -> None:
    """List your widgets. Filter with --query-id or --dashboard-id."""
    client, _ = _load_client(profile)
    try:
        result = client.list_widgets(query_id=query_id, dashboard_id=dashboard_id)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_widgets(result)


@app.command()
def get_widget(
    id: Annotated[int, typer.Option(help="Widget ID")],
    profile: ProfileOption = None,
) -> None:
    """Show a widget by ID (JSON)."""
    client, _ = _load_client(profile)
    try:
        result = client.get_widget(id)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_query_metadata(result)


@app.command()
def check_widget(
    profile: ProfileOption = None,
    id: Annotated[
        int | None, typer.Option(help="Saved widget ID (the flags change it)")
    ] = None,
    query_id: _WidgetQueryOpt = None,
    widget_type: _WidgetTypeOpt = None,
    label: _WidgetLabelOpt = None,
    x: _XOpt = None,
    y: _YOpt = None,
    y1: _Y1Opt = None,
    series_by: _SeriesByOpt = None,
    x_label: _XLabelOpt = None,
    y_label: _YLabelOpt = None,
    timeframe: _TimeframeOpt = None,
    config: _ConfigOpt = None,
    clear: _ClearOpt = None,
) -> None:
    """Check a widget like the web Visualize tab: config keys and values, the axes the type needs, and the columns of the query. Prints each problem and exits 1 when there is one. Takes --id, or --query-id and --type."""
    if id is None:
        _require_new_widget_args(query_id, widget_type)
    config_input = _config_input(config)
    flags = _flag_config(x, y, y1, series_by, x_label, y_label, timeframe)
    client, _ = _load_client(profile)
    try:
        draft = _widget_draft(
            client, id, query_id, widget_type, label, config_input, flags, clear
        )
        problems, notes = _widget_problems(client, draft)
    except typer.Exit:
        raise
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    _print_problems(problems, notes)
    if problems:
        raise typer.Exit(1)
    out.print("[green]✓[/] valid")
    output.format_query_metadata(
        {
            "type": draft.widget_type,
            "label": draft.label,
            "query_id": draft.query.get("query_id") if draft.query else None,
            "config": draft.config,
        }
    )


@app.command()
def preview_widget(
    profile: ProfileOption = None,
    id: Annotated[
        int | None, typer.Option(help="Saved widget ID (the flags change it)")
    ] = None,
    query_id: _WidgetQueryOpt = None,
    widget_type: _WidgetTypeOpt = None,
    label: _WidgetLabelOpt = None,
    x: _XOpt = None,
    y: _YOpt = None,
    y1: _Y1Opt = None,
    series_by: _SeriesByOpt = None,
    x_label: _XLabelOpt = None,
    y_label: _YLabelOpt = None,
    timeframe: _TimeframeOpt = None,
    config: _ConfigOpt = None,
    clear: _ClearOpt = None,
    limit: Annotated[
        int | None,
        typer.Option(
            help=f"Max rows (max 500). Default: {widgets.CHART_ROWS} for a chart, {widgets.TABLE_ROWS} for a table"
        ),
    ] = None,
    timeout: Annotated[
        float,
        typer.Option(help="Max seconds to wait; then the server task is revoked"),
    ] = 120.0,
    sql: Annotated[
        bool,
        typer.Option("--sql", help="Print the SQL the widget runs, and do not run it"),
    ] = False,
) -> None:
    """Run the SQL that the dashboard runs for a widget and print its rows: the query's table through ref(), or the query text when ref() cannot find the query. Takes --id, or --query-id and --type. Ctrl-C (or --timeout) revokes the server task."""
    if id is None:
        _require_new_widget_args(query_id, widget_type)
    config_input = _config_input(config)
    flags = _flag_config(x, y, y1, series_by, x_label, y_label, timeframe)
    client, _ = _load_client(profile)
    try:
        draft = _widget_draft(
            client, id, query_id, widget_type, label, config_input, flags, clear
        )
        problems, notes = _widget_problems(client, draft, check_columns=False)
        if draft.query is None:
            problems.append("The widget reads no query, so it has no rows to preview.")
        if problems:
            _print_problems(problems, notes)
            raise typer.Exit(1)
        assert draft.query is not None
        query = draft.query
        try:
            columns = _widget_columns(client, query)
        except (httpx.HTTPStatusError, PermissionError) as e:
            # The dashboard reads the rows without the columns too.
            err.print(
                f"[yellow]Note:[/] cannot read the query columns: {escape(str(e))}"
            )
            columns = []
        ref_sql, text_sql = widgets.widget_sqls_of(
            query=query,
            columns=columns,
            widget_type=draft.widget_type,
            config=draft.config,
            timeframe=draft.config.get("timeframe"),
        )
        if sql:
            typer.echo(ref_sql)
            if text_sql is not None:
                typer.echo("\n-- When ref() cannot find the query, the rows come from:")
                typer.echo(text_sql)
            return
        rows_limit = limit or (
            widgets.TABLE_ROWS if draft.widget_type == "table" else widgets.CHART_ROWS
        )

        def run(statement: str) -> list[dict]:
            return client.execute_query(
                statement,
                query["query_id"],
                query["owner"]["entity_id"],
                limit=rows_limit,
                poll_timeout=timeout,
                on_start=lambda tid: err.print(f"task {tid} (Ctrl-C to cancel)"),
            )

        try:
            rows = run(ref_sql)
        except (RuntimeError, httpx.HTTPStatusError) as e:
            if text_sql is None or not widgets.NOT_REFERABLE.search(str(e)):
                raise
            err.print(
                "ref() cannot find the query (it has no run settings): reading the query text."
            )
            try:
                rows = run(text_sql)
            except (RuntimeError, httpx.HTTPStatusError) as text_error:
                raise RuntimeError(
                    f"Read from the query text (the query has no run settings): {text_error}"
                ) from text_error
    except typer.Exit:
        raise
    except KeyboardInterrupt:
        err.print("Cancelled — server task revoked.")
        raise typer.Exit(130)
    except TimeoutError as e:
        err.print(f"{e} — task revoked. Shorten --timeframe, or raise --timeout.")
        raise typer.Exit(1)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_query_results(rows)
    _print_problems([], widgets.series_notes(draft.widget_type, draft.config, rows))


@app.command()
def create_widget(
    query_id: Annotated[
        int, typer.Option("--query-id", help="ID of the query that the widget draws")
    ],
    widget_type: Annotated[
        str,
        typer.Option(
            "--type",
            help="Widget type: line, bar, stackedbar, linebar, scatter, histogram, range, pie, table, value",
        ),
    ],
    profile: ProfileOption = None,
    label: _WidgetLabelOpt = None,
    x: _XOpt = None,
    y: _YOpt = None,
    y1: _Y1Opt = None,
    series_by: _SeriesByOpt = None,
    x_label: _XLabelOpt = None,
    y_label: _YLabelOpt = None,
    timeframe: _TimeframeOpt = None,
    config: _ConfigOpt = None,
    dashboard_id: Annotated[
        list[int] | None,
        typer.Option(
            "--dashboard-id",
            help="Also put the widget on this dashboard, under its lowest widget. Repeatable.",
        ),
    ] = None,
    entity_id: Annotated[
        int | None,
        typer.Option(
            help="Owner entity ID: you (default) or an organisation you manage"
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force", help="Skip the column checks (the other checks still run)"
        ),
    ] = False,
) -> None:
    """Save a chart, table or value widget of a query, with the checks of check-widget first. Prints the widget ID and link."""
    config_input = _config_input(config)
    flags = _flag_config(x, y, y1, series_by, x_label, y_label, timeframe)
    client, p = _load_client(profile)
    try:
        draft = _widget_draft(
            client, None, query_id, widget_type, label, config_input, flags
        )
        problems, notes = _widget_problems(client, draft, check_columns=not force)
        _print_problems(problems, notes)
        if problems:
            raise typer.Exit(1)
        query = draft.query
        assert query is not None
        body: dict = {
            "label": draft.label or query.get("query_name"),
            "category": _widget_category(client, query),
            "type": draft.widget_type,
            "query_ids": [query["query_id"]],
            "query_keys": [query["key"]] if query.get("key") else [],
            "config": draft.config,
            "dashboard_ids": list(dict.fromkeys(dashboard_id or [])),
            "x": 0,
            "y": 0,
            **widgets.default_widget_size(draft.widget_type),
        }
        if entity_id is not None:
            body["entity_id"] = entity_id
        created = client.create_widget(body)
    except typer.Exit:
        raise
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Created widget (id: {created.get('widget_id')}).")
    _echo_links(p.base_url, created, created.get("dashboard_ids") or [])


@app.command()
def update_widget(
    id: Annotated[int, typer.Option(help="Widget ID")],
    profile: ProfileOption = None,
    query_id: _WidgetQueryOpt = None,
    widget_type: _WidgetTypeOpt = None,
    label: _WidgetLabelOpt = None,
    x: _XOpt = None,
    y: _YOpt = None,
    y1: _Y1Opt = None,
    series_by: _SeriesByOpt = None,
    x_label: _XLabelOpt = None,
    y_label: _YLabelOpt = None,
    timeframe: _TimeframeOpt = None,
    config: _ConfigOpt = None,
    clear: _ClearOpt = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force", help="Skip the column checks (the other checks still run)"
        ),
    ] = False,
) -> None:
    """Change a widget on every dashboard that has it. The flags and --config merge into the saved config; --clear removes a key. Runs the checks of check-widget first. Its places stay."""
    config_input = _config_input(config)
    flags = _flag_config(x, y, y1, series_by, x_label, y_label, timeframe)
    client, p = _load_client(profile)
    try:
        draft = _widget_draft(
            client, id, query_id, widget_type, label, config_input, flags, clear
        )
        problems, notes = _widget_problems(client, draft, check_columns=not force)
        _print_problems(problems, notes)
        if problems:
            raise typer.Exit(1)
        stored = draft.stored
        assert stored is not None
        query_ids = stored.get("query_ids") or []
        query_keys = stored.get("query_keys") or []
        category = stored.get("category")
        query = draft.query
        if query_id is not None and query is not None and query_ids != [query_id]:
            # A new query: its key and its category, as a new widget gets them.
            query_ids = [query_id]
            query_keys = [query["key"]] if query.get("key") else []
            category = _widget_category(client, query)
        updated = client.update_widget(
            id,
            {
                # No dashboard: the backend then changes no place. With one, it
                # writes width/height to that place, and the stored legacy
                # columns can be older than the place.
                "dashboard_id": None,
                "label": draft.label,
                "category": category,
                "type": draft.widget_type,
                "query_ids": query_ids,
                "query_keys": query_keys,
                "config": draft.config,
                # The body must be inside the grid, but with no dashboard_id
                # the backend does not use these values.
                "x": 0,
                "y": 0,
                "width": 6,
                "height": 4,
            },
        )
    except typer.Exit:
        raise
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Updated widget {id}.")
    _echo_links(p.base_url, updated or {"widget_id": id}, [])


@app.command()
def delete_widget(
    id: Annotated[int, typer.Option(help="Widget ID")],
    profile: ProfileOption = None,
) -> None:
    """Delete a widget. It leaves every dashboard that has it."""
    client, _ = _load_client(profile)
    try:
        client.delete_widget(id)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Deleted widget {id} from every dashboard.")


@app.command()
def add_widget(
    id: Annotated[int, typer.Option(help="Widget ID")],
    dashboard_id: Annotated[
        list[int],
        typer.Option(
            "--dashboard-id",
            help="Dashboard to put the widget on, under its lowest widget. Repeatable.",
        ),
    ],
    profile: ProfileOption = None,
) -> None:
    """Put a saved widget on one or more dashboards. A dashboard that has it already keeps its place."""
    client, p = _load_client(profile)
    targets = list(dict.fromkeys(dashboard_id))
    try:
        client.add_widget_to_dashboards(id, targets)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Widget {id} is on dashboard(s) {', '.join(map(str, targets))}.")
    _echo_links(p.base_url, None, targets)


@app.command()
def remove_widget(
    id: Annotated[int, typer.Option(help="Widget ID")],
    dashboard_id: Annotated[int, typer.Option(help="Dashboard to take it off")],
    profile: ProfileOption = None,
) -> None:
    """Take a widget off one dashboard. It stays saved, and on its other dashboards."""
    client, _ = _load_client(profile)
    try:
        client.remove_dashboard_widget(dashboard_id, id)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Removed widget {id} from dashboard {dashboard_id}.")


# --- webhook sub-app ---

webhook_app = typer.Typer(help="Manage notification webhooks.")
app.add_typer(webhook_app, name="webhook")


@webhook_app.command("create")
def webhook_create(
    name: Annotated[str, typer.Option(help="Webhook name")],
    url: Annotated[str, typer.Option(help="Webhook URL")],
    profile: ProfileOption = None,
    description: Annotated[str | None, typer.Option(help="Description")] = None,
    secret: Annotated[str | None, typer.Option(help="Signing secret")] = None,
) -> None:
    """Create a webhook. Prints the new webhook ID."""
    client, _ = _load_client(profile)
    try:
        result = client.create_webhook(name, url, description, secret)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Created webhook (id: {result.get('webhook_id')}).")


@webhook_app.command("test")
def webhook_test(
    url: Annotated[str, typer.Option(help="Webhook URL to test")],
    profile: ProfileOption = None,
    secret: Annotated[str | None, typer.Option(help="Signing secret")] = None,
) -> None:
    """Send a test payload to a webhook URL and print the result."""
    client, _ = _load_client(profile)
    try:
        result = client.test_webhook(url, secret)
    except Exception as e:
        _exit_error(e)
    status = result.get("status", "")
    message = result.get("message") or ""
    typer.echo(f"{status}: {message}" if message else str(status))


@webhook_app.command("list")
def webhook_list(profile: ProfileOption = None) -> None:
    """List your webhooks."""
    client, _ = _load_client(profile)
    try:
        result = client.list_webhooks()
    except Exception as e:
        _exit_error(e)
    output.format_webhooks(result)


@webhook_app.command("get")
def webhook_get(
    id: Annotated[int, typer.Option(help="Webhook ID")],
    profile: ProfileOption = None,
) -> None:
    """Show a webhook by ID (JSON)."""
    client, _ = _load_client(profile)
    try:
        result = client.get_webhook(id)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_query_metadata(result)


@webhook_app.command("update")
def webhook_update(
    id: Annotated[int, typer.Option(help="Webhook ID")],
    name: Annotated[str, typer.Option(help="Webhook name")],
    url: Annotated[str, typer.Option(help="Webhook URL")],
    profile: ProfileOption = None,
    description: Annotated[str | None, typer.Option(help="Description")] = None,
    secret: Annotated[str | None, typer.Option(help="Signing secret")] = None,
) -> None:
    """Update a webhook (name + url required)."""
    client, _ = _load_client(profile)
    try:
        client.update_webhook(id, name, url, description, secret)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Updated webhook {id}.")


@webhook_app.command("delete")
def webhook_delete(
    id: Annotated[int, typer.Option(help="Webhook ID")],
    profile: ProfileOption = None,
) -> None:
    """Delete a webhook."""
    client, _ = _load_client(profile)
    try:
        client.delete_webhook(id)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Deleted webhook {id}.")


# --- alert-filter sub-app ---

alert_filter_app = typer.Typer(help="Manage saved alert filters (alert searches).")
app.add_typer(alert_filter_app, name="alert-filter")


def _split_ints(csv: str | None) -> list[int] | None:
    if not csv:
        return None
    return [int(x.strip()) for x in csv.split(",") if x.strip()]


@alert_filter_app.command("create")
def alert_filter_create(
    name: Annotated[str, typer.Option(help="Filter name")],
    profile: ProfileOption = None,
    query_ids: Annotated[
        str | None, typer.Option(help="Comma-separated query IDs")
    ] = None,
    chain_ids: Annotated[
        str | None, typer.Option(help="Comma-separated chain IDs")
    ] = None,
    colour: Annotated[str | None, typer.Option(help="Display colour")] = None,
) -> None:
    """Create a saved alert filter. Prints the new filter ID."""
    client, _ = _load_client(profile)
    try:
        result = client.create_alert_filter(
            name, _split_ints(query_ids), _split_ints(chain_ids), colour
        )
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Created alert filter (id: {result}).")


@alert_filter_app.command("list")
def alert_filter_list(profile: ProfileOption = None) -> None:
    """List your saved alert filters."""
    client, _ = _load_client(profile)
    try:
        result = client.list_alert_filters()
    except Exception as e:
        _exit_error(e)
    output.format_alert_filters(result)


@alert_filter_app.command("get")
def alert_filter_get(
    id: Annotated[int, typer.Option(help="Alert filter ID")],
    profile: ProfileOption = None,
) -> None:
    """Show a saved alert filter by ID (JSON)."""
    client, _ = _load_client(profile)
    try:
        result = client.get_alert_filter(id)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_query_metadata(result)


@alert_filter_app.command("update")
def alert_filter_update(
    id: Annotated[int, typer.Option(help="Alert filter ID")],
    name: Annotated[str, typer.Option(help="Filter name")],
    profile: ProfileOption = None,
    query_ids: Annotated[
        str | None, typer.Option(help="Comma-separated query IDs")
    ] = None,
    chain_ids: Annotated[
        str | None, typer.Option(help="Comma-separated chain IDs")
    ] = None,
    colour: Annotated[str | None, typer.Option(help="Display colour")] = None,
) -> None:
    """Update a saved alert filter."""
    client, _ = _load_client(profile)
    try:
        client.update_alert_filter(
            id, name, _split_ints(query_ids), _split_ints(chain_ids), colour
        )
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Updated alert filter {id}.")


@alert_filter_app.command("delete")
def alert_filter_delete(
    id: Annotated[int, typer.Option(help="Alert filter ID")],
    profile: ProfileOption = None,
) -> None:
    """Delete a saved alert filter."""
    client, _ = _load_client(profile)
    try:
        client.delete_alert_filter(id)
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Deleted alert filter {id}.")


_SKILL_NAME = "dedaub-monitoring"


class _AgentTarget(NamedTuple):
    """A place the skill can be installed. Every supported agent reads skills
    from ``<home>/<home_subdir>/skills/<name>/`` and the SKILL.md + references/
    payload is the same shared "Agent Skills" format, so one copy works for all.
    """

    key: str  # --agent value
    label: str  # display name in the picker
    home_subdir: str  # dir under $HOME, e.g. ".claude"


# claude is always a valid target; the rest are offered when detected (their
# home dir already exists) or chosen explicitly via --agent/--all/the picker.
_SKILL_AGENTS: tuple[_AgentTarget, ...] = (
    _AgentTarget("claude", "Claude Code", ".claude"),
    _AgentTarget("codex", "Codex", ".codex"),
    _AgentTarget("cursor", "Cursor", ".cursor"),
    _AgentTarget("agents", "Universal (.agents)", ".agents"),
)


def _agent_present(target: _AgentTarget) -> bool:
    """True when this agent's home dir exists, i.e. the agent is installed."""
    return (Path.home() / target.home_subdir).is_dir()


def _dedup_targets(items: list[_AgentTarget]) -> list[_AgentTarget]:
    seen: set[str] = set()
    deduped: list[_AgentTarget] = []
    for t in items:
        if t.key not in seen:
            seen.add(t.key)
            deduped.append(t)
    return deduped


def _prompt_skill_targets(detected: list[_AgentTarget]) -> list[_AgentTarget]:
    """Interactive multi-select picker (TTY only).

    Nothing starts selected. Enter toggles the highlighted agent; move down to
    the "Submit" row and press Enter there to install only the agents you
    checked. Detected agents (home dir already present) are flagged "· detected".
    """
    # Imported lazily: prompt_toolkit is heavy and only the interactive path
    # needs it — keeps the non-interactive paths (CI, bump-version, --agent,
    # --all) fast to start.
    from prompt_toolkit.application import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.containers import Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.styles import Style

    agents = list(_SKILL_AGENTS)
    submit_row = len(agents)  # synthetic row after the agents
    detected_keys = {t.key for t in detected}
    label_w = max(len(t.label) for t in agents) + 2
    selected: set[str] = set()
    cursor = 0

    def render() -> list[tuple[str, str]]:
        tokens: list[tuple[str, str]] = [
            ("class:qmark", "◆ "),
            ("class:question", "Install the dedaub-monitoring skill to:\n"),
            (
                "class:instruction",
                "  ↑↓ move · enter toggles · Submit + enter to finish\n\n",
            ),
        ]
        for i, t in enumerate(agents):
            tokens.append(("class:pointer", "❯ ") if i == cursor else ("", "  "))
            tokens.append(
                ("class:on", "◉ ") if t.key in selected else ("class:off", "◯ ")
            )
            tokens.append(("class:label", t.label.ljust(label_w)))
            tokens.append(("class:path", f"~/{t.home_subdir}/skills/{_SKILL_NAME}"))
            if t.key in detected_keys:
                tokens.append(("class:detected", "  · detected"))
            tokens.append(("", "\n"))
        tokens.append(("class:pointer", "❯ ") if cursor == submit_row else ("", "  "))
        submit_cls = "class:submit" if cursor == submit_row else "class:submit-dim"
        tokens.append((submit_cls, f"Submit ({len(selected)} selected)"))
        return tokens

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("k")
    def _up(_event: KeyPressEvent) -> None:
        nonlocal cursor
        cursor = (cursor - 1) % (submit_row + 1)

    @kb.add("down")
    @kb.add("j")
    def _down(_event: KeyPressEvent) -> None:
        nonlocal cursor
        cursor = (cursor + 1) % (submit_row + 1)

    def _toggle() -> None:
        key = agents[cursor].key
        if key in selected:
            selected.remove(key)
        else:
            selected.add(key)

    @kb.add("space")
    def _space(_event: KeyPressEvent) -> None:
        if cursor != submit_row:
            _toggle()

    @kb.add("enter")
    def _enter(event: KeyPressEvent) -> None:
        if cursor == submit_row:
            event.app.exit(result=[t for t in agents if t.key in selected])
        else:
            _toggle()

    @kb.add("c-c")
    @kb.add("c-q")
    def _abort(event: KeyPressEvent) -> None:
        event.app.exit(result=[])

    style = Style(
        [
            ("qmark", "fg:#5f87ff bold"),
            ("question", "bold"),
            ("instruction", "fg:#808080 italic"),
            ("pointer", "fg:#5f87ff bold"),
            ("on", "fg:#5fafff"),
            ("off", "fg:#808080"),
            ("path", "fg:#808080"),
            ("detected", "fg:#5faf5f"),
            ("submit", "fg:#5f87ff bold"),
            ("submit-dim", "fg:#808080"),
        ]
    )
    app: Application[list[_AgentTarget]] = Application(
        layout=Layout(
            Window(
                FormattedTextControl(render, focusable=True), always_hide_cursor=True
            )
        ),
        key_bindings=kb,
        style=style,
        erase_when_done=True,
    )
    return app.run() or []


def _resolve_skill_targets(
    agent: list[str] | None, all_agents: bool
) -> list[_AgentTarget]:
    by_key = {t.key: t for t in _SKILL_AGENTS}
    if all_agents:
        return list(_SKILL_AGENTS)
    if agent:
        chosen: list[_AgentTarget] = []
        for a in agent:
            t = by_key.get(a.lower())
            if t is None:
                err.print(f"Unknown agent '{a}'. Choices: {', '.join(by_key)}")
                raise typer.Exit(1)
            chosen.append(t)
        return _dedup_targets(chosen)
    detected = [t for t in _SKILL_AGENTS if _agent_present(t)]
    # Interactive: let the user pick. Otherwise (CI, bump-version, no TTY) fall
    # back to a deterministic default so automation never blocks on a prompt.
    if sys.stdin.isatty() and sys.stdout.isatty():
        return _prompt_skill_targets(detected)
    # Non-interactive default: claude always, plus any other detected agent.
    return _dedup_targets([by_key["claude"], *detected])


def _copy_skill_to(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    # Canonical agent-skill layout: <container>/skills/<skill-name>/SKILL.md.
    # The name-level directory is what the marketplace/plugin manifests point at
    # (.claude-plugin/*.json), so keep this path and those declarations in sync.
    src = files("dedaub_skills") / "skills" / _SKILL_NAME
    # Install SKILL.md *and* the whole references/ tree: the skill reads those paths
    # (references/database/…, references/protocols/…) at runtime, so shipping SKILL.md
    # alone would leave every reference lookup broken.
    dest.joinpath("SKILL.md").write_text(
        src.joinpath("SKILL.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    refs_dest = dest / "references"
    with as_file(src.joinpath("references")) as refs:
        # Mirror the packaged tree exactly: clear the managed references/
        # subtree first so docs dropped/renamed between versions don't linger
        # as stale orphans. SKILL.md and anything else under dest is untouched.
        if refs_dest.exists():
            shutil.rmtree(refs_dest)
        shutil.copytree(refs, refs_dest)


@app.command()
def install_skill(
    agent: Annotated[
        list[str] | None,
        typer.Option(
            "--agent",
            "-a",
            help="Agent(s) to install to: claude, codex, cursor, agents. "
            "Repeatable. Skips the interactive picker.",
        ),
    ] = None,
    all_agents: Annotated[
        bool,
        typer.Option("--all", help="Install to every supported agent target."),
    ] = False,
) -> None:
    """Install the dedaub-monitoring skill (SKILL.md + references/) to one or more agents.

    With no flags: in a TTY you get a checkbox picker; otherwise it installs to
    Claude plus any other supported agent already present on this machine. Use
    --agent to choose explicitly or --all for every target.
    """
    targets = _resolve_skill_targets(agent, all_agents)
    if not targets:
        err.print("[yellow]Nothing selected — no agents to install to.[/]")
        raise typer.Exit(1)
    installed: list[tuple[_AgentTarget, Path]] = []
    for t in targets:
        dest = Path.home() / t.home_subdir / "skills" / _SKILL_NAME
        try:
            _copy_skill_to(dest)
        except OSError as e:
            _exit_error(e)
        installed.append((t, dest))

    label_w = max(len(t.label) for t, _ in installed)
    out.print(
        f"\n[green]✓[/] [bold]{_SKILL_NAME}[/] installed to "
        f"{len(installed)} agent{'s' if len(installed) != 1 else ''} "
        "[dim](SKILL.md + references/)[/]"
    )
    for t, dest in installed:
        rel = f"~/{dest.relative_to(Path.home())}"
        out.print(f"  [green]•[/] {t.label.ljust(label_w)}  [dim]{rel}[/]")
