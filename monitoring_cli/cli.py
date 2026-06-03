from __future__ import annotations

import datetime
import select
import shutil
import sys
import time
from importlib.resources import as_file, files
from pathlib import Path, PurePosixPath
from typing import Annotated, NamedTuple, NoReturn

import typer
from rich.console import Console

from monitoring_cli import output
from monitoring_cli.auth import (
    AuthError,
    DeviceFlowExpiredError,
    SessionExpiredError,
    poll_token,
    start_device_flow,
)
from monitoring_cli.client import (
    ConflictError,
    MonitoringClient,
    NotFoundError,
    resolve_folder_id,
    resolve_query_id,
)
from monitoring_cli.config import (
    Config,
    ConfigError,
    NotLoggedInError,
    Profile,
    ProfileNotFoundError,
)

app = typer.Typer(help="Dedaub Monitoring CLI")
err = Console(stderr=True)
out = Console()

# Single network is currently supported across config/alert commands.
_NETWORK = "ethereum"

ProfileOption = Annotated[
    str | None, typer.Option("--profile", "-p", help="Profile name", hidden=True)
]


def _parse_ts(ts: str | None) -> float | None:
    if ts is None:
        return None
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def _exit_error(e: Exception) -> NoReturn:
    if isinstance(e, SessionExpiredError):
        err.print("Session expired. Run: dedaub-monitoring login")
    else:
        err.print(f"Error: {e}")
    raise typer.Exit(1)


def _load_client(profile_name: str | None) -> tuple[MonitoringClient, Profile]:
    try:
        config = Config.load()
        profile = config.get_profile(profile_name)
        return MonitoringClient(profile), profile
    except NotLoggedInError:
        err.print("Not logged in. Run: dedaub-monitoring login")
        raise typer.Exit(1)
    except ProfileNotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except SessionExpiredError:
        err.print("Session expired. Run: dedaub-monitoring login")
        raise typer.Exit(1)
    except ConfigError as e:
        err.print(f"{e}\nRun: dedaub-monitoring login")
        raise typer.Exit(1)


@app.command()
def login(
    profile: ProfileOption = "prod",
    base_url: Annotated[
        str, typer.Option(help="Backend base URL")
    ] = "https://api.dedaub.com",
    oidc_host: Annotated[
        str, typer.Option(help="Keycloak host")
    ] = "https://auth.dedaub.com",
    client_id: Annotated[
        str, typer.Option(help="Keycloak client ID")
    ] = "watchdog-client",
    realm: Annotated[str, typer.Option(help="Keycloak realm")] = "dedaub",
) -> None:
    """Authenticate via browser (OAuth2 Device Flow)."""
    profile = profile or "prod"
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

    try:
        config = Config.load()
    except NotLoggedInError:
        config = Config(default=profile, profiles={})

    config.upsert_profile(profile, p)
    config.save()
    typer.echo("Logged in.")


@app.command()
def logout(profile: ProfileOption = None) -> None:
    """Remove stored credentials for a profile."""
    try:
        config = Config.load()
    except NotLoggedInError:
        typer.echo("Not logged in.")
        return

    key = profile or config.default
    try:
        config.remove_profile(key)
    except ProfileNotFoundError:
        typer.echo("Not logged in.")
        return
    config.save()
    typer.echo("Logged out.")


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
        str, typer.Option(help="Look-back window, e.g. 5m, 24h, 7d")
    ] = "5m",
    start_time: Annotated[
        str | None,
        typer.Option(help="Start time (ISO 8601), e.g. 2025-01-01T00:00:00Z"),
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
    """Execute a query and print results. Requires --id. Pass SQL as argument or via stdin; omit to run the stored query text. Ctrl-C (or hitting --timeout) revokes the server-side task."""
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
            default_start_time=start_time,
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
    """Print the query explanation (dependency analysis). Omit SQL to use the stored query text."""
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
    src = files("monitoring_cli.skills")
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
