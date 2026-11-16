"""What a chart draws from its rows: the web chart kit, in Python.

The dashboard turns a widget's rows into series in
`watchdog-components/charts/kit/data.ts`, and draws them with the notes of
`charts/kit/option.ts`. This module counts the same things (the kind of the X
axis, the X values, the series, the rows that are not drawn) and gives the
same notes, so that `preview-widget` can tell an agent what the chart will
show without a browser. Each rule names the web file and line that it copies:
keep the two in step.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from monitoring_cli import widgets

Row = Mapping[str, Any]
XKey = float | str

# option.ts:396-398: the types that buildOption draws on an X and a Y axis.
Y_AXIS_TYPES = ("line", "bar", "stackedbar", "linebar")

# --- values (data.ts) ---------------------------------------------------------

# JavaScript `Number(text)` reads a decimal, an exponent, or a 0x / 0o / 0b
# integer. It does not read "1_000" (Python float does).
_JS_DECIMAL = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
_JS_RADIX = re.compile(r"0(?:[xX][0-9a-fA-F]+|[oO][0-7]+|[bB][01]+)")


def to_number(value: Any) -> float | None:
    """data.ts:37-45 `toNumber`: a finite number, or None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, str) and value.strip():
        text = value.strip()
        if _JS_DECIMAL.fullmatch(text):
            number = float(text)
            return number if math.isfinite(number) else None
        if _JS_RADIX.fullmatch(text):
            return float(int(text, 0))
    return None


# data.ts:47-48 ISO_DATE, with a group for each part.
_ISO_PARTS = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d+))?)?"
    r"(?:(Z)|([+-])(\d{2}):?(\d{2}))?)?"
)
_DAY_MS = 86_400_000


def _days_from_civil(year: int, month: int) -> int:
    """The days from 1970-01-01 to the first day of the month, for any year
    (also year 0, which Date.parse reads)."""
    y = year - (month <= 2)
    era = y // 400
    yoe = y - era * 400
    mp = (month + 9) % 12
    doy = (153 * mp + 2) // 5
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146_097 + doe - 719_468


def to_time(value: Any) -> float | None:
    """data.ts:52-61 `toTime`: a date or timestamp text as epoch ms, or None.
    A time with no zone is UTC. The rules of Date.parse in V8: a day up to 31
    runs on into the next month ("2026-02-30" is 2 March), 24:00 is the next
    midnight, and the fraction is cut to milliseconds."""
    if not isinstance(value, str):
        return None
    match = _ISO_PARTS.fullmatch(value.strip())
    if not match:
        return None
    year, month, day, hour, minute, second, fraction, _, sign, zh, zm = match.groups()
    h, m, s = int(hour or 0), int(minute or 0), int(second or 0)
    ms = int((fraction or "0")[:3].ljust(3, "0"))
    if not (1 <= int(month) <= 12 and 1 <= int(day) <= 31 and m <= 59 and s <= 59):
        return None
    if h > 24 or (h == 24 and (m or s or ms)):
        return None
    offset = 0
    if sign:
        if int(zh) > 23 or int(zm) > 59:
            return None
        offset = (int(zh) * 60 + int(zm)) * 60_000 * (1 if sign == "+" else -1)
    days = _days_from_civil(int(year), int(month)) + int(day) - 1
    return float(days * _DAY_MS + ((h * 60 + m) * 60 + s) * 1000 + ms - offset)


def x_kind_of(values: Sequence[Any]) -> str:
    """data.ts:64-70 `xKindOf`: "time", "value" or "category", the axis kind
    that fits every value that is not empty."""
    present = [v for v in values if v is not None and v != ""]
    if not present:
        return "category"
    if all(to_time(v) is not None for v in present):
        return "time"
    if all(not isinstance(v, str) and to_number(v) is not None for v in present):
        return "value"
    return "category"


def js_string(value: Any) -> str:
    """JavaScript `String(value)` for the JSON values of a row."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e21:
        return str(int(value))
    if isinstance(value, list):
        return ",".join("" if v is None else js_string(v) for v in value)
    if isinstance(value, dict):
        return "[object Object]"
    return str(value)


def _group_name(value: Any) -> str:
    """`String(value ?? '(empty)')`, the name of a series or a slice."""
    return "(empty)" if value is None else js_string(value)


def _x_key(kind: str, value: Any) -> XKey | None:
    """data.ts:72-77 `xKey`."""
    if value is None:
        return None
    if kind == "time":
        return to_time(value)
    if kind == "value":
        return to_number(value)
    return js_string(value)


def _js_round(value: float) -> int:
    """Math.round: a half goes up."""
    return math.floor(value + 0.5)


def number_of(value: Any) -> float | None:
    """widgetConfig.ts:382-387 `numberOf`: a number setting of a saved config."""
    if isinstance(value, str) and not value.strip():
        return None
    return to_number(value)


# --- series (data.ts buildSeries) --------------------------------------------------


@dataclass
class Point:
    x: XKey
    y: float
    n: int
    lo: float | None = None
    hi: float | None = None
    lo2: float | None = None
    hi2: float | None = None


@dataclass
class _Bucket:
    x: XKey
    values: list[float] = field(default_factory=list)
    rows: list[Row] = field(default_factory=list)


@dataclass
class Built:
    kind: str
    series: list[tuple[str, list[Point]]]
    dropped: int
    # The series before the fold into "Other" (data.ts:214).
    groups: int


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _sd(values: Sequence[float]) -> float:
    """data.ts:81-85"""
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def _quantile(ordered: Sequence[float], p: float) -> float:
    """data.ts:88-94"""
    if not ordered:
        return math.nan
    i = p * (len(ordered) - 1)
    lo = math.floor(i)
    hi = math.ceil(i)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (i - lo)


def _combine(values: Sequence[float], combine: str) -> float:
    """data.ts:113-127 `combineValues`. A count is a sum of ones."""
    if combine == "mean":
        return _mean(values)
    if combine == "median":
        return _quantile(sorted(values), 0.5)
    if combine == "min":
        return min(values)
    if combine == "max":
        return max(values)
    return sum(values)


@dataclass(frozen=True)
class _SeriesSpec:
    x: str
    y: tuple[str, ...]
    series_by: str | None
    uncertainty: str
    lower: str | None
    upper: str | None
    stderr: str | None
    combine: str


def _center_and_band(bucket: _Bucket, spec: _SeriesSpec) -> Point:
    """data.ts:129-172 `centerAndBand`."""
    values = bucket.values
    n = len(values)
    u = spec.uncertainty
    if u in ("sd", "ci95", "minmax"):
        m = _mean(values)
        if u == "minmax":
            return Point(bucket.x, m, n, lo=min(values), hi=max(values))
        if u == "sd":
            half = _sd(values)
        else:
            half = 1.96 * _sd(values) / math.sqrt(n) if n > 1 else 0.0
        return Point(bucket.x, m, n, lo=m - half, hi=m + half)
    if u == "quantiles":
        ordered = sorted(values)
        return Point(
            bucket.x,
            _quantile(ordered, 0.5),
            n,
            lo=_quantile(ordered, 0.25),
            hi=_quantile(ordered, 0.75),
            lo2=_quantile(ordered, 0.05),
            hi2=_quantile(ordered, 0.95),
        )
    y = _combine(values, spec.combine)
    if u == "columns" and spec.lower and spec.upper:
        lows = [
            v for r in bucket.rows if (v := to_number(r.get(spec.lower))) is not None
        ]
        highs = [
            v for r in bucket.rows if (v := to_number(r.get(spec.upper))) is not None
        ]
        if lows and highs:
            return Point(bucket.x, y, n, lo=min(lows), hi=max(highs))
        return Point(bucket.x, y, n)
    if u == "stderr" and spec.stderr:
        errors = [
            v for r in bucket.rows if (v := to_number(r.get(spec.stderr))) is not None
        ]
        if not errors:
            return Point(bucket.x, y, n)
        half = (
            1.96
            * math.sqrt(sum(e * e for e in errors))
            / (n if spec.combine == "mean" else 1)
        )
        return Point(bucket.x, y, n, lo=y - half, hi=y + half)
    return Point(bucket.x, y, n)


def build_series(rows: Sequence[Row], spec: _SeriesSpec) -> Built:
    """data.ts:181-233 `buildSeries`: one series for each value of series_by
    (largest total first, the ones past the palette folded into "Other"), or
    one for each Y column. Rows that share an x form one point."""
    kind = x_kind_of([r.get(spec.x) for r in rows])
    dropped = 0
    groups: dict[str, dict[XKey, _Bucket]] = {}

    def add(name: str, row: Row, column: str) -> None:
        nonlocal dropped
        x = _x_key(kind, row.get(spec.x))
        raw = row.get(column)
        if spec.combine == "count":
            y = None if raw is None or raw == "" else 1.0
        else:
            y = to_number(raw)
        if x is None or y is None:
            dropped += 1
            return
        bucket = groups.setdefault(name, {}).setdefault(x, _Bucket(x))
        bucket.values.append(y)
        bucket.rows.append(row)

    if spec.series_by:
        for row in rows:
            add(_group_name(row.get(spec.series_by)), row, spec.y[0])
    else:
        for column in spec.y:
            for row in rows:
                add(column, row, column)

    named = list(groups.items())
    count = len(named)
    if spec.series_by:

        def total(buckets: dict[XKey, _Bucket]) -> float:
            return sum(abs(v) for b in buckets.values() for v in b.values)

        named.sort(key=lambda item: -total(item[1]))
        if len(named) > widgets.MAX_SERIES:
            other: dict[XKey, _Bucket] = {}
            for _, buckets in named[widgets.MAX_SERIES - 1 :]:
                for x, bucket in buckets.items():
                    merged = other.setdefault(x, _Bucket(x))
                    merged.values.extend(bucket.values)
                    merged.rows.extend(bucket.rows)
            named = [*named[: widgets.MAX_SERIES - 1], ("Other", other)]

    series = []
    for name, buckets in named:
        ordered = list(buckets.values())
        if kind != "category":
            ordered.sort(key=lambda b: b.x)
        series.append((name, [_center_and_band(b, spec) for b in ordered]))
    return Built(kind, series, dropped, count)


# --- transforms (data.ts applyTransform) ------------------------------------------

# data.ts:240-241 BAND_KEYS, without "y": every point has a y.
_BAND_KEYS = ("lo", "hi", "lo2", "hi2")
DEFAULT_WINDOW = 20  # data.ts:238


def _with_band(p: Point, y: float, band: dict[str, float | None]) -> Point:
    return Point(p.x, y, p.n, band["lo"], band["hi"], band["lo2"], band["hi2"])


def _rolling_mean(points: list[Point], window: int) -> list[Point]:
    """data.ts:244-255: the mean of each key over the last `window` points."""
    out = []
    for i, p in enumerate(points):
        window_points = points[max(0, i - window + 1) : i + 1]
        band: dict[str, float | None] = {}
        for key in _BAND_KEYS:
            column = [getattr(q, key) for q in window_points]
            band[key] = None if any(v is None for v in column) else _mean(column)
        out.append(_with_band(p, _mean([q.y for q in window_points]), band))
    return out


def _ewma(points: list[Point], window: int) -> list[Point]:
    """data.ts:259-273: the exponentially weighted mean, alpha = 2 / (window + 1)."""
    alpha = 2 / (window + 1)
    last: dict[str, float] = {}
    out = []
    for p in points:
        band: dict[str, float | None] = {}
        for key in ("y", *_BAND_KEYS):
            v = getattr(p, key)
            if v is None:
                last.pop(key, None)
            else:
                last[key] = (
                    v if key not in last else alpha * v + (1 - alpha) * last[key]
                )
            band[key] = last.get(key)
        out.append(_with_band(p, last["y"], band))
    return out


def apply_transform(
    points: list[Point], transform: str, window: float | None, k: float | None
) -> tuple[list[Point], bool]:
    """data.ts:280-330 `applyTransform`: the points, and whether the band of
    the rows was dropped."""
    if transform == "none" or not points:
        return points, False
    size = max(2, _js_round(window if window is not None else DEFAULT_WINDOW))
    had_band = any(p.lo is not None for p in points)
    if transform == "ma7":
        return _rolling_mean(points, 7), False
    if transform == "mean":
        return _rolling_mean(points, size), False
    if transform == "ewma":
        return _ewma(points, size), False
    if transform == "bollinger":
        band_k = 2.0 if k is None else k
        out = []
        for i, p in enumerate(points):
            ys = [q.y for q in points[max(0, i - size + 1) : i + 1]]
            m = _mean(ys)
            s = _sd(ys)
            out.append(Point(p.x, m, p.n, lo=m - band_k * s, hi=m + band_k * s))
        return out, had_band
    if transform == "index":
        base = next((p.y for p in points if p.y != 0), None)
        if base is None:
            return points, False

        def scale(v: float | None) -> float | None:
            return None if v is None else v / base * 100

        return [
            Point(
                p.x,
                p.y / base * 100,
                p.n,
                scale(p.lo),
                scale(p.hi),
                scale(p.lo2),
                scale(p.hi2),
            )
            for p in points
        ], False
    if transform == "cum":
        total = 0.0
        out = []
        for p in points:
            total += p.y
            out.append(Point(p.x, total, p.n))
        return out, had_band
    out = []
    for i, p in enumerate(points):
        before = points[i - 1].y if i else 0.0
        out.append(
            Point(p.x, 0.0 if i == 0 or before == 0 else (p.y / before - 1) * 100, p.n)
        )
    return out, had_band


# --- the summary of a chart ----------------------------------------------------------


@dataclass
class Summary:
    """What the chart draws (`facts`) and what the agent should know (`notes`)."""

    facts: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# option.ts LABEL_MAX_VERTICAL / LABEL_MAX_HORIZONTAL: the chart cuts a
# category label to 14 characters (26 on horizontal bars), with the full text
# in the tooltip; `hideOverlap` (option.ts axisBase) still hides labels that
# overlap.
LONG_LABEL = 14
LONG_LABEL_HORIZONTAL = 26
_SHOWN_NAMES = 4  # name the series when there are this many or fewer


def _label_note(labels: Sequence[str], what: str = "x label") -> list[str]:
    longest = max(labels, key=len, default="")
    if len(longest) <= LONG_LABEL:
        return []
    sample = longest if len(longest) <= 40 else longest[:40] + "…"
    return [
        f"long labels: the longest {what} has {len(longest)} characters ({sample!r}). "
        f"The chart cuts labels to {LONG_LABEL} characters ({LONG_LABEL_HORIZONTAL} on "
        "--horizontal bars) and shows the full text in the tooltip. Consider --horizontal "
        "(bars), fewer categories or shorter labels."
    ]


def _names(names: Sequence[str]) -> str:
    return f" ({', '.join(names)})" if len(names) <= _SHOWN_NAMES else ""


def _log_note() -> str:
    return "A log scale needs values above 0: the linear scale is shown."


def _axis(
    widget_type: str, config: Mapping[str, Any], rows: Sequence[Row], out: Summary
) -> None:
    """option.ts:396-537 `buildOption`: line, bar, stackedbar and linebar."""
    x = config.get("x_axis_name")
    y = config.get("y_axis_name")
    if not x or not y:
        return
    series_by = config.get("series_by") or None
    y1 = config.get("y1_axis_name")
    is_bar = widget_type in widgets.BAR_TYPES  # option.ts:398
    # option.ts:400: the second Y column only without series_by.
    y_columns = (y, y1) if y1 and y1 != "None" and y1 != y and not series_by else (y,)
    uncertainty = config.get("uncertainty") or "none"
    if uncertainty != "none" and widget_type == "stackedbar":
        out.notes.append(
            "Bands and error bars do not show on stacked bars."
        )  # option.ts:402-404
        uncertainty = "none"
    combine = config.get("combine") or ("sum" if is_bar else "mean")  # option.ts:406
    stat_band = uncertainty in ("sd", "ci95", "minmax", "quantiles")
    if uncertainty != "none":
        # option.ts:410-419
        if combine == "count" or (not stat_band and combine not in ("sum", "mean")):
            out.notes.append(
                f"The band does not show when the rows are combined by {combine}."
            )
            uncertainty = "none"
        elif stat_band and config.get("combine") and config.get("combine") != "mean":
            center = "median" if uncertainty == "quantiles" else "mean"
            out.notes.append(f"With this band, each point is the {center} of its rows.")
    built = build_series(
        rows,
        _SeriesSpec(
            x=x,
            y=tuple(y_columns),
            series_by=series_by,
            uncertainty=uncertainty,
            lower=config.get("lower_name"),
            upper=config.get("upper_name"),
            stderr=config.get("stderr_name"),
            combine=combine,
        ),
    )
    if built.dropped > 0:  # option.ts:430-431
        out.notes.append(
            f"{built.dropped} rows have no number or no {x}: they are not drawn."
        )
    if config.get("order_by") == "y" and not (
        built.kind == "category" or (is_bar and built.kind == "value")
    ):  # option.ts:436-451
        out.notes.append(
            f"{x} is a time or a number: the points keep the order of {x}."
        )
    transform = config.get("transform") or "none"
    if transform == "bollinger" and widget_type != "line":  # option.ts:455-456
        transform = "none"
    window = max(
        3, _js_round(number_of(config.get("window")) or DEFAULT_WINDOW)
    )  # option.ts:457
    band_dropped = False
    series = []
    for name, points in built.series:
        drawn, dropped_band = apply_transform(
            points, transform, window, number_of(config.get("band_k"))
        )
        band_dropped = band_dropped or dropped_band
        series.append((name, drawn))
    if band_dropped:  # option.ts:463-468
        out.notes.append(
            "The ±k·σ band replaces the band of the rows."
            if transform == "bollinger"
            else "The band does not carry through a running total or a change rate."
        )
    xs = list(dict.fromkeys(p.x for _, points in series for p in points))
    if not xs:  # option.ts:469
        out.notes.append(
            f"Nothing to draw: no row has both a {x} and a number in {', '.join(y_columns)}."
        )
        return
    drawn_as = (
        ", drawn as categories" if is_bar and built.kind != "category" else ""
    )  # option.ts:517
    out.facts.append(
        f"x: {x}: {_KIND_TEXT[built.kind]} axis{drawn_as}, {len(xs)} values"
    )
    names = [name for name, _ in series]
    if built.groups > len(names):  # data.ts:214-224
        out.facts.append(
            f"series: {built.groups} values of {series_by}: the {widgets.MAX_SERIES - 1} largest + 'Other'"
        )
    else:
        out.facts.append(f"series: {len(names)}{_names(names)}")
    if config.get("scale") == "log" and any(
        p.y <= 0 or (p.lo is not None and p.lo <= 0)
        for _, points in series
        for p in points
    ):  # option.ts:530-537
        out.notes.append(_log_note())
    if built.kind == "category":
        out.notes += _label_note([str(v) for v in xs])


_KIND_TEXT = {"time": "time", "value": "number", "category": "category"}


def _pie(config: Mapping[str, Any], rows: Sequence[Row], out: Summary) -> None:
    """option.ts:980-999 `pieOption`."""
    x = config.get("x_axis_name")
    y = config.get("y_axis_name")
    if not x:
        return
    totals: dict[str, float] = {}
    skipped = 0
    for row in rows:
        key = _group_name(row.get(x))
        value = to_number(row.get(y)) if y else 1.0
        if value is None:
            # option.ts:987 skips the row with no note; the CLI says so.
            skipped += 1
            continue
        totals[key] = totals.get(key, 0.0) + value
    if skipped:
        out.notes.append(f"{skipped} rows have no number in {y}: they are not counted.")
    ordered = sorted(totals.items(), key=lambda item: -item[1])
    if not ordered:
        out.notes.append("Nothing to draw: no slice.")
        return
    limit = widgets.MAX_PIE_SLICES
    if len(ordered) > limit:  # option.ts:991-997
        out.facts.append(
            f"slices: {len(ordered)} values of {x}: the {limit - 1} largest + 'Other'"
        )
        out.notes.append(
            f"A pie draws at most {limit} slices: the other {len(ordered) - limit + 1} "
            "go into 'Other'. Use a bar for more categories, or filter the rows."
        )
    else:
        out.facts.append(f"slices: {len(ordered)}{_names([k for k, _ in ordered])}")
    out.notes += _label_note([k for k, _ in ordered], "slice name")


def _scatter(config: Mapping[str, Any], rows: Sequence[Row], out: Summary) -> None:
    """option.ts:1076-1207 `scatterOption`."""
    x = config.get("x_axis_name")
    y = config.get("y_axis_name")
    if not x or not y:
        return
    series_by = config.get("series_by") or None
    size_by = config.get("size_by") or None
    xs = [v for r in rows if (v := r.get(x)) is not None and v != ""]
    numeric = sum(1 for v in xs if to_number(v) is not None)
    # option.ts:1083-1085: a number column with a few text values stays a number axis.
    kind = "value" if xs and numeric / len(xs) >= 0.8 else x_kind_of(xs)
    scale = config.get("color_scale") == "scale" and bool(series_by)  # option.ts:1086
    categories: dict[str, None] = {}
    groups: dict[str, int] = {}
    dropped = no_size = negative_size = 0
    colors: list[float] = []
    ys: list[float] = []
    for row in rows:
        raw = row.get(x)
        if kind == "value":
            position = to_number(raw)
        elif kind == "time":
            position = to_time(raw)
        elif raw is None or raw == "":
            position = None
        else:
            categories.setdefault(js_string(raw))
            position = 0.0
        y_value = to_number(row.get(y))
        if position is None or y_value is None:  # option.ts:1114-1117
            dropped += 1
            continue
        ys.append(y_value)
        color = to_number(row.get(series_by)) if scale and series_by else None
        size = to_number(row.get(size_by)) if size_by else None
        if size_by and size is None:
            no_size += 1
        if size is not None and size < 0:
            negative_size += 1
        if color is not None:
            colors.append(color)
        if scale:
            key = f"no {series_by}" if color is None else y
        elif series_by:
            key = _group_name(row.get(series_by))
        else:
            key = y
        groups[key] = groups.get(key, 0) + 1
    if dropped:  # option.ts:1132-1133
        out.notes.append(
            f"{dropped} rows have no {x} or no number in {y}: they are not drawn."
        )
    if no_size:  # option.ts:1134-1135
        out.notes.append(
            f"{no_size} rows have no number in {size_by}: they have the smallest dot."
        )
    if negative_size:  # option.ts:1136-1137
        out.notes.append(
            f"Dot area shows values of 0 and above: {negative_size} rows are below 0."
        )
    if not groups:
        out.notes.append(f"Nothing to draw: no row has both a {x} and a number in {y}.")
        return
    out.facts.append(f"x: {x}: {_KIND_TEXT[kind]} axis, {len(ys)} dots")
    limit = widgets.MAX_SCATTER_GROUPS
    if scale:
        if colors and max(colors) == min(colors):  # option.ts:1170-1171
            out.notes.append(f"{series_by} has one value: no colour scale.")
        if not colors:  # option.ts:1172
            out.notes.append(f"{series_by} has no numbers: no colour scale.")
        if colors and max(colors) > min(colors):
            out.facts.append(f"colour: {series_by}, a scale from low to high")
    elif len(groups) > limit:  # option.ts:1143-1145
        out.facts.append(
            f"groups: {len(groups)} values of {series_by}: the {limit - 1} largest + 'Other'"
        )
    elif series_by:
        names = sorted(groups, key=lambda k: -groups[k])
        out.facts.append(f"groups: {len(groups)}{_names(names)}")
    log = config.get("scale") == "log"
    if log and any(v <= 0 for v in ys):  # option.ts:1201-1205
        out.notes.append(_log_note())
        log = False
    if (
        config.get("fit") is not False and kind == "value" and log
    ):  # option.ts:1206-1207
        out.notes.append("The fit needs a linear Y scale: it is not shown.")
    if kind == "category":
        out.notes += _label_note(list(categories))


def _histogram(config: Mapping[str, Any], rows: Sequence[Row], out: Summary) -> None:
    """option.ts:1377-1385 `histogramOption` and 1686-1710 `ecdfOption`."""
    column = config.get("x_axis_name") or config.get("y_axis_name")
    if not column:
        return
    values = [to_number(r.get(column)) for r in rows]
    numbers = [v for v in values if v is not None]
    if len(numbers) < len(rows):  # option.ts:1382-1383, 1702
        out.notes.append(f"{len(rows) - len(numbers)} rows have no number in {column}.")
    if not numbers:
        out.notes.append(f"Nothing to draw: {column} has no numbers.")
        return
    out.facts.append(
        f"values: {len(numbers)} numbers in {column}, {min(numbers):g} to {max(numbers):g}"
    )
    series_by = config.get("series_by")
    if config.get("hist_view") == "ecdf" and series_by:
        groups = {
            _group_name(r.get(series_by))
            for r, v in zip(rows, values, strict=True)
            if v is not None
        }
        if len(groups) > widgets.MAX_SERIES:  # option.ts:1704-1709
            out.facts.append(
                f"series: {len(groups)} values of {series_by}: the {widgets.MAX_SERIES - 1} largest + 'Other'"
            )
        else:
            out.facts.append(f"series: {len(groups)}")


def _range(config: Mapping[str, Any], rows: Sequence[Row], out: Summary) -> None:
    """option.ts:1471-1516 `rangeOption`."""
    x = config.get("x_axis_name")
    shape = config.get("range_shape") or "candle"
    keys = [widgets.RANGE_KEYS[p] for p in widgets.RANGE_COLUMNS.get(shape, ())]
    columns = [c for k in keys if isinstance(c := config.get(k), str) and c]
    if not x or not keys or len(columns) < len(keys):
        return
    kind = x_kind_of([r.get(x) for r in rows])
    dropped = 0
    marks: list[list[float]] = []
    labels: list[str] = []
    for row in rows:
        position = _x_key(kind, row.get(x))
        values = [to_number(row.get(c)) for c in columns]
        if position is None or any(v is None for v in values):  # option.ts:1490-1493
            dropped += 1
            continue
        marks.append([v for v in values if v is not None])
        labels.append(str(position))
    if dropped:  # option.ts:1498
        out.notes.append(
            f"{dropped} rows miss a value of the range: they are not drawn."
        )
    if not marks:
        out.notes.append("Nothing to draw: no row has every value of the range.")
        return
    out.facts.append(f"x: {x}: {_KIND_TEXT[kind]} axis, {len(marks)} {shape} marks")
    if config.get("scale") == "log" and any(
        v <= 0 for m in marks for v in m
    ):  # option.ts:1512-1516
        out.notes.append(_log_note())
    if kind == "category":
        out.notes += _label_note(labels)


def _value(config: Mapping[str, Any], rows: Sequence[Row], out: Summary) -> None:
    """StatTile.tsx:31-42: the tile shows the value of the first row."""
    y = config.get("y_axis_name")
    if not y:
        return
    raw = rows[0].get(y)
    text = "–" if raw is None else js_string(raw)  # StatTile.tsx:36
    if to_number(raw) is None:
        out.notes.append(
            f"The first row's {y} is not a number: the tile shows {text!r} as text."
        )
    out.facts.append(f"value: {text} ({y} of the first row)")


def summarize(
    widget_type: str,
    config: Mapping[str, Any],
    rows: Sequence[Row],
    *,
    limit: int | None = None,
) -> Summary:
    """What the widget shows from these rows, as the dashboard draws it.
    `limit` is the row limit of the read: the dashboard's cap
    (widgets.CHART_ROWS) or a smaller --limit. A table reads pages, so it has
    no cap."""
    out = Summary()
    read = f"rows: {len(rows)}"
    full = limit is not None and len(rows) >= limit and widget_type != "table"
    if full and limit >= widgets.CHART_ROWS:
        read += f" (the cap of {limit}: the chart reads no more rows; aggregate or narrow --timeframe)"
    elif full:
        read += (
            f" (the --limit of {limit}; the dashboard reads up to {widgets.CHART_ROWS})"
        )
    out.facts.append(read)
    if not rows:
        # option.ts:388: no rows, an empty chart.
        timeframe = config.get("timeframe")
        wider = (
            f"Use a wider --timeframe (now {timeframe}), or check"
            if timeframe and timeframe not in ("60d", "2m", "1y")
            else "Check"
        )
        out.notes.append(
            f"0 rows: the widget is empty. {wider} that the query returns rows."
        )
        return out
    if widget_type in Y_AXIS_TYPES:
        _axis(widget_type, config, rows, out)
    elif widget_type == "pie":
        _pie(config, rows, out)
    elif widget_type == "scatter":
        _scatter(config, rows, out)
    elif widget_type == "histogram":
        _histogram(config, rows, out)
    elif widget_type == "range":
        _range(config, rows, out)
    elif widget_type == "value":
        _value(config, rows, out)
    return out
