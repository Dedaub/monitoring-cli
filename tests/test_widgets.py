"""The widget rules must give the same answers as the web app.

The expected SQL strings below are the output of the frontend's own
`widgetRowsSql` (widgetConfig.ts), run under node for the same inputs. A
change to the Python that changes one byte of the SQL fails here.
"""

import datetime
import time

import pytest

from monitoring_cli import widgets

SINCE = datetime.datetime(2026, 10, 1, 12, 34, 56, 789000, tzinfo=datetime.UTC)


# --- config keys -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("camel", "snake"),
    [
        ("xAxisName", "x_axis_name"),
        ("y1AxisName", "y1_axis_name"),
        ("q1Name", "q1_name"),
        ("bandK", "band_k"),
        ("histView", "hist_view"),
        ("x_axis_name", "x_axis_name"),
        ("timeframe", "timeframe"),
    ],
)
def test_camel_to_snake_matches_the_web_client(camel, snake):
    assert widgets.camel_to_snake(camel) == snake


def test_every_known_key_is_snake_case():
    for key in widgets.CONFIG_KEYS:
        assert widgets.camel_to_snake(key) == key


def test_normalize_config_converts_camel_case_keys():
    assert widgets.normalize_config(
        {"xAxisName": "day", "y_label": "Fee", "sortingOrder": "DESC"}
    ) == {"x_axis_name": "day", "y_label": "Fee", "sorting_order": "DESC"}


def test_clean_config_drops_empty_values():
    assert widgets.clean_config(
        {"x_axis_name": "day", "y1_axis_name": "None", "prefix": "", "fit": None}
    ) == {"x_axis_name": "day"}


# --- config checks -----------------------------------------------------------------


def test_valid_config_has_no_problems():
    config = {
        "x_axis_name": "day",
        "y_axis_name": "fee",
        "x_label": "**Day**",
        "y_label": "Fee $\\mu$",
        "timeframe": "7d",
        "sorting_order": "ASC",
        "decimals": "2",
        "fit": False,
        "bins": 20,
    }
    assert widgets.config_problems("line", config) == []


def test_unknown_key_is_a_problem_with_a_hint():
    [problem] = widgets.config_problems("line", {"x_axis": "day"})
    assert "Unknown config key 'x_axis'" in problem
    assert "x_axis_name" in problem


def test_unknown_type_is_a_problem():
    [problem] = widgets.config_problems("donut", {})
    assert "Unknown widget type 'donut'" in problem


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("sorting_order", "UP"),
        ("timeframe", "90d"),
        ("range_shape", "boxes"),
        ("number_format", "money"),
        ("fit", "yes"),
        ("bins", "many"),
        ("x_axis_name", 3),
        ("x_label", 5),
    ],
)
def test_bad_values_are_problems(key, value):
    [problem] = widgets.config_problems("line", {key: value})
    assert key in problem


def test_old_timeframe_aliases_stay_valid():
    assert widgets.config_problems("line", {"timeframe": "1m"}) == []


def test_label_longer_than_120_characters_is_a_problem():
    assert widgets.config_problems("line", {"x_label": "a" * 120}) == []
    [problem] = widgets.config_problems("line", {"x_label": "a" * 121})
    assert "121 characters" in problem


def test_labels_on_a_type_without_axes_are_a_note():
    assert widgets.config_notes("pie", {"x_label": "Day"}) == [
        "x_label has no effect: a pie widget has no axes."
    ]
    assert widgets.config_notes("line", {"x_label": "Day"}) == []


# --- missingAxis ---------------------------------------------------------------------


@pytest.mark.parametrize("widget_type", ["line", "bar", "stackedbar", "linebar"])
def test_line_and_bar_need_x_then_y(widget_type):
    assert "X-axis" in widgets.missing_axis(widget_type, {})
    assert "Y-axis" in widgets.missing_axis(widget_type, {"x_axis_name": "d"})
    assert (
        widgets.missing_axis(widget_type, {"x_axis_name": "d", "y_axis_name": "v"})
        is None
    )


def test_scatter_needs_x_and_y():
    assert "X column" in widgets.missing_axis("scatter", {})
    assert "Y column" in widgets.missing_axis("scatter", {"x_axis_name": "d"})


@pytest.mark.parametrize(
    ("widget_type", "text"),
    [("histogram", "column to bin"), ("pie", "column to count")],
)
def test_histogram_and_pie_need_x(widget_type, text):
    assert text in widgets.missing_axis(widget_type, {})
    assert widgets.missing_axis(widget_type, {"x_axis_name": "d"}) is None


def test_value_needs_y():
    assert "column to show" in widgets.missing_axis("value", {})
    assert widgets.missing_axis("value", {"y_axis_name": "v"}) is None


def test_table_needs_nothing():
    assert widgets.missing_axis("table", {}) is None


def test_range_needs_x_and_the_columns_of_its_shape():
    assert "X-axis" in widgets.missing_axis("range", {})
    # The default shape is candle: open, high, low, close.
    assert "open column" in widgets.missing_axis("range", {"x_axis_name": "d"})
    box = {"x_axis_name": "d", "range_shape": "box", "low_name": "lo", "q1_name": "q1"}
    assert "median column" in widgets.missing_axis("range", box)
    done = {
        "x_axis_name": "d",
        "range_shape": "range",
        "low_name": "a",
        "high_name": "b",
    }
    assert widgets.missing_axis("range", done) is None


# --- columnsNotInQuery -----------------------------------------------------------------


def test_columns_not_in_query_lists_the_lost_columns_once():
    config = {"x_axis_name": "day", "y_axis_name": "gone", "series_by": "gone"}
    assert widgets.columns_not_in_query(config, ["day", "fee"], "line") == ["gone"]


def test_columns_not_in_query_is_empty_when_columns_are_unknown():
    assert widgets.columns_not_in_query({"x_axis_name": "day"}, [], "line") == []


def test_columns_not_in_query_ignores_none_and_other_types_keys():
    config = {
        "x_axis_name": "day",
        "y1_axis_name": "None",
        "size_by": "s",
        "low_name": "lo",
    }
    # size_by counts only for a scatter, the range columns only for a range.
    assert widgets.columns_not_in_query(config, ["day"], "line") == []
    assert widgets.columns_not_in_query(config, ["day"], "scatter") == ["s"]


def test_columns_not_in_query_reads_the_range_shape():
    config = {
        "x_axis_name": "d",
        "range_shape": "range",
        "low_name": "lo",
        "high_name": "hi",
        "open_name": "op",
        "volume_name": "vol",
    }
    assert widgets.columns_not_in_query(config, ["d", "lo"], "range") == ["hi", "vol"]


# --- the SQL (expected text from the frontend's widgetRowsSql) -----------------------


def test_sql_ref_chart_with_time_window_and_network():
    sql = widgets.widget_rows_sql(
        table="alice::My Query",
        network="base",
        columns=["day", "fee"],
        time_column="day",
        since=SINCE,
        order_column="day",
        sorting_order="ASC",
        chart_limit=500,
    )
    assert sql == (
        '--#default_network="base"\n'
        'WITH q AS (SELECT * FROM {{ ref(table="alice::My Query") }} r\n'
        "WHERE r.\"day\" > '2026-10-01T12:34:56.789Z'\n"
        'ORDER BY r."day" DESC\n'
        "LIMIT 500)\n"
        'SELECT * FROM q ORDER BY q."day" ASC'
    )


def test_sql_text_ending_in_semicolon_and_comment_keeps_first_by_y():
    sql = widgets.widget_rows_sql(
        table="q",
        query_text="SELECT 1 AS day, 2 AS fee\nLIMIT 200; -- note",
        columns=["day", "fee"],
        order_column="fee",
        sorting_order="DESC",
        keep_first=True,
        chart_limit=500,
    )
    assert sql == (
        "WITH q AS (SELECT * FROM (\n"
        "SELECT 1 AS day, 2 AS fee\n"
        "LIMIT 200\n"
        ") r\n"
        'ORDER BY r."fee" DESC NULLS LAST\n'
        "LIMIT 500)\n"
        'SELECT * FROM q ORDER BY q."fee" DESC NULLS LAST'
    )


def test_sql_column_with_a_quote_and_the_texts_network_line():
    sql = widgets.widget_rows_sql(
        table="q",
        query_text='--#default_network="arbitrum"\nselect 1 as "a""b" /* tail */',
        network="ethereum",
        columns=['a"b'],
        order_column='a"b',
        sorting_order="ASC",
    )
    assert sql == (
        '--#default_network="arbitrum"\n'
        "SELECT * FROM (\n"
        '--#default_network="arbitrum"\n'
        'select 1 as "a""b"\n'
        ") r\n"
        'ORDER BY r."a""b" ASC'
    )


def test_sql_skips_a_duplicate_column_and_a_brace():
    sql = widgets.widget_rows_sql(
        table="x",
        columns=["d", "d", "v{x}"],
        time_column="d",
        since=SINCE,
        order_column="v{x}",
        sorting_order="ASC",
        chart_limit=500,
    )
    assert sql == 'SELECT * FROM {{ ref(table="x") }} r'


def test_sql_jinja_comment_at_the_end():
    sql = widgets.widget_rows_sql(
        table="x",
        query_text="select 1 {# a #};\n{# b #}",
        columns=[],
        order_column="z",
        sorting_order="DESC",
        chart_limit=10,
    )
    assert sql == (
        "WITH q AS (SELECT * FROM (\n"
        "select 1\n"
        ") r\n"
        'ORDER BY r."z" ASC\n'
        "LIMIT 10)\n"
        'SELECT * FROM q ORDER BY q."z" DESC'
    )


def test_subquery_body_matches_the_frontend():
    assert widgets.subquery_body("-- nothing here\n;") is None
    assert widgets.subquery_body("select 1\n-- final note") == "select 1\n-- final note"
    assert widgets.widget_rows_sql(table="x", query_text="-- nothing here\n;") == (
        'SELECT * FROM {{ ref(table="x") }} r'
    )


def test_quote_identifier_refuses_a_brace():
    assert widgets.quote_identifier('a"b') == '"a""b"'
    with pytest.raises(ValueError):
        widgets.quote_identifier("{{x}}")


def test_widget_rows_sqls_has_no_text_form_for_an_empty_text():
    read = {"table": "x"}
    assert widgets.widget_rows_sqls(read, "  -- only a comment\n") == (
        'SELECT * FROM {{ ref(table="x") }} r',
        None,
    )


@pytest.fixture
def utc_local(monkeypatch):
    """timeframe_start counts in local wall time: pin the zone."""
    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


@pytest.mark.parametrize(
    ("timeframe", "start"),
    [
        ("24h", "2026-03-30T10:00:00"),
        ("7d", "2026-03-24T10:00:00"),
        # Date.setMonth: 31 March - 1 month = "31 February" = 3 March.
        ("30d", "2026-03-03T10:00:00"),
        ("60d", "2026-01-30T10:00:00"),
        ("1y", "2025-03-31T10:00:00"),
        ("bogus", "2026-03-31T10:00:00"),
    ],
)
def test_timeframe_start_matches_the_browser(utc_local, timeframe, start):
    now = datetime.datetime(2026, 3, 31, 10, 0, tzinfo=datetime.UTC)
    got = widgets.timeframe_start(timeframe, now)
    assert got == datetime.datetime.fromisoformat(start).replace(tzinfo=datetime.UTC)


def test_widget_sqls_of_reads_the_owner_query_in_the_timeframe(utc_local):
    query = {
        "query_id": 9,
        "query_name": "Fees",
        "owner": {"username": "alice", "entity_id": 7},
        "default_network": "ethereum",
        "query_text": "select day, fee from t;",
    }
    columns = [{"name": "day", "type": "timestamp"}, {"name": "fee", "type": "numeric"}]
    config = {"x_axis_name": "day", "y_axis_name": "fee", "sorting_order": "ASC"}
    now = datetime.datetime(2026, 10, 8, 12, 34, 56, 789000, tzinfo=datetime.UTC)
    ref, text = widgets.widget_sqls_of(
        query=query,
        columns=columns,
        widget_type="line",
        config=config,
        timeframe="7d",
        now=now,
    )
    assert ref == (
        '--#default_network="ethereum"\n'
        'WITH q AS (SELECT * FROM {{ ref(table="alice::Fees") }} r\n'
        "WHERE r.\"day\" > '2026-10-01T12:34:56.789Z'\n"
        'ORDER BY r."day" DESC\n'
        "LIMIT 500)\n"
        'SELECT * FROM q ORDER BY q."day" ASC'
    )
    assert text is not None
    assert text.startswith(
        '--#default_network="ethereum"\nWITH q AS (SELECT * FROM (\nselect day, fee from t\n) r'
    )


def test_widget_sqls_of_orders_bars_by_y_but_not_a_time_x():
    query = {"query_name": "Q", "owner": {}, "query_text": None}
    config = {
        "x_axis_name": "who",
        "y_axis_name": "n",
        "order_by": "y",
        "sorting_order": "DESC",
    }
    columns = [{"name": "who", "type": "text"}, {"name": "n", "type": "bigint"}]
    ref, text = widgets.widget_sqls_of(
        query=query, columns=columns, widget_type="bar", config=config
    )
    assert 'ORDER BY r."n" DESC NULLS LAST' in ref
    assert text is None
    timed = [{"name": "who", "type": "timestamp with time zone"}, columns[1]]
    ref, _ = widgets.widget_sqls_of(
        query=query, columns=timed, widget_type="bar", config=config
    )
    assert 'ORDER BY r."who" ASC' in ref  # the X order, newest 500 first


def test_a_table_sorts_all_rows():
    query = {"query_name": "Q", "owner": {"username": "bob"}}
    ref, _ = widgets.widget_sqls_of(
        query=query,
        columns=[],
        widget_type="table",
        config={"x_axis_name": "d", "sorting_order": "DESC"},
    )
    assert ref == 'SELECT * FROM {{ ref(table="bob::Q") }} r\nORDER BY r."d" DESC'


# --- saving and layout -----------------------------------------------------------------


def test_default_widget_size():
    assert widgets.default_widget_size("table") == {"width": 8, "height": 6}
    assert widgets.default_widget_size("value") == {"width": 4, "height": 2}
    assert widgets.default_widget_size("range") == {"width": 6, "height": 5}
    assert widgets.default_widget_size("line") == {"width": 4, "height": 4}


def test_chart_category():
    assert (
        widgets.chart_category({"is_scheduled": True}, notify=False) == "MATERIALIZED"
    )
    assert (
        widgets.chart_category({"is_scheduled": False}, notify=True) == "MATERIALIZED"
    )
    assert widgets.chart_category({"is_scheduled": False}, notify=False) == "VIEW"


def test_layout_problems():
    good = [{"widget_id": 1, "x": 8, "y": 0, "width": 4, "height": 4}]
    assert widgets.layout_problems(good) == []
    assert widgets.layout_problems({"widget_id": 1}) != []
    bad = [
        {"widget_id": 1, "x": 10, "y": 0, "width": 4, "height": 4},
        {"widget_id": 2, "x": 0, "y": 0, "width": 13, "height": 4},
        {"widget_id": 3, "x": 0, "y": 0, "width": 4, "height": 4, "z": 1},
        {"widget_id": 3, "x": 0, "y": 0, "width": 4, "height": True},
        {"widget_id": 4, "x": 0, "y": 0, "width": 4, "height": 4},
        {"widget_id": 4, "x": 0, "y": 0, "width": 4, "height": 4},
    ]
    problems = widgets.layout_problems(bad)
    assert any("Item 0: x + width" in p for p in problems)
    assert any("Item 1: width must be from 1 to 12" in p for p in problems)
    assert any("Item 2 has unknown keys: z" in p for p in problems)
    assert any("Item 3: height must be an integer" in p for p in problems)
    assert any("Item 5: widget 4 occurs more than one time" in p for p in problems)


# --- links -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("api", "app"),
    [
        ("https://api.dedaub.com", "https://app.dedaub.com"),
        ("https://st-api.dedaub.com", "https://st-watchdog.dedaub.com"),
        ("https://st2.api.dedaub.com", "https://st2.watchdog.dedaub.com"),
        ("http://localhost:8000", "http://localhost:8000"),
    ],
)
def test_app_url_follows_the_profile(api, app):
    assert widgets.app_url(api) == app


def test_links():
    assert (
        widgets.widget_link("https://api.dedaub.com", 12)
        == "https://app.dedaub.com/widget/12"
    )
    assert (
        widgets.dashboard_link("https://api.dedaub.com", 5)
        == "https://app.dedaub.com/dashboard/5"
    )


# --- series overflow -------------------------------------------------------------


def _rows(n: int) -> list[dict]:
    return [
        {"hour": "2026-10-31T10:00:00Z", "network": f"net{i}", "tps": i}
        for i in range(n)
    ]


def test_series_notes_warn_above_the_palette():
    notes = widgets.series_notes("line", {"series_by": "network"}, _rows(9))
    assert len(notes) == 1
    assert "9 values" in notes[0]
    assert "7 largest" in notes[0]
    assert "'Other'" in notes[0]


def test_series_notes_accept_the_palette_size():
    assert widgets.series_notes("line", {"series_by": "network"}, _rows(8)) == []


def test_series_notes_count_null_as_one_value():
    rows = _rows(8) + [{"network": None}, {"network": None}]
    assert len(widgets.series_notes("bar", {"series_by": "network"}, rows)) == 1


@pytest.mark.parametrize("widget_type", ["table", "value", "pie"])
def test_series_notes_skip_types_without_series(widget_type):
    assert widgets.series_notes(widget_type, {"series_by": "network"}, _rows(12)) == []


def test_series_notes_need_series_by():
    assert widgets.series_notes("line", {}, _rows(12)) == []


# --- arrange -----------------------------------------------------------------------


def _w(widget_id: int, widget_type: str, y: int = 0, x: int = 0, **extra) -> dict:
    return {"widget_id": widget_id, "type": widget_type, "x": x, "y": y, **extra}


def _places(layout: list[dict]) -> dict[int, tuple[int, int, int, int]]:
    return {i["widget_id"]: (i["x"], i["y"], i["width"], i["height"]) for i in layout}


def test_auto_layout_of_no_widgets_is_empty():
    assert widgets.auto_layout([]) == []


def test_auto_layout_builds_the_network_dashboard():
    # Created in one column (y = 0, 2, 4, …), as the server places new widgets.
    types = ["value"] * 6 + ["line", "line", "bar", "bar", "stackedbar", "pie", "table"]
    layout = widgets.auto_layout([_w(100 + i, t, y=2 * i) for i, t in enumerate(types)])
    places = {k - 100: v for k, v in _places(layout).items()}
    assert [places[i] for i in range(6)] == [(2 * i, 0, 2, 2) for i in range(6)]
    assert places[6] == (0, 2, 6, 5) and places[7] == (6, 2, 6, 5)
    assert places[8] == (0, 7, 6, 4) and places[9] == (6, 7, 6, 4)
    assert places[10] == (0, 11, 8, 4) and places[11] == (8, 11, 4, 4)
    assert places[12] == (0, 15, 12, 6)
    assert widgets.layout_problems(layout) == []


@pytest.mark.parametrize(("n", "width"), [(1, 4), (3, 4), (4, 3), (5, 2), (6, 2)])
def test_auto_layout_tile_width(n, width):
    places = _places(widgets.auto_layout([_w(i, "value", y=i) for i in range(n)]))
    assert {p[2] for p in places.values()} == {width}


def test_auto_layout_wraps_tiles_after_six():
    places = _places(widgets.auto_layout([_w(i, "value", y=i) for i in range(8)]))
    assert places[6] == (0, 2, 4, 2) and places[7] == (4, 2, 4, 2)


def test_auto_layout_keeps_the_order_and_puts_tables_last():
    given = [_w(1, "table", y=0), _w(2, "bar", y=6), _w(3, "value", y=10)]
    places = _places(widgets.auto_layout(given))
    assert places[3] == (0, 0, 4, 2)
    assert places[2] == (0, 2, 12, 4)
    assert places[1] == (0, 6, 12, 6)


def test_auto_layout_lone_pie_is_half_width():
    places = _places(widgets.auto_layout([_w(1, "pie")]))
    assert places[1] == (0, 0, 6, 4)


def test_auto_layout_puts_an_alerts_widget_at_full_width():
    places = _places(
        widgets.auto_layout([_w(1, "line", category="ALERT"), _w(2, "bar", y=1)])
    )
    assert places[2] == (0, 0, 12, 4)
    assert places[1] == (0, 4, 12, 6)
