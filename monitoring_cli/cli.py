from __future__ import annotations

import contextlib
import datetime
import json
import os
import re
import select
import shutil
import signal
import sys
import time
from collections.abc import Iterator
from importlib.resources import as_file, files
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, NamedTuple, NoReturn
from urllib.parse import urlsplit

import httpx
import typer
from dedaub_auth.auth import (
    AuthError,
    DeviceFlowExpiredError,
    SessionExpiredError,
    poll_token,
    revoke_token,
    start_device_flow,
    token_type,
)
from dedaub_auth.config import (
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
    persist_refresh_token,
)
from rich.console import Console
from rich.markup import escape

from monitoring_cli import chartdata, output, render, slots, sqltools, widgets
from monitoring_cli.client import (
    ConflictError,
    ForbiddenError,
    MonitoringClient,
    NotFoundError,
    QueryCapError,
    resolve_folder_id,
    resolve_query_id,
)
from monitoring_cli.version import cli_version

app = typer.Typer(help="Dedaub Monitoring CLI")
err = Console(stderr=True)
out = Console()

# Exit codes that a harness can act on. Other failures exit 1; bad arguments 2.
EXIT_NOT_LOGGED_IN = 3  # `status` only: log in first, a retry will not help
EXIT_SLOTS_BUSY = 4  # run-query: no query slot became free within --wait
EXIT_NO_PICTURE = 5  # widget-picture, dashboard-picture: no picture is stored yet
EXIT_RENDER_FAILED = 6  # render-widget: the page said "error", timed out, or is missing
EXIT_NO_BROWSER = 7  # render-widget: Playwright is not installed, or no browser starts


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
        err.print(f"Error: {escape(str(e))}")  # server text can hold "[/x]"
    raise typer.Exit(1)


def _load_client(
    profile_name: str | None, not_logged_in_exit: int = 1
) -> tuple[MonitoringClient, Profile]:
    env_token = os.environ.get(REFRESH_TOKEN_ENV)
    try:
        if env_token:
            return _env_client(profile_name, env_token)
        config = Config.load()
        key = profile_name or config.default
        profile = config.get_profile(key)
        return MonitoringClient(
            profile, on_rotate=lambda old, new: _store_refresh_token(key, old, new)
        ), profile
    except NotLoggedInError:
        err.print("Not logged in. Run: dedaub-monitoring login")
        raise typer.Exit(not_logged_in_exit)
    except ProfileNotFoundError as e:
        err.print(str(e))
        raise typer.Exit(not_logged_in_exit)
    except ConfigError as e:
        err.print(f"{e}\nRun: dedaub-monitoring login")
        raise typer.Exit(not_logged_in_exit)


def _raise_interrupt(signum: int, frame: object) -> None:
    raise KeyboardInterrupt


def _revoke_on_termination() -> None:
    """A harness that gives up on a command sends SIGTERM (or SIGHUP), not
    Ctrl-C. Treat both like Ctrl-C, so the server task is revoked and does
    not hold one of the account's query slots after the command is gone."""
    for name in ("SIGTERM", "SIGHUP"):
        sig = getattr(signal, name, None)
        if sig is not None:
            with contextlib.suppress(ValueError, OSError):
                signal.signal(sig, _raise_interrupt)


def _prepare_sql(query_text: str) -> str:
    """Replace the SQL helpers the server does not have (selector('sig'),
    topic0('sig'), keccak256('text')) with their hash, and warn about
    signature parameters that the platform's macros decode wrongly."""
    new_text, rewrites = sqltools.rewrite_helpers(query_text)
    for r in rewrites:
        err.print(
            f"Rewrote {r.call} to {r.literal}",
            markup=False,
            highlight=False,
            soft_wrap=True,
        )
    signed: dict[str, list[str]] = {}
    for macro, param in sqltools.signed_int_params(new_text):
        signed.setdefault(macro, []).append(param.text)
    for macro, params in signed.items():
        err.print(
            f"Warning: {', '.join(params)}: signed int in a {macro}(...) signature. "
            "The platform's signature macros decode signed ints wrongly (they read "
            "the decimal value as hex), so these columns are wrong. Decode them "
            "from the raw data/calldata words instead.",
            markup=False,
            highlight=False,
            soft_wrap=True,
        )
    return new_text


def _explain_empty_result(
    client: MonitoringClient,
    query_text: str,
    query_id: int,
    entity_id: int,
    network: str | None,
    duration: str,
    end_time: str | None,
) -> None:
    """After an empty result, count the logs of each logs(...) signature's
    topic0 in the same window, by any emitter (forks too), and print whether
    the indexed flags or the address are the likely cause."""
    for m in sqltools.macro_signatures(query_text)[:3]:
        if m.macro != "logs" or m.signature is None:
            continue
        chain = m.chain or network
        if chain is None:
            continue
        sig = m.signature
        t0 = sqltools.topic0(sig)
        args = f"duration='{m.duration}'" if m.duration else ""
        check = _layout_count_sql("any", chain, args, t0, None)
        if sig.address:
            # A separate sample through the (address, block) index: in a
            # sample of a busy topic0 the address can be missing.
            check += "\nUNION ALL\n" + _layout_count_sql(
                "address", chain, args, t0, sig.address
            )
        try:
            rows = client.execute_query(
                check,
                query_id,
                entity_id,
                network=network,
                default_duration=duration,
                default_start_time=end_time,
                limit=20,
                poll_timeout=30,
                cap_wait=30,
                slot_dir=slots.STATE_DIR,
            )
        except Exception:
            err.print(
                f"(Could not count the logs of {sig.canonical} to explain the empty result.)"
            )
            continue
        err.print(
            _empty_result_note(sig, t0, rows),
            markup=False,
            highlight=False,
            soft_wrap=True,
        )


_LAYOUT_SAMPLE = 10000


def _layout_count_sql(
    scope: str, chain: str, args: str, t0: str, address: str | None
) -> str:
    where = f"l0.topic0 = '\\x{t0[2:]}'::bytea"
    if address:
        where += f" AND l0.address = '\\x{address[2:]}'::bytea"
    return (
        f"(SELECT '{scope}' AS scope, (l.topic1 IS NOT NULL)::int"
        " + (l.topic2 IS NOT NULL)::int + (l.topic3 IS NOT NULL)::int AS n_indexed,"
        " count(*) AS n\n"
        " FROM (SELECT l0.topic1, l0.topic2, l0.topic3"
        f" FROM {{{{{chain}.logs({args})}}}} l0 WHERE {where}"
        f" LIMIT {_LAYOUT_SAMPLE}) l GROUP BY 2)"
    )


def _layouts(rows: list[dict]) -> str:
    total = sum(int(r["n"]) for r in rows)
    sample = f" (a sample of {_LAYOUT_SAMPLE:,})" if total >= _LAYOUT_SAMPLE else ""
    parts = ", ".join(
        f"{int(r['n'])} with {int(r['n_indexed'])} indexed"
        for r in sorted(rows, key=lambda r: -int(r["n"]))
    )
    return f"{total} logs{sample}: {parts}"


def _empty_result_note(sig: sqltools.Signature, t0: str, rows: list[dict]) -> str:
    written = sig.indexed_count
    head = f"No rows. {sig.canonical} (topic0 {t0}) in this window:"
    anywhere = [r for r in rows if r.get("scope") == "any"]
    here = [r for r in rows if r.get("scope") == "address"]
    if not any(int(r["n"]) for r in anywhere):
        return (
            f"{head} no log from any emitter either, so the window or the event "
            "is the cause, not the indexed flags."
        )
    flags = (
        f"Your signature marks {written} argument(s) as indexed. The macro matches "
        "topics by these flags, so a wrong layout returns no rows: fix the flags."
    )
    if sig.address:
        if not any(int(r["n"]) for r in here):
            return (
                f"{head} none from {sig.address}, but {_layouts(anywhere)} from other "
                "emitters (forks or other deployments). Check the address, or drop "
                "it and filter on topic0 to see them all."
            )
        if not any(int(r["n_indexed"]) == written for r in here):
            return f"{head} {sig.address} emitted {_layouts(here)}. {flags}"
    elif not any(int(r["n_indexed"]) == written for r in anywhere):
        return f"{head} {_layouts(anywhere)}. {flags}"
    return (
        f"{head} logs with your indexed layout exist ({_layouts(here or anywhere)}), "
        "so the flags are not the cause: check the other conditions."
    )


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


def _store_refresh_token(profile_name: str, old: str | None, new: str) -> None:
    # Skipped when the file no longer holds `old` (a newer login, or the other
    # CLI already stored its rotation). A failed write only costs the
    # rotation, so warn and continue.
    try:
        persist_refresh_token(profile_name, old, new)
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
def status(profile: ProfileOption = None) -> None:
    """Check the login and the query slots in use. Exit 0 when logged in; exit 3 when not logged in or the login expired (run `dedaub-monitoring login`: a retry will not help)."""
    client, _ = _load_client(profile, not_logged_in_exit=EXIT_NOT_LOGGED_IN)
    try:
        me = client.get_me()
        active = client.get_active_queries()
    except SessionExpiredError:
        err.print(_session_expired_message())
        raise typer.Exit(EXIT_NOT_LOGGED_IN)
    except Exception as e:
        _exit_error(e)
    typer.echo(f"Logged in as {me['username']} (entity {me['entity_id']}).")
    typer.echo(f"Query slots in use: {len(active)} of {slots.slot_count()}.")


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
    query_text = _prepare_sql(query_text)
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
            help="END of the window (ISO 8601), e.g. 2025-01-01T12:00:00Z. The query reads \\[end-time - duration, end-time]. Omit for now."
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
    fmt: Annotated[
        str,
        typer.Option(
            "--format",
            help="table (for a person; cut to the terminal width), tsv or json (one object per line): exact and uncut, for agents and scripts.",
        ),
    ] = "table",
    wait: Annotated[
        float,
        typer.Option(
            help="Max seconds to wait for a free query slot when the account already runs its limit of concurrent queries (exit 4 after that). Do not wrap run-query in retry loops."
        ),
    ] = 300.0,
) -> None:
    """Execute a query and print results. Requires --id. Pass SQL as argument or via stdin; omit to run the stored query text. The window is \\[--end-time - --duration, --end-time]. Ctrl-C (or hitting --timeout) revokes the server-side task. Rows go to stdout; notes go to stderr."""
    if end_time is not None and start_time is not None:
        err.print(
            "Pass only --end-time. --start-time is a deprecated alias of it, not a window start."
        )
        raise typer.Exit(2)
    _revoke_on_termination()
    if fmt not in output.RESULT_FORMATS:
        err.print(f"--format must be one of: {', '.join(output.RESULT_FORMATS)}.")
        raise typer.Exit(2)
    end_time = end_time if end_time is not None else start_time
    client, _ = _load_client(profile)
    try:
        query_text, entity_id = _resolve_query_text_and_owner(
            client, id, query_text, entity_id
        )
        query_text = _prepare_sql(query_text)
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
            cap_wait=wait,
            on_cap_wait=lambda: err.print(
                f"All query slots are in use: waiting up to {wait:.0f}s for a free one."
            ),
            slot_dir=slots.STATE_DIR,
        )
    except QueryCapError as e:
        active: list[str] = []
        with contextlib.suppress(Exception):
            active = client.get_active_queries()
        err.print(
            f"{e} Running tasks: {', '.join(active) or 'none reported'}. "
            "They can belong to other sessions of this account: do not cancel a "
            "task you did not start. Try again later, or raise --wait.",
            markup=False,
            soft_wrap=True,
        )
        raise typer.Exit(EXIT_SLOTS_BUSY)
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
    lossy = output.format_query_results(results, fmt=fmt)
    if fmt != "table":
        err.print(f"{len(results)} row(s)", highlight=False)
    if lossy:
        err.print(
            f"Note: {lossy} value(s) are 2^53 or larger. The API sends numbers as "
            "JSON floats, so their last digits are lost. Select exact amounts as "
            "text (amount::text).",
            highlight=False,
            soft_wrap=True,
        )
    if not results and offset == 0:
        _explain_empty_result(
            client, query_text, id, entity_id, network, duration, end_time
        )


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
        query_text = _prepare_sql(query_text)
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
        query_text = _prepare_sql(query_text)
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
        query_text = _prepare_sql(query_text)
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
        query_text = _prepare_sql(query_text)
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


# The config flags of check-widget, preview-widget, create-widget and
# update-widget: the parameter name of each one and the config key it sets.
_FLAG_KEYS = {
    "x": "x_axis_name",
    "y": "y_axis_name",
    "y1": "y1_axis_name",
    "series_by": "series_by",
    "x_label": "x_label",
    "y_label": "y_label",
    "timeframe": "timeframe",
    "combine": "combine",
    "order_by": "order_by",
    "sorting_order": "sorting_order",
    "scale": "scale",
    "number_format": "number_format",
    "prefix": "prefix",
    "suffix": "suffix",
    "decimals": "decimals",
    "line_style": "line_style",
    "transform": "transform",
    "percent": "percent",
    "horizontal": "horizontal",
}


def _flag_config(params: dict[str, Any]) -> dict:
    """The config keys that the flags set, from the parameters of a widget
    command (call it with `locals()` first thing). An empty value clears the
    key. config_problems checks the values."""
    return {
        key: params[name]
        for name, key in _FLAG_KEYS.items()
        if params.get(name) is not None
    }


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


class _Checked(NamedTuple):
    """The checks of a draft: problems (each one blocks a save), notes, and
    the facts that the column types tell about the chart."""

    problems: list[str]
    notes: list[str]
    facts: list[str]


def _widget_problems(
    client: MonitoringClient, draft: _Draft, check_columns: bool = True
) -> _Checked:
    """The problems, the notes and the facts of a draft."""
    problems = widgets.config_problems(draft.widget_type, draft.config)
    problems += widgets.draw_problems(draft.widget_type, draft.config)
    notes = widgets.config_notes(draft.widget_type, draft.config)
    axis = widgets.missing_axis(draft.widget_type, draft.config)
    if axis:
        problems.append(axis)
    if not check_columns:
        return _Checked(problems, notes, [])
    if draft.query is None:
        notes.append("The widget reads no query, so the column check was skipped.")
        return _Checked(problems, notes, [])
    try:
        columns = _widget_columns(client, draft.query)
    except (httpx.HTTPStatusError, PermissionError) as e:
        problems.append(f"Cannot read the query columns: {e}")
        return _Checked(problems, notes, [])
    if not columns:
        notes.append(
            "The query metadata has no columns, so the column check was skipped."
        )
    names = [c["name"] for c in columns]
    for name in widgets.columns_not_in_query(draft.config, names, draft.widget_type):
        problems.append(f"The query has no column {name!r}.")
    facts, type_notes = widgets.column_type_notes(
        draft.widget_type, draft.config, columns
    )
    return _Checked(problems, notes + type_notes, facts)


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
_CombineOpt = Annotated[
    str | None,
    typer.Option(
        "--combine",
        help="Rows that share an X become one point by: sum, mean, median, min, max, count (combine; lines and bars)",
    ),
]
_OrderByOpt = Annotated[
    str | None,
    typer.Option(
        "--order-by",
        help="x (default) or y: put the X categories in the order of Y (order_by; lines and bars)",
    ),
]
_SortingOrderOpt = Annotated[
    str | None,
    typer.Option("--sorting-order", help="ASC or DESC (sorting_order)"),
]
_ScaleOpt = Annotated[
    str | None, typer.Option("--scale", help="Y scale: linear or log (scale)")
]
_NumberFormatOpt = Annotated[
    str | None,
    typer.Option(
        "--number-format",
        help="compact, full, currency or percent (number_format)",
    ),
]
_PrefixOpt = Annotated[
    str | None,
    typer.Option(
        "--prefix",
        help="Unit text before each value: tile, axis, tooltip (prefix), e.g. '$'",
    ),
]
_SuffixOpt = Annotated[
    str | None,
    typer.Option(
        "--suffix",
        help="Unit text after each value: tile, axis, tooltip (suffix); type the space: ' ETH'",
    ),
]
_DecimalsOpt = Annotated[
    str | None,
    typer.Option("--decimals", help="Digits after the decimal point, 0-20 (decimals)"),
]
_LineStyleOpt = Annotated[
    str | None,
    typer.Option(
        "--line-style",
        help="line, area, step or stacked (stacked areas, one per --series-by value) (line_style; line only)",
    ),
]
_PercentOpt = Annotated[
    bool | None,
    typer.Option(
        "--percent/--no-percent",
        help="A 100% stack: each series as its share of the total (percent; stackedbar, or line with --line-style stacked)",
    ),
]
_HorizontalOpt = Annotated[
    bool | None,
    typer.Option(
        "--horizontal/--no-horizontal",
        help="Bars on their side, categories down the left: for long labels (horizontal; bar, stackedbar)",
    ),
]
_TransformOpt = Annotated[
    str | None,
    typer.Option(
        "--transform",
        help="none, ma7, mean, ewma, bollinger (line only), cum, index or pct (transform; lines and bars)",
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
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400 and _PRIVATE_QUERIES.search(str(e)):
            # dashboard.py update_dashboard: a public dashboard cannot read a
            # private query. The publish route makes them public together.
            err.print(
                f"Error: {escape(str(e))}\nRun `dedaub-monitoring publish-dashboard --id {id}`: it lists"
                " the private queries and makes them public with the dashboard"
                " (--dry-run lists them only)."
            )
            raise typer.Exit(1)
        _exit_error(e)
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
def arrange_dashboard(
    id: Annotated[int, typer.Option(help="Dashboard ID")],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Print the layout as JSON (the input of set-layout) and save nothing",
        ),
    ] = False,
    profile: ProfileOption = None,
) -> None:
    """Arrange the widgets of a dashboard on the 12-column grid by type: value tiles in a row at the top, charts in pairs (a pie beside an 8-wide chart), tables at full width at the bottom. The order of the widgets stays. All or nothing."""
    client, p = _load_client(profile)
    try:
        # The dashboard body has no widgets; get-dashboard reads them the same way.
        current = client.list_widgets(dashboard_id=id) or []
        layout = widgets.auto_layout(current)
        if not layout:
            typer.echo(f"Dashboard {id} has no widgets.")
            return
        problems = widgets.layout_problems(layout)
        if problems:  # A bug in auto_layout: never send a bad layout.
            _print_problems(problems, [])
            raise typer.Exit(1)
        if dry_run:
            typer.echo(json.dumps(layout, indent=2))
            return
        client.set_dashboard_layout(id, layout)
    except typer.Exit:
        raise
    except NotFoundError as e:
        err.print(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    by_id = {w.get("widget_id"): w for w in current}
    output.format_query_results(
        [
            {
                "widget_id": item["widget_id"],
                "type": by_id.get(item["widget_id"], {}).get("type"),
                "x": item["x"],
                "y": item["y"],
                "width": item["width"],
                "height": item["height"],
            }
            for item in layout
        ]
    )
    typer.echo(f"Arranged {len(layout)} widget(s) on dashboard {id}.")
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
    combine: _CombineOpt = None,
    order_by: _OrderByOpt = None,
    sorting_order: _SortingOrderOpt = None,
    scale: _ScaleOpt = None,
    number_format: _NumberFormatOpt = None,
    prefix: _PrefixOpt = None,
    suffix: _SuffixOpt = None,
    decimals: _DecimalsOpt = None,
    line_style: _LineStyleOpt = None,
    transform: _TransformOpt = None,
    percent: _PercentOpt = None,
    horizontal: _HorizontalOpt = None,
    config: _ConfigOpt = None,
    clear: _ClearOpt = None,
) -> None:
    """Check a widget like the web Visualize tab: config keys and values, the options of the type, the axes the type needs, and the columns of the query and their types. Does not run the query. Prints each problem and exits 1 when there is one. Takes --id, or --query-id and --type."""
    flags = _flag_config(locals())
    if id is None:
        _require_new_widget_args(query_id, widget_type)
    config_input = _config_input(config)
    client, _ = _load_client(profile)
    try:
        draft = _widget_draft(
            client, id, query_id, widget_type, label, config_input, flags, clear
        )
        problems, notes, facts = _widget_problems(client, draft)
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
    for fact in facts:
        typer.echo(fact)
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
    combine: _CombineOpt = None,
    order_by: _OrderByOpt = None,
    sorting_order: _SortingOrderOpt = None,
    scale: _ScaleOpt = None,
    number_format: _NumberFormatOpt = None,
    prefix: _PrefixOpt = None,
    suffix: _SuffixOpt = None,
    decimals: _DecimalsOpt = None,
    line_style: _LineStyleOpt = None,
    transform: _TransformOpt = None,
    percent: _PercentOpt = None,
    horizontal: _HorizontalOpt = None,
    config: _ConfigOpt = None,
    clear: _ClearOpt = None,
    limit: Annotated[
        int | None,
        typer.Option(
            help=f"Max rows to read. Default and max for a chart: {widgets.CHART_ROWS}; for a table: {widgets.TABLE_ROWS} (max {widgets.PAGE_ROWS})"
        ),
    ] = None,
    show_rows: Annotated[
        int | None,
        typer.Option(
            "--show-rows",
            help=f"Rows to print (0: none). Default: {_SHOWN_ROWS} for a chart, all for a table. The summary counts all the rows read",
        ),
    ] = None,
    refresh: Annotated[
        bool,
        typer.Option(
            "--refresh",
            help="A chart reads its rows through the API's shared 15-minute cache, as the dashboard does; read the database again",
        ),
    ] = False,
    timeout: Annotated[
        float,
        typer.Option(help="Max seconds to wait for the rows"),
    ] = 120.0,
    sql: Annotated[
        bool,
        typer.Option("--sql", help="Print the SQL the widget runs, and do not run it"),
    ] = False,
) -> None:
    """Read the rows that the dashboard reads for a widget, and print a summary of what the chart draws (the X axis, the series, the rows it cannot draw) and the web chart's notes. A chart reads the query's table through ref() (or the query text when ref() cannot find the query) with the dashboard's row cap and cache; a table reads one page. Takes --id, or --query-id and --type."""
    flags = _flag_config(locals())
    if id is None:
        _require_new_widget_args(query_id, widget_type)
    _check_limit(limit, widget_type)
    config_input = _config_input(config)
    client, _ = _load_client(profile)
    # Known for sure after the draft (a saved widget has its own type).
    kind = {"table": widget_type == "table"}
    with _read_errors(kind):
        draft = _widget_draft(
            client, id, query_id, widget_type, label, config_input, flags, clear
        )
        kind["table"] = draft.widget_type == "table"
        columns, ref_sql, text_sql = _checked_sqls(client, draft, limit)
        if sql:
            typer.echo(ref_sql)
            if text_sql is not None:
                typer.echo("\n-- When ref() cannot find the query, the rows come from:")
                typer.echo(text_sql)
            return
        rows_limit = limit or (
            widgets.TABLE_ROWS if kind["table"] else widgets.CHART_ROWS
        )
        rows, read = _read_rows(
            client, draft, ref_sql, text_sql, rows_limit, refresh, timeout
        )
    _print_preview(draft, rows, rows_limit, show_rows, read)


def _check_limit(limit: int | None, widget_type: str | None) -> None:
    """Exit 2 on a --limit out of range. With no known type, the widest range
    (a table's page, or a chart) is the bound; _checked_sqls checks again with
    the type of the draft."""
    if limit is None:
        return
    if widget_type is None:
        max_rows = max(widgets.PAGE_ROWS, widgets.CHART_ROWS)
    else:
        max_rows = widgets.PAGE_ROWS if widget_type == "table" else widgets.CHART_ROWS
    if not 1 <= limit <= max_rows:
        what = f"for a {widget_type}" if widget_type else "for a widget"
        err.print(f"--limit must be from 1 to {max_rows} {what}.")
        raise typer.Exit(2)


def _checked_sqls(
    client: MonitoringClient, draft: _Draft, limit: int | None
) -> tuple[list[dict], str, str | None]:
    """Check the draft as preview-widget does (exit 1 on a problem, 2 on a bad
    --limit), then its columns and its SQL in the two forms."""
    _check_limit(limit, draft.widget_type)
    problems, notes, _ = _widget_problems(client, draft, check_columns=False)
    if draft.query is None:
        problems.append("The widget reads no query, so it has no rows to preview.")
    _print_problems(problems, notes)
    if problems:
        raise typer.Exit(1)
    assert draft.query is not None
    try:
        columns = _widget_columns(client, draft.query)
    except (httpx.HTTPStatusError, PermissionError) as e:
        # The dashboard reads the rows without the columns too.
        err.print(f"[yellow]Note:[/] cannot read the query columns: {escape(str(e))}")
        columns = []
    ref_sql, text_sql = widgets.widget_sqls_of(
        query=draft.query,
        columns=columns,
        widget_type=draft.widget_type,
        config=draft.config,
        timeframe=draft.config.get("timeframe"),
    )
    return columns, ref_sql, text_sql


def _read_rows(
    client: MonitoringClient,
    draft: _Draft,
    ref_sql: str,
    text_sql: str | None,
    rows_limit: int,
    refresh: bool,
    timeout: float,
) -> tuple[list[dict], dict[str, Any]]:
    """The rows of the widget as the dashboard reads them, and how they were
    read ({"cached", "read_at"} for a chart). When ref() cannot find the
    query, the rows come from the query text (widgetRows.ts:99-119)."""
    query = draft.query
    assert query is not None
    is_table = draft.widget_type == "table"
    read: dict[str, Any] = {}

    def run(statement: str) -> list[dict]:
        if is_table:
            # A table reads pages, as the Results tab does: a task that
            # Ctrl-C revokes.
            return client.execute_query(
                statement,
                query["query_id"],
                query["owner"]["entity_id"],
                limit=rows_limit,
                poll_timeout=timeout,
                on_start=lambda tid: err.print(f"task {tid} (Ctrl-C to cancel)"),
            )
        # A chart reads its rows as the dashboard does (widgetRows.ts:73-97).
        answer = client.widget_rows(
            statement,
            query["query_id"],
            query["owner"]["entity_id"],
            limit=rows_limit,
            refresh=refresh,
            timeout=timeout,
        )
        read.update(cached=answer.get("cached"), read_at=answer.get("read_at"))
        return answer.get("rows") or []

    try:
        return run(ref_sql), read
    except (RuntimeError, httpx.HTTPStatusError) as e:
        if text_sql is None or not widgets.NOT_REFERABLE.search(str(e)):
            raise
    err.print(
        "ref() cannot find the query (it has no run settings): reading the query text."
    )
    try:
        return run(text_sql), read
    except (RuntimeError, httpx.HTTPStatusError) as text_error:
        raise RuntimeError(
            f"Read from the query text (the query has no run settings): {text_error}"
        ) from text_error


@contextlib.contextmanager
def _read_errors(kind: dict[str, bool]) -> Iterator[None]:
    """The errors of a widget read, as messages and exit codes. `kind["table"]`
    says whether the read was a task that Ctrl-C revokes."""
    try:
        yield
    except typer.Exit:
        raise
    except KeyboardInterrupt:
        # A chart's read has no task: the server stops it at its own timeout.
        err.print("Cancelled — server task revoked." if kind["table"] else "Cancelled.")
        raise typer.Exit(130)
    except TimeoutError as e:
        revoked = " — task revoked." if kind["table"] else "."
        err.print(f"{escape(str(e))}{revoked} Shorten --timeframe, or raise --timeout.")
        raise typer.Exit(1)
    except NotFoundError as e:
        err.print(escape(str(e)))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)


# preview-widget prints this many rows of a chart by default: the summary
# counts all of them, and 10,000 rows would flood the terminal.
_SHOWN_ROWS = 20


def _print_preview(
    draft: _Draft,
    rows: list[dict],
    rows_limit: int,
    show_rows: int | None,
    read: dict[str, Any],
) -> None:
    """The sample rows, then the summary of the chart (stdout) and its notes (stderr)."""
    if show_rows is None:
        count = len(rows) if draft.widget_type == "table" else _SHOWN_ROWS
    else:
        count = max(0, show_rows)
    shown = rows[:count]
    if shown or not rows:
        output.format_query_results(shown)
    if shown and len(shown) < len(rows):
        typer.echo(
            f"Printed {len(shown)} of {len(rows)} rows (--show-rows N prints more)."
        )
    if read.get("cached"):
        typer.echo(
            f"The rows come from the shared 15-minute cache, read at {read.get('read_at')}"
            " (--refresh reads the database again)."
        )
    try:
        summary = chartdata.summarize(
            draft.widget_type, draft.config, rows, limit=rows_limit
        )
    except (OverflowError, ValueError):
        # A number past the float range: the summary is a help, not a gate.
        summary = chartdata.Summary(
            notes=["The summary is not available for these values."]
        )
    for fact in summary.facts:
        typer.echo(fact)
    notes = summary.notes + widgets.series_notes(draft.widget_type, draft.config, rows)
    _print_problems([], notes)


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
    combine: _CombineOpt = None,
    order_by: _OrderByOpt = None,
    sorting_order: _SortingOrderOpt = None,
    scale: _ScaleOpt = None,
    number_format: _NumberFormatOpt = None,
    prefix: _PrefixOpt = None,
    suffix: _SuffixOpt = None,
    decimals: _DecimalsOpt = None,
    line_style: _LineStyleOpt = None,
    transform: _TransformOpt = None,
    percent: _PercentOpt = None,
    horizontal: _HorizontalOpt = None,
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
    flags = _flag_config(locals())
    config_input = _config_input(config)
    client, p = _load_client(profile)
    try:
        draft = _widget_draft(
            client, None, query_id, widget_type, label, config_input, flags
        )
        problems, notes, _ = _widget_problems(client, draft, check_columns=not force)
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
    combine: _CombineOpt = None,
    order_by: _OrderByOpt = None,
    sorting_order: _SortingOrderOpt = None,
    scale: _ScaleOpt = None,
    number_format: _NumberFormatOpt = None,
    prefix: _PrefixOpt = None,
    suffix: _SuffixOpt = None,
    decimals: _DecimalsOpt = None,
    line_style: _LineStyleOpt = None,
    transform: _TransformOpt = None,
    percent: _PercentOpt = None,
    horizontal: _HorizontalOpt = None,
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
    flags = _flag_config(locals())
    config_input = _config_input(config)
    client, p = _load_client(profile)
    try:
        draft = _widget_draft(
            client, id, query_id, widget_type, label, config_input, flags, clear
        )
        problems, notes, _ = _widget_problems(client, draft, check_columns=not force)
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


# --- render-widget: a real picture, drawn by the web app ---------------------------

# The card picture of the Widgets tab (widgetPreview.ts:24-25 and :61): a JPEG of
# 640 x 360 at quality 0.85.
_CARD_WIDTH = 640
_CARD_HEIGHT = 360
_CARD_QUALITY = 85
# backend routers/utils.py MAX_UPLOAD_FILE_SIZE
_MAX_UPLOAD_BYTES = 2 * 1024 * 1024
# The PNG for the agent is drawn at 2 device pixels per CSS pixel: small axis
# labels stay readable.
_PNG_SCALE = 2.0
_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")


def _check_theme(theme: str) -> None:
    """Exit 2 on a theme other than dark or light, before any network call."""
    if theme not in ("dark", "light"):
        err.print("--theme must be dark or light.")
        raise typer.Exit(2)


def _render_page_url(app_url: str | None, base_url: str) -> str:
    """The render page of the web app: the app of the profile's API, or
    --app-url (https, or http on this machine for a dev server)."""
    url = (app_url or widgets.app_url(base_url)).rstrip("/")
    parts = urlsplit(url)
    local = parts.hostname in _LOCAL_HOSTS
    if not parts.hostname or not (
        parts.scheme == "https" or (parts.scheme == "http" and local)
    ):
        err.print(
            "--app-url must be https://…, or http://localhost:<port> for a dev server."
        )
        raise typer.Exit(2)
    app_host = urlsplit(widgets.app_url(base_url)).hostname
    if not local and parts.hostname != app_host:
        # The page gets the rows of the query: say where they go.
        err.print(f"Warning: The rows of the query go to {escape(parts.hostname)}.")
    return url + render.PAGE_PATH


def _check_upload(draft: _Draft, limit: int | None = None) -> None:
    """--upload stores the picture of the saved widget only, as the owner's
    browser makes it: a chart, with no change from the flags, all its rows
    (no --limit) and the query that it reads."""
    stored = draft.stored
    if stored is None:
        err.print("--upload needs --id: it stores the picture of a saved widget.")
        raise typer.Exit(2)
    if limit is not None:
        err.print(
            "--upload draws all the rows that the widget reads: do not use --limit"
            " with it."
        )
        raise typer.Exit(2)
    query_id = (draft.query or {}).get("query_id")
    if query_id is not None and query_id not in (stored.get("query_ids") or []):
        err.print(
            f"--upload draws the query of the saved widget, not query {query_id}."
            " Save the change first (update-widget), or render without --upload."
        )
        raise typer.Exit(2)
    saved = widgets.clean_config(widgets.normalize_config(stored.get("config") or {}))
    if draft.config != saved or draft.widget_type != stored.get("type"):
        err.print(
            "--upload draws the saved widget only. Save the changes first"
            " (update-widget), or render without --upload."
        )
        raise typer.Exit(2)
    if draft.widget_type not in widgets.CHART_TYPES:
        # widgetPreview.ts:11: a widget with no chart has no picture.
        err.print(f"A {draft.widget_type} widget has no card picture in the web app.")
        raise typer.Exit(2)


@app.command()
def render_widget(
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
    combine: _CombineOpt = None,
    order_by: _OrderByOpt = None,
    sorting_order: _SortingOrderOpt = None,
    scale: _ScaleOpt = None,
    number_format: _NumberFormatOpt = None,
    prefix: _PrefixOpt = None,
    suffix: _SuffixOpt = None,
    decimals: _DecimalsOpt = None,
    line_style: _LineStyleOpt = None,
    transform: _TransformOpt = None,
    percent: _PercentOpt = None,
    horizontal: _HorizontalOpt = None,
    config: _ConfigOpt = None,
    clear: _ClearOpt = None,
    limit: Annotated[
        int | None,
        typer.Option(help=f"Max rows to read. Default and max: {widgets.CHART_ROWS}"),
    ] = None,
    refresh: Annotated[
        bool,
        typer.Option(
            "--refresh",
            help="Read the database again, not the API's shared 15-minute cache",
        ),
    ] = False,
    theme: Annotated[str, typer.Option("--theme", help="dark or light")] = "dark",
    width: Annotated[
        int,
        typer.Option(
            help=f"Card width in CSS pixels, {render.MIN_SIZE}-{render.MAX_SIZE}"
        ),
    ] = render.DEFAULT_WIDTH,
    height: Annotated[
        int,
        typer.Option(
            help=f"Card height in CSS pixels, {render.MIN_SIZE}-{render.MAX_SIZE}"
        ),
    ] = render.DEFAULT_HEIGHT,
    out_path: Annotated[
        Path | None,
        typer.Option(
            "--out",
            help="PNG file to write. Default: widget-<id or draft>-<theme>.png in the current directory",
        ),
    ] = None,
    app_url: Annotated[
        str | None,
        typer.Option(
            "--app-url",
            help="Web app that draws the widget. Default: the app of the profile's API. http://localhost:<port> for a dev server",
        ),
    ] = None,
    browser_channel: Annotated[
        str | None,
        typer.Option(
            "--browser-channel",
            help="chrome, msedge or chromium (the browser of `playwright install chromium`). Default: chrome, then chromium",
        ),
    ] = None,
    upload: Annotated[
        bool,
        typer.Option(
            "--upload",
            help="Also store the picture as the widget's card picture of --theme (a 640x360 JPEG, as the web app makes it). Saved widget (--id) that you own, with no flag changes",
        ),
    ] = False,
    timeout: Annotated[
        float,
        typer.Option(help="Max seconds for each step: the rows, then the page"),
    ] = 60.0,
) -> None:
    """Draw a widget with the web app's own chart code in a headless browser, and save it as a PNG. It reads the rows as preview-widget does, runs the same checks and prints the same summary, then draws them on the web app's /render/widget page. Open the PNG and check it: labels, an empty plot, too many series. Takes --id, or --query-id and --type. Needs the render extra (Playwright). Exits 1 on a problem of the checks, 6 when the page cannot draw the widget, 7 when Playwright or a browser is missing."""
    flags = _flag_config(locals())
    if id is None:
        _require_new_widget_args(query_id, widget_type)
    _check_theme(theme)
    _check_limit(limit, "chart")
    for name, size in (("--width", width), ("--height", height)):
        if not render.MIN_SIZE <= size <= render.MAX_SIZE:
            err.print(f"{name} must be from {render.MIN_SIZE} to {render.MAX_SIZE}.")
            raise typer.Exit(2)
    config_input = _config_input(config)
    client, p = _load_client(profile)
    page_url = _render_page_url(app_url, p.base_url)
    kind = {"table": False}
    with _read_errors(kind):
        draft = _widget_draft(
            client, id, query_id, widget_type, label, config_input, flags, clear
        )
        if draft.widget_type == "table":
            err.print("A table widget has no chart to draw: use preview-widget.")
            raise typer.Exit(2)
        if upload:
            _check_upload(draft, limit)
        columns, ref_sql, text_sql = _checked_sqls(client, draft, limit)
        rows_limit = limit or widgets.CHART_ROWS
        rows, read = _read_rows(
            client, draft, ref_sql, text_sql, rows_limit, refresh, timeout
        )
    _print_preview(draft, rows, rows_limit, 0, read)
    query = draft.query or {}
    page_input: dict[str, Any] = {
        "type": draft.widget_type,
        "config": draft.config,
        "rows": rows,
        "label": draft.label or query.get("query_name") or "",
        "theme": theme,
        "width": width,
        "height": height,
    }
    if columns:
        page_input["columns"] = [c["name"] for c in columns]
    shots = [render.Shot(page_input, "png", scale=_PNG_SCALE)]
    if upload:
        # The card of the Widgets tab shows the chart with no title.
        card = {
            **page_input,
            "label": "",
            "width": _CARD_WIDTH,
            "height": _CARD_HEIGHT,
        }
        shots.append(render.Shot(card, "jpeg", scale=1.0, quality=_CARD_QUALITY))
    try:
        pictures = render.render(
            page_url, shots, channel=browser_channel, timeout=timeout
        )
    except render.PlaywrightMissing as e:
        err.print(escape(str(e)))
        raise typer.Exit(EXIT_NO_BROWSER)
    except render.RenderFailed as e:
        err.print(f"{escape(str(e))} (page: {escape(page_url)})")
        raise typer.Exit(EXIT_RENDER_FAILED)
    name = draft.stored.get("widget_id") if draft.stored else "draft"
    path = out_path or Path(f"widget-{name}-{theme}.png")
    _write_file(path, pictures[0].data)
    pixels = f"{round(width * _PNG_SCALE)}x{round(height * _PNG_SCALE)} px"
    typer.echo(f"Saved {path} ({len(pictures[0].data)} bytes, PNG, {pixels}).")
    if pictures[0].message is not None:
        # WidgetRender.tsx: the widget shows a message, not a chart. The picture
        # is saved so that the agent can see it; it is not uploaded.
        err.print(
            f"✗ The widget shows a message, not a chart: {escape(pictures[0].message)}"
        )
        raise typer.Exit(1)
    if upload:
        _upload_card(client, draft, theme, pictures[1].data)


def _upload_card(
    client: MonitoringClient, draft: _Draft, theme: str, picture: bytes
) -> None:
    assert draft.stored is not None
    widget_id = draft.stored["widget_id"]
    if len(picture) > _MAX_UPLOAD_BYTES:
        err.print(
            f"The card picture has {len(picture)} bytes; the API takes at most {_MAX_UPLOAD_BYTES}."
        )
        raise typer.Exit(1)
    try:
        url = client.upload_widget_picture(widget_id, theme, picture)
    except ForbiddenError as e:
        err.print(
            f"Refused: {escape(str(e.detail or e))}. Only the owner of the widget can store its picture."
        )
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    typer.echo(
        f"Uploaded the {theme} card picture of widget {widget_id}"
        f" ({len(picture)} bytes, JPEG, {_CARD_WIDTH}x{_CARD_HEIGHT} px): {url}"
    )


# --- sharing, publishing and the stored pictures ---------------------------------

# dashboard.py update_dashboard: the 400 when a public dashboard reads a private query.
_PRIVATE_QUERIES = re.compile(r"contains private queries")


def _query_list(queries: list[dict], ids: list[int]) -> str:
    """`id (name)` for each of `ids`, with the names from `queries`."""
    names = {q.get("query_id"): q.get("query_name") for q in queries}
    return ", ".join(f"{i} ({names[i]})" if names.get(i) else str(i) for i in ids)


def _refuse_blocked(queries: list[dict], what: str) -> None:
    """Exit 1 when a private query cannot be made public: the server would
    answer 403 and change nothing."""
    blocked = [q for q in queries if not q.get("can_edit")]
    if blocked:
        err.print(
            f"{len(blocked)} of the private queries cannot be made public, so the {what}"
            " cannot be public. Nothing changed."
        )
        raise typer.Exit(1)


def _publish_error(e: ConflictError | ForbiddenError, command: str) -> NoReturn:
    """The 409 and 403 of a share or a publish (dashboard.py make_queries_public)."""
    if isinstance(e, ConflictError):
        err.print(
            f"{escape(str(e.detail or 'The private queries changed.'))} Nothing changed:"
            f" run `dedaub-monitoring {command}` again to see the new list."
        )
    else:
        err.print(
            f"Refused: {escape(str(e.detail or e))}. Only the owner can do this, and each private"
            " query must be one that you can edit. Nothing changed."
        )
    raise typer.Exit(1)


@app.command()
def widget_private_queries(
    id: Annotated[int, typer.Option(help="Widget ID")],
    profile: ProfileOption = None,
) -> None:
    """List the private queries that a widget reads (also through ref()): share-widget --public makes them public. Owner only."""
    client, _ = _load_client(profile)
    try:
        queries = client.widget_private_queries(id)
    except NotFoundError as e:
        err.print(escape(str(e)))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    output.format_private_queries(queries)


@app.command()
def share_widget(
    id: Annotated[int, typer.Option(help="Widget ID")],
    public: Annotated[
        bool | None,
        typer.Option(
            "--public/--private",
            help="--public: everyone who is signed in can open the widget, and its private queries become public. --private: only the owner",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="With --public: list the private queries that would become public; change nothing",
        ),
    ] = False,
    profile: ProfileOption = None,
) -> None:
    """Share a widget with everyone who is signed in (--public), or make it private again (--private). --public also makes public each private query that the widget reads, also through ref(): their text, rows and alerts. It prints them first. All or nothing."""
    if public is None:
        err.print("Provide --public or --private.")
        raise typer.Exit(2)
    if dry_run and not public:
        err.print(
            "--dry-run needs --public: it lists the queries that would be published."
        )
        raise typer.Exit(2)
    client, p = _load_client(profile)
    queries: list[dict] = []
    try:
        if public:
            queries = client.widget_private_queries(id)
            if queries:
                output.format_private_queries(queries)
            _refuse_blocked(queries, "widget")
            if dry_run:
                if not queries:
                    typer.echo("No private query would become public.")
                typer.echo("Dry run: nothing changed.")
                return
        result = client.share_widget(id, public, [q["query_id"] for q in queries])
    except typer.Exit:
        raise
    except (ConflictError, ForbiddenError) as e:
        _publish_error(e, f"share-widget --id {id} --public")
    except NotFoundError as e:
        err.print(escape(str(e)))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    if not public:
        typer.echo(f"Widget {id} is private: only its owner can open it.")
        return
    typer.echo(f"Widget {id} is public: everyone who is signed in can open it.")
    made_public = result.get("public_query_ids") or []
    if made_public:
        typer.echo(f"These queries are public now: {_query_list(queries, made_public)}")
    _echo_links(p.base_url, {"widget_id": id}, [])


@app.command()
def publish_dashboard(
    id: Annotated[int, typer.Option(help="Dashboard ID")],
    unlisted: Annotated[
        bool | None,
        typer.Option(
            "--unlisted/--listed",
            help="Hide the dashboard from the public list, or show it. Default: as it is",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="List the private queries that would become public; change nothing",
        ),
    ] = False,
    profile: ProfileOption = None,
) -> None:
    """Make a dashboard public, and make public each private query that its widgets read (also through ref()), in one step: their text, rows and alerts. It prints them first. On an unlisted dashboard, those queries are unlisted too. All or nothing. Use this, not update-dashboard --public, when the dashboard reads a private query."""
    client, p = _load_client(profile)
    try:
        stored = client.get_dashboard(id)
        queries = client.dashboard_private_queries(id)
        output.format_private_queries(queries)
        _refuse_blocked(queries, "dashboard")
        if dry_run:
            typer.echo("Dry run: nothing changed.")
            return
        is_unlisted = bool(stored.get("is_unlisted")) if unlisted is None else unlisted
        result = client.publish_dashboard(
            id,
            {
                "name": stored.get("name"),
                "description": stored.get("description"),
                "is_public": True,
                "is_unlisted": is_unlisted,
                "entity_id": stored.get("entity_id"),
                "query_ids": [q["query_id"] for q in queries],
            },
        )
    except typer.Exit:
        raise
    except (ConflictError, ForbiddenError) as e:
        _publish_error(e, f"publish-dashboard --id {id}")
    except NotFoundError as e:
        err.print(escape(str(e)))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)
    visibility = "public, unlisted" if is_unlisted else "public"
    typer.echo(f"Dashboard {id} is {visibility}.")
    made_public = result.get("public_query_ids") or []
    if made_public:
        typer.echo(f"These queries are public now: {_query_list(queries, made_public)}")
    _echo_links(p.base_url, None, [id])


# The picture columns of each theme (backend dashboard.py PREVIEW_COLUMNS): the
# URL, the time of its upload, and the other theme's time.
_PICTURE_KEYS = {
    "dark": ("preview_url", "preview_updated_at", "preview_light_updated_at"),
    "light": ("preview_url_light", "preview_light_updated_at", "preview_updated_at"),
}
_PICTURE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}
# How the web app makes each picture (DashboardClient.tsx canCapture: the
# owner's dashboard page, 1000 px wide or more, in the theme of the picture).
_PICTURE_HOW = {
    "widget": "The owner's visit of a dashboard that has the widget makes the picture of"
    " the page's theme. A table or value widget has none (widgetPreview.ts:11).",
    "dashboard": "The owner's visit of the dashboard (a window 1000 px wide or more)"
    " makes the picture of the page's theme.",
}
_PICTURE_AGAIN = {
    # widgetPreview.ts:14-15 WIDGET_PREVIEW_FRESH_MS
    "widget": "A dashboard visit makes a new picture only when the old one is more"
    " than 24 hours old.",
    "dashboard": "The owner's next visit of the dashboard makes a new picture.",
}
# Two writes of one transaction have the same now(): a picture upload also
# sets the row's _ts (the trigger common.updated_timestamp_func).
_SAME_WRITE = datetime.timedelta(seconds=2)
_ThemeOpt = Annotated[
    str, typer.Option("--theme", help="dark or light: the picture of this theme")
]
_OutOpt = Annotated[
    Path | None,
    typer.Option(
        "--out",
        help="File to write. Default: <kind>-<id>-<theme>.jpg in the current directory",
    ),
]


def _parse_time(value: Any) -> datetime.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        moment = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=datetime.UTC)


def _age(moment: datetime.datetime, now: datetime.datetime) -> str:
    seconds = max(0, int((now - moment).total_seconds()))
    days, rest = divmod(seconds, 86_400)
    hours, rest = divmod(rest, 3_600)
    if days:
        return f"{days}d {hours}h"
    return f"{hours}h {rest // 60}m" if hours else f"{rest // 60}m"


def _stale(
    taken: datetime.datetime | None,
    other: datetime.datetime | None,
    changed: datetime.datetime | None,
) -> str:
    """Whether the row changed after the picture. The row's _ts also moves on
    a share and on the upload of the other theme's picture, so a change at
    that upload's time is not known to be a config change."""
    if taken is None or changed is None:
        return "unknown (no time of the picture or of the last change)"
    if changed - taken <= _SAME_WRITE:
        return "no"
    if other is not None and abs(changed - other) <= _SAME_WRITE:
        return "unknown (the last change is the upload of the other theme's picture)"
    return (
        f"yes: changed {_age(taken, changed)} after the picture"
        " (a share also counts as a change)"
    )


def _write_file(path: Path, data: bytes) -> None:
    """Write a picture, or stop with a clear message (exit 1), not a traceback."""
    try:
        path.write_bytes(data)
    except OSError as e:
        err.print(f"Cannot write {escape(str(path))}: {escape(str(e.strerror or e))}")
        raise typer.Exit(1)


def _save_picture(
    client: MonitoringClient,
    kind: str,
    item_id: int,
    record: dict,
    theme: str,
    out_path: Path | None,
    changed: datetime.datetime | None,
    unknown: str | None = None,
) -> None:
    """Save the stored picture of a widget or a dashboard and print its facts.
    The commands check --theme before any network call."""
    url_key, time_key, other_key = _PICTURE_KEYS[theme]
    url = record.get(url_key)
    if not url:
        err.print(
            f"No picture yet: only the owner's browser makes it. {_PICTURE_HOW[kind]}"
        )
        raise typer.Exit(EXIT_NO_PICTURE)
    data, content_type = client.download_public(str(url))
    extension = _PICTURE_TYPES.get(content_type, ".jpg")
    path = out_path or Path(f"{kind}-{item_id}-{theme}{extension}")
    _write_file(path, data)
    now = datetime.datetime.now(datetime.UTC)
    taken = _parse_time(record.get(time_key))
    typer.echo(f"Saved {path} ({len(data)} bytes, {content_type or 'unknown type'}).")
    if taken is not None:
        utc = taken.astimezone(datetime.UTC)
        typer.echo(f"Taken: {utc:%Y-%m-%d %H:%M} UTC ({_age(taken, now)} ago)")
    if changed is not None:
        utc = changed.astimezone(datetime.UTC)
        typer.echo(f"Last change: {utc:%Y-%m-%d %H:%M} UTC")
    stale = unknown or _stale(taken, _parse_time(record.get(other_key)), changed)
    typer.echo(f"Stale: {stale}")
    if stale.startswith("yes"):
        typer.echo(_PICTURE_AGAIN[kind])


# After the dashboard picture, the owner's browser uploads the card picture of
# each widget it owns, one after the other (DashboardClient.tsx:420-431).
_CARD_UPLOADS_AFTER = datetime.timedelta(minutes=10)


def _widget_change(widget: dict) -> tuple[datetime.datetime | None, bool]:
    """The widget's last change, and whether that change is the upload of its
    own card picture. That upload moves the widget's _ts too
    (common.updated_timestamp_func), so an edit before it cannot be seen."""
    changed = _parse_time(widget.get("_ts"))
    if changed is None:
        return None, False
    for key in ("preview_updated_at", "preview_light_updated_at"):
        picture = _parse_time(widget.get(key))
        if picture is not None and abs(changed - picture) <= _SAME_WRITE:
            return changed, True
    return changed, False


def _dashboard_change(
    dashboard: dict, dashboard_widgets: list[dict], taken: datetime.datetime | None
) -> tuple[datetime.datetime | None, str | None]:
    """The last change of a dashboard and its widgets, and why it is unknown.
    A card upload in the minutes after the dashboard picture is part of the
    same visit: it is not a change. A later card upload (the widget page,
    the Widgets tab, `render-widget --upload`) can hide an edit."""
    times = [_parse_time(dashboard.get("_ts"))]
    hidden: list[tuple[datetime.datetime, int]] = []
    for widget in dashboard_widgets:
        changed, card = _widget_change(widget)
        if changed is None:
            continue
        if not card:
            times.append(changed)
        elif taken is None or not (
            taken - _SAME_WRITE <= changed <= taken + _CARD_UPLOADS_AFTER
        ):
            hidden.append((changed, int(widget.get("widget_id") or 0)))
    known = max((t for t in times if t is not None), default=None)
    late = max(hidden, default=None)
    if (
        late is not None
        and taken is not None
        and late[0] > taken + _SAME_WRITE
        and (known is None or late[0] > known)
    ):
        return late[0], (
            f"unknown (the last change of widget {late[1]} is the upload of its "
            "card picture: an edit before it cannot be told apart)"
        )
    return known, None


@app.command()
def widget_picture(
    id: Annotated[int, typer.Option(help="Widget ID")],
    theme: _ThemeOpt = "dark",
    out_path: _OutOpt = None,
    profile: ProfileOption = None,
) -> None:
    """Download the stored picture of a widget (the card of the Widgets tab) and print its path, its age, and whether the widget changed after it. Only the owner's browser makes the picture; a table or value widget has none. Exits 5 when there is no picture."""
    _check_theme(theme)
    client, _ = _load_client(profile)
    try:
        widget = client.get_widget(id)
        _save_picture(
            client,
            "widget",
            id,
            widget,
            theme,
            out_path,
            _parse_time(widget.get("_ts")),
        )
    except typer.Exit:
        raise
    except NotFoundError as e:
        err.print(escape(str(e)))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)


@app.command()
def dashboard_picture(
    id: Annotated[int, typer.Option(help="Dashboard ID")],
    theme: _ThemeOpt = "dark",
    out_path: _OutOpt = None,
    profile: ProfileOption = None,
) -> None:
    """Download the stored picture of a dashboard (the preview of its link) and print its path, its age, and whether the dashboard or one of its widgets changed after it. Only the owner's browser makes the picture. Exits 5 when there is no picture."""
    _check_theme(theme)
    client, _ = _load_client(profile)
    try:
        dashboard = client.get_dashboard(id)
        # The last change of a dashboard is the later of its own change and its
        # newest widget change (dashboard.py list_dashboards updated_at).
        taken = _parse_time(dashboard.get(_PICTURE_KEYS[theme][1]))
        changed, unknown = _dashboard_change(
            dashboard, client.list_widgets(dashboard_id=id), taken
        )
        _save_picture(
            client, "dashboard", id, dashboard, theme, out_path, changed, unknown
        )
    except typer.Exit:
        raise
    except NotFoundError as e:
        err.print(escape(str(e)))
        raise typer.Exit(1)
    except Exception as e:
        _exit_error(e)


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
