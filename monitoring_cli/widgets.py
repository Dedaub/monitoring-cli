"""The widget rules of the web app, in Python.

The Visualize tab and the dashboard decide what a chart needs, which columns a
query lost, and the SQL that reads a widget's rows. The CLI must give the same
answers, so this module copies those rules from the frontend
(`watchdog-components/txMonitor/widgets/widgetConfig.ts`, `saveWidget.ts`,
`ChartOptionsFields.tsx`, `charts/kit/option.ts`). Keep the names close to the
TypeScript ones, so a change there is easy to find here.

The API stores a widget config with snake_case keys: the web client converts
the camelCase keys of `Widget.tsx` with `camelToSnake` before it sends them.
"""

from __future__ import annotations

import datetime
import difflib
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any, cast
from urllib.parse import urlsplit

# --- types and sizes ---------------------------------------------------------

# charts/kit/option.ts CHART_TYPES: the types the chart kit draws.
CHART_TYPES = (
    "line",
    "bar",
    "stackedbar",
    "linebar",
    "pie",
    "scatter",
    "histogram",
    "range",
)
# The backend's WidgetType: the chart types plus a table and a single value.
WIDGET_TYPES = (*CHART_TYPES, "table", "value")
# ChartOptionsFields.tsx AXIS_TYPES: the types with an X and a Y axis.
AXIS_TYPES = ("line", "bar", "stackedbar", "linebar", "scatter", "histogram", "range")
LABEL_MAX = 120

# widgetConfig.ts CHART_ROWS: a chart reads at most this many rows.
CHART_ROWS = 500
# BusinessIntelligenceWidget.tsx PAGE: a table widget reads one page of rows.
TABLE_ROWS = 25

# widgetConfig.ts TIMEFRAME_OPTIONS. utils.ts timeframeToTimestart also reads
# the older aliases, so a saved widget with one of them stays valid.
TIMEFRAMES = ("24h", "7d", "30d", "60d")
_TIMEFRAME_ALIASES = ("1d", "1w", "1m", "2m", "1y")

# VisualizeTab.tsx DEFAULT_CONFIG: what a new widget starts with in the web app.
DEFAULT_CONFIG: dict[str, Any] = {
    "timeframe": "30d",
    "sorting_order": "ASC",
    "decimals": "2",
}

# The backend's WidgetCategory values. widgets/modals/utils.ts names
# MATERIALIZED "BUSINESS_INTELLIGENCE".
CATEGORY_VIEW = "VIEW"
CATEGORY_MATERIALIZED = "MATERIALIZED"

# --- config keys ---------------------------------------------------------------

# charts/kit/option.ts RANGE_COLUMNS and widgetConfig.ts RANGE_KEYS / RANGE_LABELS.
RANGE_COLUMNS: dict[str, tuple[str, ...]] = {
    "range": ("low", "high"),
    "candle": ("open", "high", "low", "close"),
    "box": ("low", "q1", "median", "q3", "high"),
}
RANGE_KEYS = {
    "low": "low_name",
    "high": "high_name",
    "open": "open_name",
    "close": "close_name",
    "q1": "q1_name",
    "median": "median_name",
    "q3": "q3_name",
}
RANGE_LABELS: dict[str, dict[str, str]] = {
    "range": {"low": "Low column", "high": "High column"},
    "candle": {
        "open": "Open column",
        "high": "High column",
        "low": "Low column",
        "close": "Close column",
    },
    "box": {
        "low": "Minimum column",
        "q1": "Lower quartile (q1) column",
        "median": "Median column",
        "q3": "Upper quartile (q3) column",
        "high": "Maximum column",
    },
}

# Widget.tsx: every config key, by the kind of value it holds.
COLUMN_KEYS = (
    "x_axis_name",
    "y_axis_name",
    "y1_axis_name",
    "series_by",
    "lower_name",
    "upper_name",
    "stderr_name",
    "low_name",
    "high_name",
    "open_name",
    "close_name",
    "q1_name",
    "median_name",
    "q3_name",
    "volume_name",
    "size_by",
)
TEXT_KEYS = ("x_label", "y_label", "prefix", "suffix", "reference_label")
LABEL_KEYS = ("x_label", "y_label")
# The editors save these as text, but some saved widgets hold a number.
NUMBER_KEYS = ("decimals", "reference_line", "bins", "window", "band_k", "anomaly_k")
BOOL_KEYS = ("fit", "anomalies", "trend", "correlation")
ENUM_KEYS: dict[str, tuple[str, ...]] = {
    "timeframe": TIMEFRAMES + _TIMEFRAME_ALIASES,
    "sorting_order": ("ASC", "DESC"),
    "order_by": ("x", "y"),
    "line_style": ("line", "area", "step"),
    "transform": ("none", "ma7", "mean", "ewma", "bollinger", "cum", "index", "pct"),
    "uncertainty": (
        "none",
        "sd",
        "ci95",
        "minmax",
        "quantiles",
        "columns",
        "stderr",
    ),
    "scale": ("linear", "log"),
    "number_format": ("compact", "full", "currency", "percent"),
    "hist_view": ("counts", "ecdf"),
    "range_shape": ("range", "candle", "box"),
    "combine": ("sum", "mean", "median", "min", "max", "count"),
    "color_scale": ("groups", "scale"),
}
CONFIG_KEYS = frozenset(
    (*COLUMN_KEYS, *TEXT_KEYS, *NUMBER_KEYS, *BOOL_KEYS, *ENUM_KEYS)
)


def camel_to_snake(name: str) -> str:
    """The web client's `camelToSnake`: xAxisName -> x_axis_name, y1AxisName -> y1_axis_name."""
    return re.sub(r"([a-z0-9_])([A-Z])", r"\1_\2", name).lower()


def normalize_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """The config with snake_case keys, as the API stores it."""
    return {camel_to_snake(str(k)): v for k, v in config.items()}


def clean_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """saveWidget.ts `cleanConfig`: a saved widget holds only what it uses."""
    return {
        k: v for k, v in config.items() if v is not None and v != "" and v != "None"
    }


# --- checks ----------------------------------------------------------------------


def _is_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int | float):
        return math.isfinite(value)
    if isinstance(value, str) and value.strip():
        try:
            return math.isfinite(float(value))
        except ValueError:
            return False
    return False


def config_problems(widget_type: str, config: Mapping[str, Any]) -> list[str]:
    """Each key or value that the web app does not know, as one sentence.
    `config` has snake_case keys."""
    problems: list[str] = []
    if widget_type not in WIDGET_TYPES:
        problems.append(
            f"Unknown widget type {widget_type!r}. Use one of: {', '.join(WIDGET_TYPES)}."
        )
    for key, value in config.items():
        if key not in CONFIG_KEYS:
            close = difflib.get_close_matches(key, sorted(CONFIG_KEYS), n=1)
            hint = f" Did you mean {close[0]!r}?" if close else ""
            problems.append(f"Unknown config key {key!r}.{hint}")
        elif key in ENUM_KEYS:
            if value not in ENUM_KEYS[key]:
                allowed = ENUM_KEYS[key] if key != "timeframe" else TIMEFRAMES
                problems.append(
                    f"{key} must be one of {', '.join(allowed)}, not {value!r}."
                )
        elif key in COLUMN_KEYS:
            if not isinstance(value, str) or not value:
                problems.append(f"{key} must be a column name, not {value!r}.")
        elif key in TEXT_KEYS:
            if not isinstance(value, str):
                problems.append(f"{key} must be text, not {value!r}.")
            elif key in LABEL_KEYS and len(value) > LABEL_MAX:
                problems.append(
                    f"{key} has {len(value)} characters. The maximum is {LABEL_MAX}."
                )
        elif key in NUMBER_KEYS:
            if not _is_number(value):
                problems.append(f"{key} must be a number, not {value!r}.")
        elif key in BOOL_KEYS and not isinstance(value, bool):
            problems.append(f"{key} must be true or false, not {value!r}.")
    return problems


def config_notes(widget_type: str, config: Mapping[str, Any]) -> list[str]:
    """Keys that are valid but that this type does not show. Not an error."""
    if widget_type in AXIS_TYPES or widget_type not in WIDGET_TYPES:
        return []
    return [
        f"{key} has no effect: a {widget_type} widget has no axes."
        for key in LABEL_KEYS
        if config.get(key)
    ]


# The chart palette has this many colours (palette.ts SERIES_LIGHT). With more
# series_by values, data.ts keeps the largest MAX_SERIES - 1 series and adds the
# rest together into one "Other" series.
MAX_SERIES = 8


def series_notes(
    widget_type: str, config: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]
) -> list[str]:
    """A note when the rows have more series_by values than the chart draws."""
    column = config.get("series_by")
    if not column or widget_type not in AXIS_TYPES:
        return []
    values = {
        str(row.get(column) if row.get(column) is not None else "(empty)")
        for row in rows
    }
    if len(values) <= MAX_SERIES:
        return []
    kept = MAX_SERIES - 1
    return [
        f"series_by {column!r} has {len(values)} values in these rows. The chart draws "
        f"the {kept} largest and adds the other {len(values) - kept} together as one "
        f"'Other' series. That sum is wrong for a rate or a percentage: split the rows "
        f"into two queries, or filter them, so that each chart has at most {MAX_SERIES}."
    ]


# The flag that sets each key, for the messages.
_FLAG_OF = {
    "x_axis_name": "--x",
    "y_axis_name": "--y",
    "y1_axis_name": "--y1",
    "series_by": "--series-by",
}


def _flag(key: str) -> str:
    return f" ({_FLAG_OF[key]})" if key in _FLAG_OF else f" (config key {key})"


def missing_axis(widget_type: str, config: Mapping[str, Any]) -> str | None:
    """widgetConfig.ts `missingAxis`: what the chart type still needs, or None."""
    x = _flag("x_axis_name")
    y = _flag("y_axis_name")
    if widget_type in ("line", "bar", "stackedbar", "linebar"):
        if not config.get("x_axis_name"):
            return f"Choose the X-axis column{x}."
        if not config.get("y_axis_name"):
            return f"Choose the Y-axis column{y}."
        return None
    if widget_type == "scatter":
        if not config.get("x_axis_name"):
            return f"Choose the X column{x}."
        if not config.get("y_axis_name"):
            return f"Choose the Y column{y}."
        return None
    if widget_type == "histogram":
        return None if config.get("x_axis_name") else f"Choose the column to bin{x}."
    if widget_type == "pie":
        return None if config.get("x_axis_name") else f"Choose the column to count{x}."
    if widget_type == "range":
        if not config.get("x_axis_name"):
            return f"Choose the X-axis column{x}."
        shape = config.get("range_shape") or "candle"
        if shape not in RANGE_COLUMNS:
            return None
        for part in RANGE_COLUMNS[shape]:
            key = RANGE_KEYS[part]
            if not config.get(key):
                return f"Choose the {RANGE_LABELS[shape][part].lower()}{_flag(key)}."
        return None
    if widget_type == "value":
        return None if config.get("y_axis_name") else f"Choose the column to show{y}."
    return None


def columns_not_in_query(
    config: Mapping[str, Any], columns: list[str], widget_type: str | None = None
) -> list[str]:
    """widgetConfig.ts `columnsNotInQuery`: the columns that the config names
    and the query does not have. Empty when the columns are not known."""
    if not columns:
        return []
    names: list[Any] = [
        config.get("x_axis_name"),
        config.get("y_axis_name"),
        config.get("y1_axis_name"),
        config.get("series_by"),
        config.get("lower_name"),
        config.get("upper_name"),
        config.get("stderr_name"),
        config.get("size_by") if widget_type == "scatter" else None,
    ]
    if widget_type == "range":
        shape = config.get("range_shape") or "candle"
        names += [config.get(RANGE_KEYS[p]) for p in RANGE_COLUMNS.get(shape, ())]
        names.append(config.get("volume_name"))
    seen: list[str] = []
    for name in names:
        if isinstance(name, str) and name and name != "None" and name not in seen:
            seen.append(name)
    return [name for name in seen if name not in columns]


# --- the SQL that reads a widget's rows --------------------------------------------

# The backend renders the SQL as a Jinja template before it parses it: a brace in
# a name could open a Jinja expression that quoting does not stop.
_JINJA = re.compile(r"[{}]")
# The engine reads the network line only at the very start of the SQL.
_NETWORK_LINE = re.compile(r'--#[ ]*default_network[ ]*=[ ]*"([a-zA-Z0-9_]+)"')
_NUMBER_TYPE = re.compile(
    r"(smallint|integer|bigint|numeric|decimal|real|double precision)"
)
# widgetConfig.ts Y_ORDER_TYPES: the types that can put X in the order of Y.
Y_ORDER_TYPES = ("line", "bar", "stackedbar", "linebar")


def is_time_column(column_type: str) -> bool:
    return "timestamp" in column_type or column_type == "date"


def y_order_applies(widget_type: str, x_type: str | None) -> bool:
    """widgetConfig.ts `yOrderApplies`."""
    if widget_type not in Y_ORDER_TYPES:
        return False
    if not x_type:
        return True
    if is_time_column(x_type):
        return False
    return widget_type != "line" or not _NUMBER_TYPE.match(x_type)


def quote_identifier(name: str) -> str:
    """A column name as a quoted SQL identifier: keeps its case and its spaces."""
    if _JINJA.search(name):
        raise ValueError(f"The column name {json.dumps(name)} has a brace.")
    return '"' + name.replace('"', '""') + '"'


def subquery_body(text: str) -> str | None:
    """widgetConfig.ts `subqueryBody`: the query text as the body of a subquery,
    or None when nothing is left. A final ";" goes, also with a comment after
    it; a final line comment alone stays."""
    body = text
    while True:
        before = body
        body = body.rstrip()
        body = re.sub(r"\{#[\s\S]*?#\}\Z", "", body, count=1)
        body = re.sub(r"/\*(?:(?!/\*)[\s\S])*?\*/\Z", "", body, count=1)
        body = re.sub(r";[ \t]*(?:--[^\n]*)?\Z", "", body, count=1)
        if body == before:
            break
    code = re.sub(r"--[^\n]*", "", body).strip()
    return body if code else None


def _js_string(value: str) -> str:
    """JSON.stringify of a string."""
    return json.dumps(value, ensure_ascii=False)


def _iso(moment: datetime.datetime) -> str:
    """Date.prototype.toISOString: UTC with milliseconds."""
    utc = moment.astimezone(datetime.UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def widget_rows_sql(
    *,
    table: str,
    query_text: str | None = None,
    network: str | None = None,
    columns: list[str] | None = None,
    time_column: str | None = None,
    since: datetime.datetime | None = None,
    order_column: str | None = None,
    sorting_order: str | None = None,
    keep_first: bool = False,
    chart_limit: int | None = None,
) -> str:
    """widgetConfig.ts `widgetRowsSql`: the SQL that reads a widget's rows from
    the table of its query (`ref()`), or from the query text when `query_text`
    is given. A chart reads the newest `chart_limit` rows by its order column,
    then sorts them; a table sorts all rows."""

    def usable(name: str | None) -> bool:
        # A name that the query returns twice is ambiguous in WHERE and ORDER BY.
        return (
            bool(name)
            and not _JINJA.search(name or "")
            and (not columns or columns.count(name) == 1)
        )

    body = None if query_text is None else subquery_body(query_text)
    source = (
        f"(\n{body}\n)"
        if body is not None
        else f"{{{{ ref(table={_js_string(table)}) }}}}"
    )
    sql = f"SELECT * FROM {source} r"
    if time_column and usable(time_column) and since:
        sql += f"\nWHERE r.{quote_identifier(time_column)} > '{_iso(since)}'"
    if order_column and usable(order_column) and sorting_order:
        order = "DESC" if sorting_order == "DESC" else "ASC"
        column = quote_identifier(order_column)
        if chart_limit and keep_first:
            sql = (
                f"WITH q AS ({sql}\nORDER BY r.{column} {order} NULLS LAST\nLIMIT {chart_limit})\n"
                f"SELECT * FROM q ORDER BY q.{column} {order} NULLS LAST"
            )
        elif chart_limit:
            reverse = "DESC" if order == "ASC" else "ASC"
            sql = (
                f"WITH q AS ({sql}\nORDER BY r.{column} {reverse}\nLIMIT {chart_limit})\n"
                f"SELECT * FROM q ORDER BY q.{column} {order}"
            )
        else:
            sql += f"\nORDER BY r.{column} {order}"
    # The text's own network line wins, as when the Results tab runs the text.
    net = network
    if body is not None and query_text is not None:
        match = _NETWORK_LINE.match(query_text)
        if match:
            net = match.group(1)
    if net:
        sql = f"--#default_network={_js_string(net)}\n{sql}"
    return sql


def widget_rows_sqls(
    read: dict[str, Any], query_text: str | None
) -> tuple[str, str | None]:
    """widgetConfig.ts `widgetRowsSqls`: the SQL through `ref()`, and over the
    query text (None when the text is empty)."""
    ref = widget_rows_sql(**read)
    if query_text is None or subquery_body(query_text) is None:
        return ref, None
    return ref, widget_rows_sql(**read, query_text=query_text)


def _shift_months(moment: datetime.datetime, months: int) -> datetime.datetime:
    """Date.setMonth / setFullYear: the same day, and a day past the end of the
    month runs on into the next month (31 March - 1 month = 3 March)."""
    index = moment.year * 12 + moment.month - 1 + months
    first = moment.replace(year=index // 12, month=index % 12 + 1, day=1)
    return first + datetime.timedelta(days=moment.day - 1)


def timeframe_start(
    timeframe: str, now: datetime.datetime | None = None
) -> datetime.datetime:
    """utils.ts `timeframeToTimestart`. It counts in local wall time, as the
    browser does. An unknown timeframe gives `now`."""
    local = (now or datetime.datetime.now(datetime.UTC)).astimezone()
    wall = local.replace(tzinfo=None)
    if timeframe in ("24h", "1d"):
        wall -= datetime.timedelta(days=1)
    elif timeframe in ("7d", "1w"):
        wall -= datetime.timedelta(days=7)
    elif timeframe in ("30d", "1m"):
        wall = _shift_months(wall, -1)
    elif timeframe in ("60d", "2m"):
        wall -= datetime.timedelta(days=60)
    elif timeframe == "1y":
        wall = _shift_months(wall, -12)
    return wall.astimezone(datetime.UTC)


def widget_sqls_of(
    *,
    query: Mapping[str, Any],
    columns: list[dict[str, str]],
    widget_type: str,
    config: Mapping[str, Any],
    timeframe: str | None = None,
    now: datetime.datetime | None = None,
) -> tuple[str, str | None]:
    """widgetConfig.ts `widgetSqlsOf`: the SQL of a widget in its two forms.
    `columns` are {"name", "type"} pairs from the query metadata."""
    x = config.get("x_axis_name")
    y = config.get("y_axis_name")
    sorting = config.get("sorting_order")
    x_type = next((c["type"] for c in columns if c["name"] == x), None)
    by_y = (
        config.get("order_by") == "y"
        and bool(y)
        and y_order_applies(widget_type, x_type)
    )
    owner = (query.get("owner") or {}).get("username")
    table = (f"{owner}::" if owner else "") + str(query.get("query_name", ""))
    read: dict[str, Any] = {
        # The owner's query: a viewer's own query of the same name must not answer for it.
        "table": table,
        "network": query.get("default_network"),
        "columns": [c["name"] for c in columns],
        "time_column": next(
            (c["name"] for c in columns if is_time_column(c["type"])), None
        ),
        "since": timeframe_start(timeframe, now) if timeframe else None,
        "order_column": y if by_y else x,
        # The Y order always has a direction: smallest first, as the chart draws it.
        "sorting_order": "ASC" if by_y and sorting != "DESC" else sorting,
        "keep_first": by_y,
        "chart_limit": None if widget_type == "table" else CHART_ROWS,
    }
    return widget_rows_sqls(read, query.get("query_text"))


# widgetRows.ts NOT_REFERABLE: the engine's error when `ref()` does not find the
# query (it has no run settings on Ethereum, or the viewer may not read it).
NOT_REFERABLE = re.compile(
    r"you requested does not exist, or has not been shared with you"
)


# --- saving ------------------------------------------------------------------------


def default_widget_size(widget_type: str) -> dict[str, int]:
    """widgetConfig.ts `defaultWidgetSize` on the 12-column grid."""
    if widget_type == "table":
        return {"width": 8, "height": 6}
    if widget_type == "value":
        return {"width": 4, "height": 2}
    if widget_type == "range":
        return {"width": 6, "height": 5}
    return {"width": 4, "height": 4}


def chart_category(query: Mapping[str, Any], notify: bool) -> str:
    """The category the Visualize tab saves a chart or results table with: a
    query with notifications or a schedule reads its materialized table
    (`chartCategory` turns ALERT into MATERIALIZED), any other one a view."""
    if notify or query.get("is_scheduled"):
        return CATEGORY_MATERIALIZED
    return CATEGORY_VIEW


# --- layout ------------------------------------------------------------------------

GRID_COLUMNS = 12
MAX_WIDGET_HEIGHT = 40
MAX_INT4 = 2**31 - 1
MAX_LAYOUT_WIDGETS = 500
_LAYOUT_FIELDS = ("widget_id", "x", "y", "width", "height")
_LAYOUT_RANGES = {
    "widget_id": (1, MAX_INT4),
    "x": (0, GRID_COLUMNS - 1),
    "y": (0, MAX_INT4),
    "width": (1, GRID_COLUMNS),
    "height": (1, MAX_WIDGET_HEIGHT),
}


def layout_problems(layout: Any) -> list[str]:
    """The backend's DashboardLayout rules: a list of at most 500 items, each
    {widget_id, x, y, width, height} inside the 12-column grid, each widget once."""
    if not isinstance(layout, list):
        return ["The layout must be a JSON list of {widget_id, x, y, width, height}."]
    problems: list[str] = []
    if len(layout) > MAX_LAYOUT_WIDGETS:
        problems.append(
            f"The layout has {len(layout)} items. The maximum is {MAX_LAYOUT_WIDGETS}."
        )
    seen: set[int] = set()
    for i, raw in enumerate(layout):
        where = f"Item {i}"
        if not isinstance(raw, dict):
            problems.append(f"{where} must be an object.")
            continue
        item = cast(dict[str, Any], raw)
        extra = sorted(set(item) - set(_LAYOUT_FIELDS))
        if extra:
            problems.append(f"{where} has unknown keys: {', '.join(extra)}.")
        ok = True
        for field in _LAYOUT_FIELDS:
            value = item.get(field)
            low, high = _LAYOUT_RANGES[field]
            if isinstance(value, bool) or not isinstance(value, int):
                problems.append(f"{where}: {field} must be an integer.")
                ok = False
            elif not low <= value <= high:
                problems.append(
                    f"{where}: {field} must be from {low} to {high}, not {value}."
                )
                ok = False
        if not ok:
            continue
        if item["x"] + item["width"] > GRID_COLUMNS:
            problems.append(f"{where}: x + width must be at most {GRID_COLUMNS}.")
        if item["widget_id"] in seen:
            problems.append(
                f"{where}: widget {item['widget_id']} occurs more than one time."
            )
        seen.add(item["widget_id"])
    return problems


# --- arrange ----------------------------------------------------------------------

TILE_HEIGHT = 2
CHART_HEIGHT = 4
TALL_CHART_HEIGHT = 5
TABLE_HEIGHT = 6
TILES_PER_ROW = 6
# A time series with many points reads better a little taller.
TALL_TYPES = ("line", "linebar", "range")
# A pie beside another chart: the pie is narrow, the chart is wide.
PIE_WIDTH = 4


def _is_full_width(widget: Mapping[str, Any]) -> bool:
    """A table, or an alerts widget (it shows the alerts of its query as rows)."""
    return widget.get("type") == "table" or widget.get("category") == "ALERT"


def auto_layout(dashboard_widgets: Sequence[Mapping[str, Any]]) -> list[dict[str, int]]:
    """A clean 12-column layout for the widgets of a dashboard, from their types.

    The order of the widgets stays (top to bottom, then left to right):
    - value tiles go first, at most 6 in a row: 1-3 tiles are 4 wide, 4 are 3
      wide, 5-6 are 2 wide;
    - the charts follow in pairs, 6 and 6 wide; a pie beside another chart is
      4 wide and the chart is 8 wide; a chart alone in its row is 12 wide (a pie
      alone is 6 wide);
    - tables and alerts widgets go last, 12 wide.
    """
    ordered = sorted(
        dashboard_widgets,
        key=lambda w: (w.get("y") or 0, w.get("x") or 0, w.get("widget_id") or 0),
    )
    tiles = [w for w in ordered if w.get("type") == "value" and not _is_full_width(w)]
    wide = [w for w in ordered if _is_full_width(w)]
    charts = [w for w in ordered if w not in tiles and w not in wide]

    layout: list[dict[str, int]] = []
    y = 0

    def place(widget: Mapping[str, Any], x: int, width: int, height: int) -> None:
        layout.append(
            {
                "widget_id": int(widget["widget_id"]),
                "x": x,
                "y": y,
                "width": width,
                "height": height,
            }
        )

    for start in range(0, len(tiles), TILES_PER_ROW):
        row = tiles[start : start + TILES_PER_ROW]
        width = max(2, min(4, GRID_COLUMNS // len(row)))
        for i, widget in enumerate(row):
            place(widget, i * width, width, TILE_HEIGHT)
        y += TILE_HEIGHT

    for start in range(0, len(charts), 2):
        pair = charts[start : start + 2]
        pies = [w.get("type") == "pie" for w in pair]
        if len(pair) == 1:
            widths = [GRID_COLUMNS // 2 if pies[0] else GRID_COLUMNS]
        elif pies.count(True) == 1:
            widths = [PIE_WIDTH if pie else GRID_COLUMNS - PIE_WIDTH for pie in pies]
        else:
            widths = [GRID_COLUMNS // 2, GRID_COLUMNS // 2]
        tall = any(w.get("type") in TALL_TYPES for w in pair)
        height = TALL_CHART_HEIGHT if tall else CHART_HEIGHT
        x = 0
        for widget, width in zip(pair, widths, strict=True):
            place(widget, x, width, height)
            x += width
        y += height

    for widget in wide:
        place(widget, 0, GRID_COLUMNS, TABLE_HEIGHT)
        y += TABLE_HEIGHT
    return layout


# --- links -------------------------------------------------------------------------

DEFAULT_APP_URL = "https://app.dedaub.com"


def app_url(api_base: str) -> str:
    """The web app that goes with an API base URL. Production is api -> app;
    staging is st-api -> st-watchdog and st2.api -> st2.watchdog. Another host
    (a local backend) gives its own origin."""
    parts = urlsplit(api_base)
    host = parts.hostname or ""
    scheme = parts.scheme or "https"
    if host == "api.dedaub.com":
        return DEFAULT_APP_URL
    labels = host.split(".")
    if host.endswith(".dedaub.com"):
        if labels[0] == "api":
            labels[0] = "app"
        elif labels[0].endswith("-api"):
            labels[0] = labels[0][: -len("-api")] + "-watchdog"
        elif len(labels) > 3 and labels[1] == "api":
            labels[1] = "watchdog"
        return f"{scheme}://{'.'.join(labels)}"
    origin = f"{scheme}://{parts.netloc}" if parts.netloc else DEFAULT_APP_URL
    return origin


def widget_link(api_base: str, widget_id: int) -> str:
    return f"{app_url(api_base)}/widget/{widget_id}"


def dashboard_link(api_base: str, dashboard_id: int) -> str:
    return f"{app_url(api_base)}/dashboard/{dashboard_id}"
