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

# widgetConfig.ts:33 CHART_ROWS: a chart reads at most this many rows. The API
# allows the same number on /tsql/query/widget_rows (MAX_WIDGET_ROWS in
# backend/library_api/routers/tsql.py).
CHART_ROWS = 10_000
# backend tsql.py MAX_PAGE_ROWS: the most rows of one /tsql/query/execute_async
# run (a Results page). A table widget reads pages through it.
PAGE_ROWS = 1_000
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
BOOL_KEYS = ("fit", "anomalies", "trend", "correlation", "percent", "horizontal")
ENUM_KEYS: dict[str, tuple[str, ...]] = {
    "timeframe": TIMEFRAMES + _TIMEFRAME_ALIASES,
    "sorting_order": ("ASC", "DESC"),
    "order_by": ("x", "y"),
    "line_style": ("line", "area", "step", "stacked"),
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
                where = f"{key} ({_FLAG_OF[key]})" if key in _FLAG_OF else key
                problems.append(
                    f"{where} must be one of {', '.join(allowed)}, not {value!r}."
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
    if widget_type not in WIDGET_TYPES:
        return []
    notes = []
    if widget_type not in AXIS_TYPES:
        # ChartOptionsFields.tsx:446-451: only the types with axes show the labels.
        notes += [
            f"{key} has no effect: a {widget_type} widget has no axes."
            for key in LABEL_KEYS
            if config.get(key)
        ]
    if (
        widget_type == "line"
        and config.get("percent")
        and config.get("line_style") != "stacked"
    ):
        # option.ts: `percent` applies to stacked bars and stacked areas only.
        notes.append(
            "percent (--percent) has no effect: a line shows shares only with --line-style stacked."
        )
    if (
        widget_type == "line"
        and config.get("line_style") == "stacked"
        and not config.get("series_by")
    ):
        # ChartOptionsFields.tsx: stacked areas need a series column.
        notes.append(
            "line_style stacked needs --series-by: with one series the area is drawn alone."
        )
    return notes + ignored_key_notes(widget_type, config)


# --- the options of each type (ChartOptionsFields.tsx) -----------------------------

# The types that use each option, as ChartOptionsFields.tsx shows its control.
# A key on another type is ignored: a note, not an error, so a saved widget
# that changed its type stays valid. Keep each rule next to its web line.
_OPTION_TYPES: dict[str, tuple[str, ...]] = {
    # ChartOptionsFields.tsx:149-171 (and option.ts:1471-1476 reads them)
    "range_shape": ("range",),
    "low_name": ("range",),
    "high_name": ("range",),
    "open_name": ("range",),
    "close_name": ("range",),
    "q1_name": ("range",),
    "median_name": ("range",),
    "q3_name": ("range",),
    "volume_name": ("range",),  # ChartOptionsFields.tsx:172-178
    "hist_view": ("histogram",),  # ChartOptionsFields.tsx:181-193
    # ChartOptionsFields.tsx:194-210. A linebar is not in the web editor list,
    # but option.ts:400-423 draws its series: it stays valid here.
    "series_by": ("line", "bar", "stackedbar", "linebar", "scatter", "histogram"),
    "color_scale": ("scatter",),  # ChartOptionsFields.tsx:211-224
    "size_by": ("scatter",),  # ChartOptionsFields.tsx:225-231
    "combine": (
        "line",
        "bar",
        "stackedbar",
        "linebar",
    ),  # ChartOptionsFields.tsx:232-253
    "line_style": ("line",),  # ChartOptionsFields.tsx:254-267
    "transform": (
        "line",
        "bar",
        "stackedbar",
        "linebar",
    ),  # ChartOptionsFields.tsx:268-288
    # ChartOptionsFields.tsx:289-314; option.ts:402-404 drops a band on stacked bars.
    "uncertainty": ("line", "bar", "linebar"),
    "band_k": ("line",),  # ChartOptionsFields.tsx:315-322
    "anomalies": ("line",),  # ChartOptionsFields.tsx:323-345
    "anomaly_k": ("line",),
    "trend": ("line",),
    "correlation": ("line",),
    "window": (
        "line",
        "bar",
        "stackedbar",
        "linebar",
    ),  # ChartOptionsFields.tsx:144-145, 346-352
    "lower_name": ("line", "bar", "linebar"),  # ChartOptionsFields.tsx:353-358
    "upper_name": ("line", "bar", "linebar"),
    "stderr_name": ("line", "bar", "linebar"),  # ChartOptionsFields.tsx:359-366
    "scale": (
        "line",
        "bar",
        "linebar",
        "scatter",
        "range",
    ),  # ChartOptionsFields.tsx:367-379
    # ChartOptionsFields.tsx:380-394
    "number_format": (
        "line",
        "bar",
        "stackedbar",
        "linebar",
        "scatter",
        "pie",
        "value",
        "range",
    ),
    "reference_line": (
        "line",
        "bar",
        "stackedbar",
        "linebar",
    ),  # ChartOptionsFields.tsx:395-408
    "reference_label": (
        "line",
        "bar",
        "stackedbar",
        "linebar",
    ),  # ChartOptionsFields.tsx:409-420
    "fit": ("scatter",),  # ChartOptionsFields.tsx:423-432
    "bins": ("histogram",),  # ChartOptionsFields.tsx:433-445
    # VisualizeTab.tsx:688-715 shows them for a value only; WidgetChart.tsx:95-96
    # gives them to the stat tile, and chartSpecOf (widgetConfig.ts:405-454) not.
    # The value tile (VisualizeTab.tsx), and the units of the charts
    # (ChartOptionsFields.tsx "Before each value" / "After each value"; option.ts withUnit).
    "prefix": (
        "value",
        "line",
        "bar",
        "stackedbar",
        "linebar",
        "scatter",
        "pie",
        "range",
    ),
    "suffix": (
        "value",
        "line",
        "bar",
        "stackedbar",
        "linebar",
        "scatter",
        "pie",
        "range",
    ),
    # ChartOptionsFields.tsx "100% stack": stacked bars, and a line with line_style "stacked".
    "percent": ("line", "stackedbar"),
    # ChartOptionsFields.tsx "Horizontal bars"; option.ts onItsSide.
    "horizontal": ("bar", "stackedbar"),
    # VisualizeTab.tsx:664-676: the second Y column of lines and bars.
    "y1_axis_name": ("line", "bar", "stackedbar", "linebar"),
    # widgetConfig.ts:48 Y_ORDER_TYPES and :75 orderChoiceOf.
    "order_by": ("line", "bar", "stackedbar", "linebar"),
}


def _types_text(types: Sequence[str]) -> str:
    return ", ".join(types)


def ignored_key_notes(widget_type: str, config: Mapping[str, Any]) -> list[str]:
    """One note for each key that the web app ignores on this widget type,
    and for each value that only another type uses (ChartOptionsFields.tsx)."""
    notes: list[str] = []

    def ignored(key: str, why: str) -> None:
        notes.append(f"{key} is ignored for a {widget_type} widget: {why}.")

    for key, types in _OPTION_TYPES.items():
        if config.get(key) is not None and widget_type not in types:
            ignored(
                key,
                f"only {_types_text(types)} {'uses' if len(types) == 1 else 'use'} it",
            )
    if widget_type not in CHART_TYPES:
        return notes

    transform = config.get("transform") or "none"
    uncertainty = config.get("uncertainty") or "none"
    series_by = config.get("series_by")
    # ChartOptionsFields.tsx:279-281 offers it for a line; option.ts:455-456
    # draws no transform on another type.
    if transform == "bollinger" and widget_type in ("bar", "stackedbar", "linebar"):
        ignored("transform bollinger", "only line uses it")
    if uncertainty == "quantiles" and widget_type in ("bar", "linebar"):
        # ChartOptionsFields.tsx:300-302 offers it for a line only.
        ignored("uncertainty quantiles", "only line offers it")
    if (
        widget_type == "line"
        and config.get("band_k") is not None
        and transform != "bollinger"
    ):
        # ChartOptionsFields.tsx:315-322
        ignored("band_k", "it needs transform bollinger")
    anomalies_on = widget_type == "line" and config.get("anomalies") is not False
    if (
        widget_type == "line"
        and config.get("anomaly_k") is not None
        and not anomalies_on
    ):
        # ChartOptionsFields.tsx:328-334
        ignored("anomaly_k", "anomalies is false")
    # ChartOptionsFields.tsx:143-145: the rolling transforms, the unusual points
    # and the rolling correlation read the window.
    rolling = transform in ("mean", "ewma", "bollinger")
    uses_window = (
        rolling
        or anomalies_on
        or (widget_type == "line" and bool(config.get("correlation")))
    )
    in_window_types = widget_type in _OPTION_TYPES["window"]
    if config.get("window") is not None and in_window_types and not uses_window:
        ignored(
            "window",
            "only a rolling transform, the anomalies or the correlation use it",
        )
    if widget_type in _OPTION_TYPES["lower_name"]:
        # ChartOptionsFields.tsx:353-366: the band columns of uncertainty.
        for key in ("lower_name", "upper_name"):
            if config.get(key) and uncertainty != "columns":
                ignored(key, "it needs uncertainty columns")
        if config.get("stderr_name") and uncertainty != "stderr":
            ignored("stderr_name", "it needs uncertainty stderr")
    if config.get("reference_label") and not config.get("reference_line"):
        # ChartOptionsFields.tsx:409-420
        ignored("reference_label", "it needs reference_line")
    if widget_type == "scatter" and config.get("color_scale") and not series_by:
        # ChartOptionsFields.tsx:211-213
        ignored("color_scale", "it needs series_by")
    if widget_type == "histogram" and series_by and config.get("hist_view") != "ecdf":
        # ChartOptionsFields.tsx:194-195: a histogram has series in its ECDF view only.
        ignored("series_by", "only hist_view ecdf uses it")
    if widget_type == "range":
        shape = config.get("range_shape") or "candle"
        if config.get("volume_name") and shape != "candle":
            # ChartOptionsFields.tsx:172-178; option.ts:1651
            notes.append("The volume panel shows under candles only.")
    if config.get("y1_axis_name") and series_by and widget_type in Y_ORDER_TYPES:
        # option.ts:400: with series_by, the chart draws y_axis_name only.
        ignored("y1_axis_name", "series_by is set, so the chart draws y_axis_name only")
    return notes


def draw_problems(widget_type: str, config: Mapping[str, Any]) -> list[str]:
    """The configs that the web app saves but cannot draw as asked. Each one
    blocks a save, as a missing axis does."""
    problems: list[str] = []
    if widget_type not in _OPTION_TYPES["uncertainty"]:
        return problems
    uncertainty = config.get("uncertainty")
    # data.ts:150: a band from columns needs both columns; without them, no band.
    if uncertainty == "columns" and not (
        config.get("lower_name") and config.get("upper_name")
    ):
        problems.append(
            "uncertainty columns needs lower_name and upper_name (the band's columns)."
        )
    # data.ts:161: a band from a standard error needs its column.
    if uncertainty == "stderr" and not config.get("stderr_name"):
        problems.append(
            "uncertainty stderr needs stderr_name (the standard error column)."
        )
    return problems


def column_type_notes(
    widget_type: str, config: Mapping[str, Any], columns: Sequence[Mapping[str, str]]
) -> tuple[list[str], list[str]]:
    """What the column types say before the query runs: the kind of the X
    axis (facts), and each column that must hold numbers but has another type
    (notes). The chart reads a number from a text value too (data.ts:37-45
    toNumber), so a text column is a note, not a problem."""
    types = {c["name"]: c["type"] for c in columns}
    facts: list[str] = []
    notes: list[str] = []
    x = config.get("x_axis_name")
    x_type = types.get(x) if isinstance(x, str) else None
    if (
        x_type
        and widget_type in CHART_TYPES
        and widget_type not in ("pie", "histogram")
    ):
        if is_time_column(x_type):
            kind = "time"
        elif _NUMBER_TYPE.match(x_type):
            kind = "number"
        else:
            kind = "category"
        # option.ts:517: bars put every X on a category axis.
        drawn = (
            ", drawn as categories"
            if widget_type in BAR_TYPES and kind != "category"
            else ""
        )
        facts.append(f"x: {x} ({x_type}): {kind} axis{drawn}")
    by_y = config.get("order_by") == "y" and widget_type in Y_ORDER_TYPES
    # widgetConfig.ts:56-61 yOrderApplies; option.ts:450
    if by_y and x_type and not y_order_applies(widget_type, x_type):
        notes.append(
            f"order_by y has no effect: {x} is a time or a number, so the points keep the order of {x}."
        )
    for key in _numeric_keys(widget_type, config):
        name = config.get(key)
        column_type = types.get(name) if isinstance(name, str) else None
        if column_type and not _NUMBER_TYPE.match(column_type):
            notes.append(
                f"{key} {name!r} is {column_type}, not a number type: the chart draws only the values that read as numbers."
            )
    return facts, notes


# option.ts:398: the bar types.
BAR_TYPES = ("bar", "stackedbar", "linebar")


def _numeric_keys(widget_type: str, config: Mapping[str, Any]) -> list[str]:
    """The config keys whose column the chart reads as numbers."""
    if widget_type in Y_ORDER_TYPES:
        # data.ts:191: "count" counts the rows with any value.
        keys = [] if config.get("combine") == "count" else ["y_axis_name"]
        if not config.get("series_by") and config.get("combine") != "count":
            keys.append("y1_axis_name")  # option.ts:400
        uncertainty = config.get("uncertainty")
        if uncertainty == "columns":
            keys += ["lower_name", "upper_name"]  # data.ts:150-156
        if uncertainty == "stderr":
            keys.append("stderr_name")  # data.ts:161-164
        return keys
    if widget_type == "scatter":
        keys = ["y_axis_name", "size_by"]  # option.ts:1113, 1119
        if config.get("color_scale") == "scale":
            keys.append("series_by")  # option.ts:1118
        return keys
    if widget_type == "histogram":
        return ["x_axis_name"]  # option.ts:1379-1381, 1688-1693
    if widget_type in ("pie", "value"):
        return ["y_axis_name"]  # option.ts:986; StatTile.tsx:33
    if widget_type == "range":
        shape = config.get("range_shape") or "candle"
        keys = [RANGE_KEYS[p] for p in RANGE_COLUMNS.get(shape, ())]
        return [*keys, "volume_name"]  # option.ts:1489, 1495
    return []


# The chart palette has this many colours (palette.ts SERIES_LIGHT). With more
# series_by values, data.ts keeps the largest MAX_SERIES - 1 series and adds the
# rest together into one "Other" series.
MAX_SERIES = 8
# option.ts:1143-1145: a scatter colours at most 3 groups (the 2 largest and
# "Other"): any two dots can touch, and only 3 palette slots pass for all pairs.
MAX_SCATTER_GROUPS = 3
# option.ts:991-997: a pie draws at most 6 slices (the 5 largest and "Other").
MAX_PIE_SLICES = 6


def series_notes(
    widget_type: str, config: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]
) -> list[str]:
    """A note when the rows have more series_by values than the chart draws."""
    column = config.get("series_by")
    if not column or widget_type not in AXIS_TYPES or widget_type == "range":
        return []
    if widget_type == "histogram" and config.get("hist_view") != "ecdf":
        return []
    values = {
        str(row.get(column) if row.get(column) is not None else "(empty)")
        for row in rows
    }
    if widget_type == "scatter":
        if config.get("color_scale") == "scale" or len(values) <= MAX_SCATTER_GROUPS:
            return []
        # option.ts:1143-1145: a scatter keeps 2 groups and puts the rest in "Other".
        kept = MAX_SCATTER_GROUPS - 1
        return [
            f"series_by {column!r} has {len(values)} values in these rows. A scatter colours "
            f"the {kept} largest groups and puts the other {len(values) - kept} together "
            f"as one grey 'Other' group. Filter the rows, or use color_scale scale for a number."
        ]
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
    "combine": "--combine",
    "order_by": "--order-by",
    "sorting_order": "--sorting-order",
    "scale": "--scale",
    "number_format": "--number-format",
    "prefix": "--prefix",
    "suffix": "--suffix",
    "decimals": "--decimals",
    "line_style": "--line-style",
    "percent": "--percent",
    "horizontal": "--horizontal",
    "transform": "--transform",
    "timeframe": "--timeframe",
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
