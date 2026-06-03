from __future__ import annotations

from pathlib import PurePosixPath

from rich.console import Console
from rich.table import Table
from rich.tree import Tree

_console = Console()

_MSG_MAX = 120


def _truncate(text: str, limit: int = _MSG_MAX) -> str:
    return text if len(text) <= limit else text[:limit] + "…"


def format_entities(
    entities: list[dict],
    *,
    console: Console | None = None,
) -> None:
    c = console or _console
    table = Table(show_header=True)
    table.add_column("Name")
    table.add_column("ID")
    for e in entities:
        table.add_row(str(e["username"]), str(e["entity_id"]))
    c.print(table)


def format_tree(
    folders: list[dict],
    queries: list[dict],
    entity_name: str,
    *,
    console: Console | None = None,
) -> None:
    c = console or _console
    root = Tree(f"({entity_name})\n/")
    path_to_node: dict[str, Tree] = {"/": root}
    folder_id_to_node: dict[int, Tree] = {}

    for folder in sorted(folders, key=lambda f: len(PurePosixPath(f["path"]).parts)):
        path = folder["path"]
        parent_path = str(PurePosixPath(path).parent)
        if parent_path == path:
            parent_path = "/"
        parent_node = path_to_node.get(parent_path, root)
        node = parent_node.add(PurePosixPath(path).name)
        path_to_node[path] = node
        folder_id_to_node[folder["folder_id"]] = node

    for query in queries:
        parent = folder_id_to_node.get(query["folder_id"], root)
        parent.add(f"{query['query_name']} (id: {query['query_id']})")

    c.print(root)


def format_query_text(
    query_text: str,
    *,
    console: Console | None = None,
) -> None:
    c = console or _console
    c.print(query_text)


def format_query_metadata(
    metadata: dict | list,
    *,
    console: Console | None = None,
) -> None:
    c = console or _console
    c.print_json(data=metadata)


def format_lines(
    lines: list[str],
    *,
    console: Console | None = None,
) -> None:
    c = console or _console
    for line in lines:
        c.print(line)


def format_alert_queries(
    queries: list[dict],
    folders: list[dict],
    *,
    console: Console | None = None,
) -> None:
    c = console or _console
    folder_map = {f["folder_id"]: f["path"] for f in folders}
    table = Table(show_header=True)
    table.add_column("ID")
    table.add_column("Path")
    for q in queries:
        folder_path = folder_map.get(q["folder_id"], "?")
        path = f"{folder_path}/{q['query_name']}"
        table.add_row(str(q["query_id"]), path)
    c.print(table)


def format_schema(
    schema: dict,
    network: str | None = None,
    table_filter: str | None = None,
    *,
    console: Console | None = None,
) -> None:
    c = console or _console
    for net, tables in sorted(schema.items()):
        if network and net != network:
            continue
        matching = [
            t
            for t in tables
            if not table_filter or table_filter.lower() in t["name"].lower()
        ]
        if not matching:
            continue
        c.print(f"\n[bold]{net}[/bold]")
        for t in sorted(matching, key=lambda x: x["name"]):
            cols = ", ".join(
                f"{col['column_name']} {col['column_type']}" for col in t["columns"]
            )
            c.print(f"  [cyan]{t['name']}[/cyan]  ({cols})")
            for idx in t.get("indices") or []:
                c.print(
                    f"    [dim]index {idx['index_name']}: {idx['index_definition']}[/dim]"
                )


def format_macros(
    macros: dict,
    *,
    console: Console | None = None,
) -> None:
    c = console or _console
    for name in sorted(macros):
        c.print(f"  [cyan]{name}[/cyan]")


def format_logs(
    logs: list[dict],
    *,
    console: Console | None = None,
) -> None:
    c = console or _console
    if not logs:
        c.print("No logs found.")
        return
    table = Table(show_header=True)
    table.add_column("Status")
    table.add_column("Query")
    table.add_column("Started")
    table.add_column("Message")
    for log in logs:
        query = log.get("query") or {}
        name = query.get("query_name") or str(log.get("query_id", ""))
        msg = str(log.get("message") or "")
        table.add_row(
            log.get("status", ""),
            name,
            str(log.get("start_ts", "")),
            _truncate(msg),
        )
    c.print(table)
    last = logs[-1]
    if ts := last.get("start_ts"):
        c.print(f"[dim]Next page: --before {ts}[/dim]")


def format_fired_alerts(
    alerts: list[dict],
    *,
    console: Console | None = None,
) -> None:
    c = console or _console
    if not alerts:
        c.print("No alerts found.")
        return
    table = Table(show_header=True)
    table.add_column("ID")
    table.add_column("Query")
    table.add_column("Time")
    table.add_column("Message")
    for alert in alerts:
        query = alert.get("query") or {}
        name = query.get("query_name") or str(alert.get("query_id", ""))
        msg = str(alert.get("query_message") or "")
        table.add_row(
            str(alert.get("alert_id", "")),
            name,
            str(alert.get("_ts", "")),
            _truncate(msg),
        )
    c.print(table)
    last = alerts[-1]
    if aid := last.get("alert_id"):
        c.print(f"[dim]Next page: --after-id {aid}[/dim]")


def format_query_results(
    results: list[dict],
    *,
    console: Console | None = None,
) -> None:
    c = console or _console
    if not results:
        c.print("No results.")
        return
    headers = list(results[0].keys())
    table = Table(show_header=True)
    for h in headers:
        table.add_column(h)
    for row in results:
        table.add_row(*[str(row.get(h, "")) for h in headers])
    c.print(table)


def format_columns(
    columns: list[dict],
    *,
    console: Console | None = None,
) -> None:
    c = console or _console
    if not columns:
        c.print("No columns.")
        return
    table = Table(show_header=True)
    table.add_column("Column")
    table.add_column("Type")
    for col in columns:
        table.add_row(col.get("column_name", ""), col.get("column_type", ""))
    c.print(table)


def format_webhooks(
    webhooks: list[dict],
    *,
    console: Console | None = None,
) -> None:
    c = console or _console
    if not webhooks:
        c.print("No webhooks.")
        return
    table = Table(show_header=True)
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("URL")
    table.add_column("Description")
    for w in webhooks:
        table.add_row(
            str(w.get("webhook_id", "")),
            str(w.get("name", "")),
            str(w.get("url", "")),
            _truncate(str(w.get("description") or "")),
        )
    c.print(table)


def format_alert_filters(
    filters: list[dict],
    *,
    console: Console | None = None,
) -> None:
    c = console or _console
    if not filters:
        c.print("No alert filters.")
        return
    table = Table(show_header=True)
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Queries")
    table.add_column("Chains")
    for f in filters:
        qids = f.get("query_ids") or []
        cids = f.get("chain_ids") or []
        table.add_row(
            str(f.get("search_id", f.get("id", ""))),
            str(f.get("filter_name", "")),
            ", ".join(str(q) for q in qids),
            ", ".join(str(ci) for ci in cids),
        )
    c.print(table)


def format_query_history(
    history: list[dict],
    *,
    console: Console | None = None,
) -> None:
    c = console or _console
    if not history:
        c.print("No history.")
        return
    table = Table(show_header=True)
    table.add_column("Version")
    table.add_column("Saved")
    table.add_column("Name")
    table.add_column("Network")
    for h in history:
        table.add_row(
            str(h.get("version", "")),
            str(h.get("version_ts", "")),
            str(h.get("query_name", "")),
            str(h.get("default_network") or ""),
        )
    c.print(table)
