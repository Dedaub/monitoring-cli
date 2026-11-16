"""What a chart draws must be what the web chart kit draws.

The expected values below are the output of the frontend's own `data.ts`
(`toNumber`, `toTime`, `xKindOf`, `buildSeries`, `applyTransform`), run under
node for the same inputs. A change to the Python that changes one of them
fails here.
"""

import pytest

from monitoring_cli import chartdata

# --- values (data.ts) -------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "number"),
    [
        ("  12 ", 12),
        ("1e3", 1000),
        ("1.", 1),
        (".5", 0.5),
        ("0x1F", 31),
        ("0X1f", 31),
        ("0b101", 5),
        ("+3", 3),
        (" -4.5e-2 ", -0.045),
        (5, 5),
        (2.5, 2.5),
        ("-0x1F", None),
        ("1_000", None),
        ("Infinity", None),
        ("", None),
        ("-", None),
        ("1e", None),
        ("abc", None),
        (True, None),
        (None, None),
    ],
)
def test_to_number_matches_javascript(value, number):
    assert chartdata.to_number(value) == number


@pytest.mark.parametrize(
    ("value", "ms"),
    [
        ("2026-10-01", 1790812800000),
        (" 2026-10-01 ", 1790812800000),
        ("2026-10-01T12:34", 1790858040000),
        ("2026-10-01 12:34:56Z", 1790858096000),
        ("2026-10-01T12:34:56.123456789+0530", 1790838296123),
        ("2026-10-01T12:34:56.9999Z", 1790858096999),
        ("2026-10-01T12:34+23:59", 1790771700000),
        ("2026-02-30", 1772409600000),  # V8 runs on into March
        ("2026-04-31", 1777593600000),
        ("2026-10-01T24:00Z", 1790899200000),
        ("0000-01-01T00:00Z", -62167219200000),
        ("2026-02-32", None),
        ("2026-00-10", None),
        ("2026-13-01", None),
        ("2026-10-01T23:60Z", None),
        ("2026-10-01T24:00:01Z", None),
        ("2026-10-01T12:34+24:00", None),
        ("2026-1-01", None),
        (5, None),
        (None, None),
    ],
)
def test_to_time_matches_date_parse(value, ms):
    assert chartdata.to_time(value) == ms


@pytest.mark.parametrize(
    ("values", "kind"),
    [
        (["2026-01-01", None, ""], "time"),
        ([1, 2.5, "3"], "category"),  # a number as text is not a number axis
        ([1, 2], "value"),
        ([True, 1], "category"),
        ([], "category"),
        ([None], "category"),
        (["2026-01-01", 3], "category"),
    ],
)
def test_x_kind_of_matches_the_web(values, kind):
    assert chartdata.x_kind_of(values) == kind


# --- series ------------------------------------------------------------------------


def _points(built, transform):
    out = []
    for name, points in built.series:
        drawn, dropped = chartdata.apply_transform(points, transform, None, None)
        out.append((name, [[p.x, p.y, p.lo] for p in drawn], dropped))
    return out


def test_build_series_folds_the_ninth_series_into_other():
    rows = [
        {"d": "2026-10-02", "n": "a", "v": 3},
        {"d": "2026-10-01", "n": "b", "v": "4"},
        {"d": "2026-10-01", "n": "a", "v": 1},
        {"d": "2026-10-02", "n": "c", "v": None},
        {"d": None, "n": "c", "v": 2},
        {"d": "2026-10-03", "n": "d", "v": -6},
        {"d": "2026-10-03", "n": "e", "v": 0.5},
        {"d": "2026-10-03", "n": "f", "v": 7},
        {"d": "2026-10-03", "n": "g", "v": 8},
        {"d": "2026-10-03", "n": "h", "v": 9},
        {"d": "2026-10-03", "n": "i", "v": 10},
        {"d": "2026-10-03", "n": None, "v": 11},
    ]
    spec = chartdata._SeriesSpec("d", ("v",), "n", "none", None, None, None, "sum")
    built = chartdata.build_series(rows, spec)
    assert (built.kind, built.dropped, built.groups) == ("time", 2, 9)
    assert _points(built, "cum") == [
        ("(empty)", [[1790985600000, 11, None]], False),
        ("i", [[1790985600000, 10, None]], False),
        ("h", [[1790985600000, 9, None]], False),
        ("g", [[1790985600000, 8, None]], False),
        ("f", [[1790985600000, 7, None]], False),
        ("d", [[1790985600000, -6, None]], False),
        ("a", [[1790812800000, 1, None], [1790899200000, 4, None]], False),
        ("Other", [[1790812800000, 4, None], [1790985600000, 4.5, None]], False),
    ]


def test_build_series_two_columns_with_a_band_and_a_change_rate():
    rows = [
        {"d": "2026-10-01", "v": 2, "w": 5},
        {"d": "2026-10-01", "v": 4, "w": "x"},
        {"d": "2026-10-02", "v": 6, "w": 1},
    ]
    spec = chartdata._SeriesSpec("d", ("v", "w"), None, "sd", None, None, None, "mean")
    built = chartdata.build_series(rows, spec)
    assert (built.kind, built.dropped) == ("time", 1)
    assert _points(built, "pct") == [
        ("v", [[1790812800000, 0, None], [1790899200000, 100, None]], True),
        ("w", [[1790812800000, 0, None], [1790899200000, -80, None]], True),
    ]


# --- golden values of the transforms -------------------------------------------------
#
# The numbers below are the output of data.ts itself (`applyTransform` and
# `buildSeries` of watchdog-components/charts/kit/data.ts), run under vitest on
# these exact inputs. Each point is [y, lo, hi].

_YS = [10, 12, 11, 15, 14, 18, 17, 21, 20, 25]


def _line(ys, lo=None, hi=None):
    return [
        chartdata.Point(
            i,
            y,
            1,
            None if lo is None else lo[i],
            None if hi is None else hi[i],
        )
        for i, y in enumerate(ys)
    ]


def _out(points):
    return [[p.y, p.lo, p.hi] for p in points]


def _transform(points, transform, window=None, k=None):
    drawn, _ = chartdata.apply_transform(points, transform, window, k)
    return drawn


def _same(actual, expected):
    assert len(actual) == len(expected)
    for got, want in zip(actual, expected, strict=True):
        assert got == pytest.approx(want, rel=1e-9, abs=1e-12)


_BANDED = _line([2, 4, 6, 8], lo=[1, 3, 5, None], hi=[3, 5, 7, None])


def test_ma7_matches_data_ts():
    expected = [10, 11, 11, 12, 12.4, 13.333333333333334, 13.857142857142858]
    expected += [15.428571428571429, 16.571428571428573, 18.571428571428573]
    _same([p.y for p in _transform(_line(_YS), "ma7")], expected)


def test_rolling_mean_with_a_window_matches_data_ts():
    expected = [10, 11, 11, 12.666666666666666, 13.333333333333334]
    expected += [15.666666666666666, 16.333333333333332, 18.666666666666668]
    expected += [19.333333333333332, 22]
    _same([p.y for p in _transform(_line(_YS), "mean", 3)], expected)


def test_rolling_mean_carries_the_band_and_drops_it_after_a_gap():
    drawn = _transform(_BANDED, "mean", 3)
    _same(_out(drawn)[:3], [[2, 1, 3], [3, 2, 4], [4, 3, 5]])
    assert _out(drawn)[3] == [6, None, None]  # a point with no band in the window


def test_ewma_matches_data_ts():
    expected = [10, 11, 11, 13, 13.5, 15.75, 16.375, 18.6875, 19.34375, 22.171875]
    _same([p.y for p in _transform(_line(_YS), "ewma", 3)], expected)
    drawn = _transform(_BANDED, "ewma", 3)
    _same(_out(drawn)[:3], [[2, 1, 3], [3, 2, 4], [4.5, 3.5, 5.5]])
    assert _out(drawn)[3] == [6.25, None, None]


def test_bollinger_matches_data_ts():
    expected = [
        [10, 10, 10],
        [11, 8.17157287525381, 13.82842712474619],
        [11, 9, 13],
        [12.666666666666666, 8.5033346677344, 16.829998665598932],
        [13.333333333333334, 9.170001334401068, 17.4966653322656],
        [15.666666666666666, 11.5033346677344, 19.829998665598932],
        [16.333333333333332, 12.170001334401066, 20.4966653322656],
        [18.666666666666668, 14.503334667734402, 22.829998665598936],
        [19.333333333333332, 15.170001334401066, 23.4966653322656],
        [22, 16.70849737787082, 27.29150262212918],
    ]
    _same(_out(_transform(_line(_YS), "bollinger", 3, 2)), expected)
    default_k = [
        [10, 10, 10],
        [11, 8.17157287525381, 13.82842712474619],
        [11, 9, 13],
        [12, 7.679506201061426, 16.320493798938575],
        [13, 9.348516283298892, 16.651483716701108],
        [14.5, 8.726497308103742, 20.273502691896258],
        [16, 12.348516283298892, 19.651483716701108],
        [17.5, 11.726497308103742, 23.273502691896258],
        [19, 15.348516283298892, 22.651483716701108],
        [20.75, 14.14192413280033, 27.35807586719967],
    ]
    _same(_out(_transform(_line(_YS), "bollinger", 4, None)), default_k)


def test_index_matches_data_ts():
    points = _line([0, 5, 10, 20], lo=[-1, 4, 9, 19], hi=[2, 7, 12, 22])
    expected = [[0, -20, 40], [100, 80, 140], [200, 180, 240]]
    expected.append([400, 380, 440.00000000000006])
    _same(_out(_transform(points, "index")), expected)


def test_rolling_transforms_keep_a_constant_series_constant():
    # Property: the mean of a constant is that constant, for any window.
    constant = _line([3.5] * 9)
    for window in (None, 2, 5, 40):
        drawn = _transform(constant, "mean", window)
        assert [p.y for p in drawn] == [3.5] * 9
    assert [p.y for p in _transform(constant, "ma7")] == [3.5] * 9
    bands = _transform(constant, "bollinger", 4, 2)
    assert [(p.y, p.lo, p.hi) for p in bands] == [(3.5, 3.5, 3.5)] * 9


def test_rolling_mean_of_huge_values_does_not_lose_the_small_ones():
    # A running sum must not keep an error from a value that left the window.
    ys = [1e18, 1e18, 5.0, 7.0, 9.0, 11.0]
    drawn = _transform(_line(ys), "mean", 2)
    assert [p.y for p in drawn][3:] == [6.0, 8.0, 10.0]


def _golden_rows():
    rows = [
        ("2026-10-01", 2, 0.3),
        ("2026-10-01", 4, 0.4),
        ("2026-10-01", 9, 0.5),
        ("2026-10-02", 5, 0.2),
        ("2026-10-03", 1, 0.1),
        ("2026-10-03", 9, 0.1),
        ("2026-10-03", 5, 0.1),
        ("2026-10-03", 3, 0.1),
    ]
    return [{"d": d, "v": v, "e": e} for d, v, e in rows]


def _built(uncertainty="none", combine="sum", stderr=None):
    spec = chartdata._SeriesSpec(
        "d", ("v",), None, uncertainty, None, None, stderr, combine
    )
    [(_, points)] = chartdata.build_series(_golden_rows(), spec).series
    return [[p.x, p.y, p.n, p.lo, p.hi] for p in points]


def test_ci95_matches_data_ts():
    _same(
        _built("ci95"),
        [
            [1790812800000, 5, 3, 0.91993464104638, 9.08006535895362],
            [1790899200000, 5, 1, 5, 5],
            [1790985600000, 4.5, 4, 1.1526627497865314, 7.847337250213469],
        ],
    )


def test_stderr_band_matches_data_ts():
    _same(
        _built("stderr", "sum", "e"),
        [
            [1790812800000, 15, 3, 13.614070708874367, 16.385929291125635],
            [1790899200000, 5, 1, 4.608, 5.392],
            [1790985600000, 18, 4, 17.608, 18.392],
        ],
    )
    _same(
        _built("stderr", "mean", "e"),
        [
            [1790812800000, 5, 3, 4.538023569624789, 5.461976430375211],
            [1790899200000, 5, 1, 4.608, 5.392],
            [1790985600000, 4.5, 4, 4.402, 4.598],
        ],
    )


def test_median_combine_matches_data_ts():
    points = _built(combine="median")
    assert [p[1] for p in points] == [4, 5, 4]
    assert [p[2] for p in points] == [3, 1, 4]


# --- the summary ---------------------------------------------------------------------


def _summary(widget_type, config, rows, limit=None):
    return chartdata.summarize(widget_type, config, rows, limit=limit)


def test_no_rows_asks_for_a_wider_timeframe():
    s = _summary(
        "line", {"x_axis_name": "d", "y_axis_name": "v", "timeframe": "7d"}, []
    )
    assert s.facts == ["rows: 0"]
    assert s.notes == [
        "0 rows: the widget is empty. Use a wider --timeframe (now 7d), or check that the query returns rows."
    ]
    widest = _summary("line", {"timeframe": "60d"}, [])
    assert widest.notes == [
        "0 rows: the widget is empty. Check that the query returns rows."
    ]


def test_the_chart_cap_is_a_fact(monkeypatch):
    monkeypatch.setattr(chartdata.widgets, "CHART_ROWS", 3)
    rows = [{"d": "2026-10-01", "v": 1}] * 3
    s = _summary("line", {"x_axis_name": "d", "y_axis_name": "v"}, rows, limit=3)
    assert s.facts[0].startswith("rows: 3 (the cap of 3: the chart reads no more rows")


def test_a_smaller_limit_is_not_the_dashboard_cap():
    rows = [{"d": "2026-10-01", "v": 1}] * 3
    s = _summary("line", {"x_axis_name": "d", "y_axis_name": "v"}, rows, limit=3)
    assert s.facts[0] == "rows: 3 (the --limit of 3; the dashboard reads up to 10000)"


def test_a_full_table_page_has_no_cap():
    rows = [{"d": "2026-10-01", "v": 1}] * 25
    assert _summary("table", {}, rows, limit=25).facts == ["rows: 25"]


def test_line_summary_counts_x_series_and_dropped_rows():
    rows = [
        {"d": "2026-10-01", "v": 1, "w": 2},
        {"d": "2026-10-02", "v": "n/a", "w": 3},
        {"d": None, "v": 4, "w": 5},
    ]
    config = {"x_axis_name": "d", "y_axis_name": "v", "y1_axis_name": "w"}
    s = _summary("line", config, rows)
    assert s.facts == ["rows: 3", "x: d: time axis, 2 values", "series: 2 (v, w)"]
    # option.ts:431, counted for each Y column
    assert s.notes == ["3 rows have no number or no d: they are not drawn."]


def test_bars_draw_a_time_x_as_categories_and_name_the_fold():
    rows = [{"d": "2026-10-01", "n": f"net{i}", "v": i + 1} for i in range(10)]
    config = {"x_axis_name": "d", "y_axis_name": "v", "series_by": "n"}
    s = _summary("stackedbar", config, rows)
    assert "x: d: time axis, drawn as categories, 1 values" in s.facts
    assert "series: 10 values of n: the 7 largest + 'Other'" in s.facts


def test_log_scale_with_a_zero_falls_back_to_linear():
    rows = [{"d": 1, "v": 0}, {"d": 2, "v": 5}]
    s = _summary("line", {"x_axis_name": "d", "y_axis_name": "v", "scale": "log"}, rows)
    assert "A log scale needs values above 0: the linear scale is shown." in s.notes


def test_band_notes_of_the_web():
    rows = [{"d": 1, "v": 1}, {"d": 1, "v": 3}]
    base = {"x_axis_name": "d", "y_axis_name": "v"}
    stacked = _summary("stackedbar", {**base, "uncertainty": "sd"}, rows)
    assert "Bands and error bars do not show on stacked bars." in stacked.notes
    count = _summary("bar", {**base, "uncertainty": "sd", "combine": "count"}, rows)
    assert "The band does not show when the rows are combined by count." in count.notes
    median = _summary(
        "line", {**base, "uncertainty": "quantiles", "combine": "sum"}, rows
    )
    assert "With this band, each point is the median of its rows." in median.notes
    cum = _summary("line", {**base, "uncertainty": "sd", "transform": "cum"}, rows)
    assert (
        "The band does not carry through a running total or a change rate." in cum.notes
    )


def test_order_by_y_keeps_a_time_order():
    rows = [{"d": "2026-10-01", "v": 1}]
    s = _summary("bar", {"x_axis_name": "d", "y_axis_name": "v", "order_by": "y"}, rows)
    assert "d is a time or a number: the points keep the order of d." in s.notes


def test_long_category_labels_are_a_note():
    rows = [{"who": "A protocol with a long name", "v": 1}, {"who": "short", "v": 2}]
    s = _summary("bar", {"x_axis_name": "who", "y_axis_name": "v"}, rows)
    assert any(
        n.startswith("long labels: the longest x label has 27 characters")
        for n in s.notes
    )
    short = _summary("bar", {"x_axis_name": "who", "y_axis_name": "v"}, rows[1:])
    assert not any(n.startswith("long labels") for n in short.notes)


def test_horizontal_bars_cut_labels_at_26_and_need_no_horizontal_hint():
    label = "A protocol with a long name"  # 27 characters
    rows = [{"who": label, "v": 1}, {"who": "A name of 20 chars xx", "v": 2}]
    config = {"x_axis_name": "who", "y_axis_name": "v"}
    [vertical] = [
        n for n in _summary("bar", config, rows).notes if n.startswith("long labels")
    ]
    assert "cuts labels to 14 characters" in vertical
    assert "Consider --horizontal" in vertical
    [flat] = [
        n
        for n in _summary("bar", {**config, "horizontal": True}, rows).notes
        if n.startswith("long labels")
    ]
    assert "cuts labels to 26 characters" in flat
    assert "--horizontal" not in flat
    # 20 characters: cut when vertical, shown whole when horizontal.
    short = [{"who": "A name of 20 chars xx", "v": 2}]
    assert any(
        n.startswith("long labels") for n in _summary("bar", config, short).notes
    )
    assert not any(
        n.startswith("long labels")
        for n in _summary("bar", {**config, "horizontal": True}, short).notes
    )


def test_pie_keeps_six_slices_and_counts_the_skipped_rows():
    rows = [{"k": f"k{i}", "v": i + 1} for i in range(8)] + [{"k": "x", "v": "n/a"}]
    s = _summary("pie", {"x_axis_name": "k", "y_axis_name": "v"}, rows)
    assert "slices: 8 values of k: the 5 largest + 'Other'" in s.facts
    assert "1 rows have no number in v: they are not counted." in s.notes
    assert any(
        n.startswith("A pie draws at most 6 slices: the other 3") for n in s.notes
    )
    six = _summary("pie", {"x_axis_name": "k"}, rows[:6])
    assert "slices: 6" in six.facts


def test_scatter_groups_dots_and_size_notes():
    rows = [
        {"x": i, "y": i + 1, "g": f"g{i % 5}", "s": -1 if i == 0 else i}
        for i in range(10)
    ] + [
        {"x": 1, "y": None, "g": "g0", "s": None},
        {"x": 2, "y": 3, "g": "g1", "s": "?"},
    ]
    config = {"x_axis_name": "x", "y_axis_name": "y", "series_by": "g", "size_by": "s"}
    s = _summary("scatter", config, rows)
    assert "x: x: number axis, 11 dots" in s.facts
    assert "groups: 5 values of g: the 2 largest + 'Other'" in s.facts
    assert "1 rows have no x or no number in y: they are not drawn." in s.notes
    assert "1 rows have no number in s: they have the smallest dot." in s.notes
    assert "Dot area shows values of 0 and above: 1 rows are below 0." in s.notes


def test_scatter_log_scale_hides_the_fit():
    rows = [{"x": 1, "y": 2}, {"x": 2, "y": 3}]
    s = _summary(
        "scatter", {"x_axis_name": "x", "y_axis_name": "y", "scale": "log"}, rows
    )
    assert s.notes == ["The fit needs a linear Y scale: it is not shown."]


def test_histogram_counts_the_rows_with_no_number():
    rows = [{"v": 1}, {"v": "x"}, {"v": 3}]
    s = _summary("histogram", {"x_axis_name": "v"}, rows)
    assert s.facts == ["rows: 3", "values: 2 numbers in v, 1 to 3"]
    assert s.notes == ["1 rows have no number in v."]


def test_range_drops_rows_that_miss_a_value():
    rows = [
        {"d": "2026-10-01", "lo": 1, "hi": 2},
        {"d": "2026-10-02", "lo": None, "hi": 2},
    ]
    config = {
        "x_axis_name": "d",
        "range_shape": "range",
        "low_name": "lo",
        "high_name": "hi",
    }
    s = _summary("range", config, rows)
    assert "x: d: time axis, 1 range marks" in s.facts
    assert s.notes == ["1 rows miss a value of the range: they are not drawn."]


def test_value_tile_shows_the_first_row():
    s = _summary("value", {"y_axis_name": "v"}, [{"v": "n/a"}, {"v": 2}])
    assert "value: n/a (v of the first row)" in s.facts
    assert s.notes == [
        "The first row's v is not a number: the tile shows 'n/a' as text."
    ]
