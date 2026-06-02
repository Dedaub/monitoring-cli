from __future__ import annotations

import datetime
import sys
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import Annotated, NoReturn

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


def _resolve_query_text_and_owner(
    client: MonitoringClient,
    query_id: int,
    query_text: str | None,
    entity_id: int | None,
) -> tuple[str, int]:
    """Resolve query text (from arg, stdin, or stored) and the owning entity id."""
    if query_text is None:
        if sys.stdin.isatty():
            q = client.get_query(query_id)
            query_text = q.get("query_text", "")
            if entity_id is None:
                entity_id = q["owner"]["entity_id"]
        else:
            query_text = sys.stdin.read()
    if entity_id is None:
        entity_id = client.get_query(query_id)["owner"]["entity_id"]
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
        if sys.stdin.isatty():
            err.print("No query text provided. Pass as argument or pipe via stdin.")
            raise typer.Exit(1)
        query_text = sys.stdin.read()
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
) -> None:
    """Execute a query and print results. Requires --id. Pass SQL as argument or via stdin; omit to run the stored query text."""
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
        )
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_query_results(results)


@app.command()
def get_config(
    profile: ProfileOption = None,
    id: Annotated[int | None, typer.Option(help="Query ID")] = None,
    path: Annotated[str | None, typer.Option(help="Query path")] = None,
    entity_id: Annotated[
        int | None, typer.Option(help="Entity ID (for path lookup)")
    ] = None,
) -> None:
    """Show materialization/scheduling config for a query. Specify with --id <query_id> or --path /Folder/QueryName."""
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        cfg = client.get_run_config(qid, _NETWORK)
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
            _NETWORK,
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
            _NETWORK,
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
            _NETWORK,
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
) -> None:
    """Disable notifications for a query (materialization is left unchanged). Specify with --id <query_id> or --path /Folder/QueryName."""
    client, _ = _load_client(profile)
    try:
        qid = _resolve_query(client, id, path, entity_id)
        client.set_notify_config(
            qid, _NETWORK, {"notify": False, "alert_email": False, "webhook_id": None}
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
            if client.get_notify_config(q["query_id"], _NETWORK).get("notify")
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
def install_skill() -> None:
    """Install the Claude Code /dedaub-monitoring skill to ~/.claude/skills/dedaub-monitoring/SKILL.md."""
    dest = Path.home() / ".claude" / "skills" / "dedaub-monitoring" / "SKILL.md"
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        src = files("monitoring_cli.skills").joinpath("SKILL.md")
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError as e:
        _exit_error(e)
    typer.echo(f"Skill installed to {dest}")
