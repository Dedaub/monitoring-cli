# Widgets and dashboards (CLI only)

A **widget** is a saved chart, table or single value of one query. A **dashboard** is a grid of widgets.
A widget can be on no dashboard, or on many. These commands need a shell with the `dedaub-monitoring`
CLI. The CLI runs the same checks and the same SQL as the web app's Visualize tab, so a widget that
passes `check-widget` draws on the dashboard.

## Flow

1. **Pick one widget** for the saved query (table below). Read its columns: `query-columns --id <QID>`.
2. `check-widget --query-id <QID> --type <T> --x <COL> --y <COL> …` — exit 0, or one line per problem.
3. `preview-widget` with the same flags — the rows that the chart will draw. 0 rows: widen `--timeframe`.
4. `create-widget` with the same flags — prints the widget id and `https://app.dedaub.com/widget/<id>`.
5. Ask the user about a dashboard: `list-dashboards`, then `add-widget --id <WID> --dashboard-id <DID>`,
   or `create-dashboard "<Name>"` first.

Each write prints its link. Give the user the link. Never delete or change a widget or dashboard that you
did not create in this session unless the user asks.

## Which widget

| The query returns | Widget |
|-------------------|--------|
| A time column + one or more numbers (daily volume, fees) | `line` (`--x <time> --y <num>`, `--y1` for a second number) |
| Categories + a number (top protocols, by token) | `bar` (`--x <category> --y <num>`); a breakdown over time → `stackedbar` with `--series-by` |
| Two numbers per row (size vs fee) | `scatter` (`--x --y`) |
| One number to bin (a distribution) | `histogram` (`--x <num>`) |
| Shares of a whole | `pie` (`--x <category>`, counts rows per value; `--y` sums a number) |
| One headline number | `value` (`--y <num>`) |
| Low/high, OHLC or quartiles per row | `range` (`--x`, `range_shape` + its columns) |
| Rows to read (alerts, transfers) | `table` |

## Judge first: chart, aggregate, or no widget

Decide case by case. Do not force a chart.

- **No widget.** The rows have nothing to plot: a list of alerts, addresses, hashes or free text with no
  number to measure, or a lookup table. Tell the user why in one sentence, and make no widget.
- **Aggregate first.** The rows are row-level events (one row per transfer, swap, tx or log), and a chart
  needs a count or a sum per day or per category. Make a derived query next to the saved one, then put
  the widget on it:

  ```bash
  # ref() finds only a query with run settings (on the ethereum slot). Without them the derived query
  # fails with "does not exist, or has not been shared with you". VIEW gives run settings and
  # materializes nothing: the saved query is re-evaluated each time the derived one reads it.
  dedaub-monitoring set-config --id <QID> --network ethereum --materialize VIEW
  dedaub-monitoring create-query /<Folder>/<name>_by_day
  dedaub-monitoring write-query --id <NEW_QID> "SELECT date_trunc('day', r.block_time) AS day,
    count(*) AS transfers, sum(r.amount_usd) AS volume_usd
    FROM {{ ref(query_id=<QID>) }} r GROUP BY 1 ORDER BY 1"
  dedaub-monitoring run-query --id <NEW_QID> --duration 7d
  ```

  `ref(query_id=…)` reads the saved query through its run settings (the `set-config` line above), so a
  later edit of the saved query reaches the derived one. Skip `set-config` when `get-config --id <QID>`
  already shows run settings: do not overwrite an alert's `INCREMENTAL` config. Name every output
  column with `AS`. Copy the saved query's `--#default_network=` first line when it has one.
- **Chart directly.** The rows already have a time or category column and a number: use the table above.

## Types and the columns each one needs (`missingAxis`)

| Type | Needs |
|------|-------|
| `line`, `bar`, `stackedbar`, `linebar` | `x_axis_name` and `y_axis_name` |
| `scatter` | `x_axis_name` and `y_axis_name` |
| `histogram` | `x_axis_name` (the column to bin) |
| `pie` | `x_axis_name` (the column to count) |
| `range` | `x_axis_name` and the columns of `range_shape`: `range` → `low_name`, `high_name`; `candle` (default) → `open_name`, `high_name`, `low_name`, `close_name`; `box` → `low_name`, `q1_name`, `median_name`, `q3_name`, `high_name` |
| `value` | `y_axis_name` (the column to show) |
| `table` | nothing |

**Column check (`columnsNotInQuery`).** Each column that the config names must be a column of the query:
`x_axis_name`, `y_axis_name`, `y1_axis_name`, `series_by`, `lower_name`, `upper_name`, `stderr_name`,
`size_by` (scatter only), and for `range` the shape's columns plus `volume_name`. Column names are
case-sensitive. `--force` on `create-widget`/`update-widget` skips only this check.

## Config keys

The API stores snake_case keys. `--config FILE|-` takes a JSON object in camelCase or snake_case; the flags
win over it. A new widget starts with `{"timeframe": "30d", "sorting_order": "ASC", "decimals": "2"}`.

| Flag | Key | Values |
|------|-----|--------|
| `--x` | `x_axis_name` | column |
| `--y` | `y_axis_name` | column |
| `--y1` | `y1_axis_name` | column (second Y; `linebar` draws it as the line) |
| `--series-by` | `series_by` | column: one series for each value (max 8; scatter: colour) |
| `--x-label` | `x_label` | label text (see Labels) |
| `--y-label` | `y_label` | label text |
| `--timeframe` | `timeframe` | `24h`, `7d`, `30d`, `60d` |
| | `sorting_order` | `ASC`, `DESC` |
| | `order_by` | `x` (default), `y`: the X categories in the order of Y (line, bar, stackedbar, linebar; not for a time X, nor for a number X on a line) |
| | `combine` | `sum`, `mean`, `median`, `min`, `max`, `count` (rows that share an X) |
| | `line_style` | `line`, `area`, `step` (line) |
| | `transform` | `none`, `ma7`, `mean`, `ewma`, `bollinger` (line), `cum`, `index`, `pct` |
| | `uncertainty` | `none`, `sd`, `ci95`, `minmax`, `quantiles` (line), `columns` (+ `lower_name`, `upper_name`), `stderr` (+ `stderr_name`) |
| | `scale` | `linear`, `log` |
| | `number_format` | `compact`, `full`, `currency`, `percent` |
| | `hist_view` | `counts`, `ecdf` (histogram) |
| | `range_shape` | `range`, `candle`, `box` |
| | `color_scale` | `groups`, `scale` (scatter with `series_by`) |
| | `size_by` | column (scatter dot size) |
| | `volume_name` | column (candle volume) |
| | `prefix`, `suffix`, `reference_label` | text |
| | `decimals`, `reference_line`, `bins`, `window`, `band_k`, `anomaly_k` | number (as text, e.g. `"2"`) |
| | `fit`, `anomalies`, `trend`, `correlation` | `true` / `false` |

`--clear KEY` (on `update-widget`) removes a key from the saved config.

## Labels (`x_label`, `y_label`, and the widget title `--label`)

- Inline Markdown: `**bold**`, `*italic*` or `_italic_`, `` `code` ``. No links, no blocks, no HTML.
- TeX: `$x$` inline, `$$\frac{a}{b}$$` display. `$` opens math only before a non-space: "$5 and $10" stays text.
- `\$` writes a dollar sign.
- Axis labels: 120 characters max, and only the charts with axes show them: `line`, `bar`, `stackedbar`,
  `linebar`, `scatter`, `histogram`, `range`.

## Timeframes and rows

`timeframe` filters the query's first time column (`timestamp…` or `date`) to the last 24h / 7d / 30d (one
calendar month) / 60d. A chart reads the newest 500 rows by its X column, then sorts them; a table reads 25
rows a page. A dashboard's own time range wins over the widget's. The rows come from the query's table
through `ref()`; a query that `ref()` cannot find (no run settings) reads its text. So schedule the query
(`set-config`) for a fast widget on big data.

## Commands (one example each)

```bash
dedaub-monitoring check-widget   --query-id 123 --type line --x day --y volume_usd --y-label 'Volume (\$)'
dedaub-monitoring preview-widget --query-id 123 --type line --x day --y volume_usd --timeframe 7d
dedaub-monitoring preview-widget --id 456 --sql                       # print the SQL, do not run it
dedaub-monitoring create-widget  --query-id 123 --type line --x day --y volume_usd --label '**Daily volume**'
dedaub-monitoring update-widget  --id 456 --type bar --clear y_label
dedaub-monitoring get-widget     --id 456
dedaub-monitoring list-widgets   --query-id 123
dedaub-monitoring delete-widget  --id 456                             # leaves every dashboard
dedaub-monitoring list-dashboards
dedaub-monitoring get-dashboard  --id 78                              # the dashboard and its widgets (JSON)
dedaub-monitoring create-dashboard "DEX volume" --description 'Daily DEX volume'
dedaub-monitoring update-dashboard --id 78 --name "DEX volume (Base)"
dedaub-monitoring add-widget     --id 456 --dashboard-id 78           # under the lowest widget
dedaub-monitoring remove-widget  --id 456 --dashboard-id 78           # off this dashboard only
dedaub-monitoring set-layout     --id 78 --layout layout.json         # [{"widget_id", "x", "y", "width", "height"}]
dedaub-monitoring set-default-dashboard --id 78
dedaub-monitoring delete-dashboard --id 78                            # widgets stay; --delete-widgets removes them
```

A public dashboard takes only widgets of public queries. The grid has 12 columns; `x + width` ≤ 12.
