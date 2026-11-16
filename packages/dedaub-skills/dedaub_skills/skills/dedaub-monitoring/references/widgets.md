# Widgets and dashboards (CLI only)

A **widget** is a saved chart, table or single value of one query. A **dashboard** is a grid of widgets.
A widget can be on no dashboard, or on many. These commands need a shell with the `dedaub-monitoring`
CLI, version 0.6.0 or later (`dedaub-monitoring --version`; an older CLI has no widget commands). The
chart summary, the option flags, sharing, publishing and the pictures need 0.9.0 or later. The CLI runs
the same checks and the same SQL as the web app's Visualize tab, so a widget that passes `check-widget`
draws on the dashboard. An HTTP 500 on a widget command can mean that the server does
not have the backend of that command yet: the error names the CLI version. Do not retry it in a loop.

## Flow

1. **Pick one widget** for the saved query (table below). Read its columns: `query-columns --id <QID>`.
2. `check-widget --query-id <QID> --type <T> --x <COL> --y <COL> …` — exit 0, or one line per problem.
   It does not run the query. It prints the X axis kind from the column types, and a `Note:` for each
   key that the type ignores and for each Y column that is not a number type.
3. `preview-widget` with the same flags — reads the rows as the dashboard does and prints what the chart
   draws (see "What preview-widget tells you"). Read each `Note:` and fix the config or the query.
   **See the chart:** `render-widget` with the same flags writes a PNG that the web app's own chart code
   drew (see "See the chart"). If you can read images, open it and check it: axis labels, an empty plot,
   too many series, labels that overlap. Fix the config, then render again.
4. `create-widget` with the same flags — prints the widget id and `https://app.dedaub.com/widget/<id>`.
5. Ask the user about a dashboard: `list-dashboards`, then `add-widget --id <WID> --dashboard-id <DID>`,
   or `create-dashboard "<Name>"` first.
6. After the last widget is on the dashboard, run `arrange-dashboard --id <DID>` (see Dashboard layout).

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

## What preview-widget tells you

`preview-widget` reads the rows that the dashboard reads (a chart: up to 10,000 rows through the API's
shared 15-minute cache, `--refresh` reads the database again; a table: one page of 25 rows). It prints 20
sample rows (`--show-rows N`, `0` for none), then one line for each fact, then one `Note:` line for each
web chart note:

```
rows: 2400
x: day: time axis, 30 values
series: 9 values of network: the 7 largest + 'Other'
Note: 12 rows have no number or no day: they are not drawn.
Note: A log scale needs values above 0: the linear scale is shown.
```

| Line | Meaning |
|------|---------|
| `rows: N (the cap of 10000 …)` | The read hit the cap: the chart shows only part of the range. Aggregate in the query, or narrow `--timeframe` |
| `rows: N (the --limit of N; …)` | Your `--limit` stopped the read; the dashboard reads up to 10,000 rows. A table has no cap line: it reads pages |
| `x: COL: time / number / category axis` | How the chart reads X (the web `xKindOf`). Bars draw every X as a category |
| `series:`, `slices:`, `groups:` | What the chart colours, and what goes into **Other** |
| `0 rows: the widget is empty` | Widen `--timeframe`, or check that the query returns rows |
| `N rows have no number or no X` | Y is not a number (or X is empty) in those rows: the chart drops them |
| `A log scale needs values above 0` | A value is 0 or less: the chart falls back to linear |
| `long labels: …` | A category label is longer than 14 characters: the axis hides the labels that overlap. Use fewer categories or shorter labels |

## See the chart (`render-widget`)

`render-widget` reads the rows as `preview-widget` does, runs the same checks, prints the same summary,
and then draws the widget on the web app's `/render/widget` page in a headless browser. It writes
`widget-<id or draft>-<theme>.png` (`--out PATH`), at 2 pixels for each CSS pixel of the card (default
640 × 360, `--width`/`--height` 200–2560, `--theme dark|light`). It works before the save (`--query-id
--type …`) and after (`--id`). A table has no chart: use `preview-widget`.

- It needs the `render` extra and a browser:
  `uv tool install --force 'monitoring-cli[render] @ git+https://github.com/Dedaub/monitoring-cli'`, then
  `playwright install chromium`; or use an installed Chrome with `--browser-channel chrome`.
- The browser loads only the app and its fonts: every other request (analytics, tags) is blocked.
- `--app-url http://localhost:3000` draws on a dev server of the web app. The default is the app of the
  profile's API. The browser gets the rows only: no token and no cookie.
- `--upload` (a saved widget that you own, with no flag changes) also stores the picture as the widget's
  card picture of `--theme`, a 640 × 360 JPEG, as the owner's browser makes it. Do it only when the user
  asks.

| Exit | Meaning |
|------|---------|
| 0 | The PNG is saved |
| 1 | A problem of the checks, the rows cannot be read, or the widget shows a message in place of a chart (a column left the query, an unsupported type): the PNG is saved so you can see it, and the message is printed |
| 2 | A bad flag (a table, a size out of range, `--upload` without `--id` or with changes) |
| 6 | The page cannot draw the widget: it said "error", it timed out (`--timeout`, default 60 s each step), or the web app has no `/render/widget` page yet (give `--app-url`) |
| 7 | Playwright or a browser is not installed: install them as above |

## Limits: what goes into "Other"

| Chart | Draws at most | The rest |
|-------|---------------|----------|
| Lines and bars with `series_by`, histogram `ecdf` | 8 series | the 7 largest (by total) + **Other** |
| `pie` | 6 slices | the 5 largest + **Other** |
| `scatter` with `series_by` (groups) | 3 colours | the 2 largest groups + **Other**; `color_scale scale` has no limit |

**Colours.** A series of `series_by` values (a token, a chain) and a pie slice take their colour by
name: the same name has the same colour on each widget of a dashboard. One chart never holds two colours
that a colour-blind viewer cannot tell apart, so a name can move to another colour in a chart where its
own colour would clash. Y columns (`--y`, `--y1`) keep the palette order. **Other** is grey.

**Long labels.** The chart cuts a category label to 14 characters (26 on `--horizontal` bars), with the
full text in the tooltip. For a top-N of tokens or addresses, use `--horizontal`.

**Other** adds the values together. A sum is correct for a count or a volume, but it is wrong for a
rate, an average or a percentage (TPS, block time, gas used %). `check-widget` cannot see this, because
it does not run the query; `preview-widget` counts the values and prints a note. Fix it in the SQL: split
the rows into two derived queries (for example L1 chains and L2 chains, each one
`SELECT … FROM {{ ref("Query") }} WHERE layer = 'L1'`), or filter the rows. For a pie with more than 6
categories, use a `bar`.

## Value tiles

A `value` widget shows **one row**: the newest row by its `--x` column (the widget sorts the rows
descending). With `--x` set to a time column, the tile also shows the change from the row before it and
a sparkline of up to 30 rows. So give a headline tile an hourly or daily series (one row per bucket, the
totals in columns), not a one-row snapshot. Without `--x`, the tile shows the first row as the query
returns it, with no change and no sparkline.

## Dashboard layout

The grid has 12 columns. `create-widget --dashboard-id` and `add-widget` put each new widget in a place
that the server selects, so after many adds the dashboard can be one long column. **After you add the
widgets, arrange the dashboard once:**

```bash
dedaub-monitoring arrange-dashboard --id 78 --dry-run   # print the layout (JSON), save nothing
dedaub-monitoring arrange-dashboard --id 78             # save it
```

`arrange-dashboard` keeps the order of the widgets (top to bottom, then left to right) and sets the
place and size of each one from its type:

| Widgets | Place | Width × height |
|---------|-------|----------------|
| `value` tiles | First, at most 6 in a row | 1–3 tiles: 4 × 2; 4 tiles: 3 × 2; 5–6 tiles: 2 × 2 |
| Charts | In pairs, after the tiles | 6 + 6; a `pie` beside a chart: 8 + 4; a chart alone: 12 (a `pie` alone: 6). Height 5 when the row has a `line`, `linebar` or `range`, else 4 |
| `table` and alerts widgets | Last | 12 × 6 |

So put the widgets in the order that you want, then arrange. To change one place, take the `--dry-run`
JSON, edit it, and give it to `set-layout --id 78 --layout layout.json` (all or nothing; `x + width` ≤ 12).

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

## Options of each type (`ChartOptionsFields`)

A key that the type does not use is ignored: `check-widget` prints a `Note:` and exits 0.

| Key | Types |
|-----|-------|
| `y1_axis_name` | `line`, `bar`, `stackedbar`, `linebar`, and only with no `series_by` |
| `series_by` | `line`, `bar`, `stackedbar`, `linebar`, `scatter`, `histogram` (`hist_view ecdf` only) |
| `combine`, `transform`, `reference_line`, `reference_label`, `order_by` | `line`, `bar`, `stackedbar`, `linebar` (`transform bollinger`: `line` only) |
| `uncertainty` (+ `lower_name`, `upper_name`, `stderr_name`) | `line`, `bar`, `linebar` (`quantiles`: `line` only) |
| `line_style`, `anomalies`, `anomaly_k`, `trend`, `correlation`, `band_k` | `line` (`band_k` needs `transform bollinger`) |
| `window` | a rolling `transform` (`mean`, `ewma`, `bollinger`), or a `line` with `anomalies` (on by default) or `correlation` |
| `scale` | `line`, `bar`, `linebar`, `scatter`, `range` |
| `number_format` | all but `histogram` and `table` |
| `fit`, `size_by`, `color_scale` | `scatter` (`color_scale` needs `series_by`) |
| `bins`, `hist_view` | `histogram` |
| `range_shape`, the range columns, `volume_name` | `range` (`volume_name`: `candle` only) |
| `prefix`, `suffix` | `value` and every chart but `histogram` (axis, tooltip, labels) |
| `percent` | `stackedbar`, and `line` with `line_style stacked` |
| `horizontal` | `bar`, `stackedbar` |
| `x_label`, `y_label` | the types with axes (see Labels) |

**A band that cannot draw is a problem (exit 1):** `uncertainty columns` needs `lower_name` and
`upper_name`; `uncertainty stderr` needs `stderr_name`.

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
| `--sorting-order` | `sorting_order` | `ASC`, `DESC` |
| `--order-by` | `order_by` | `x` (default), `y`: the X categories in the order of Y (line, bar, stackedbar, linebar; not for a time X, nor for a number X on a line) |
| `--combine` | `combine` | `sum`, `mean`, `median`, `min`, `max`, `count` (rows that share an X) |
| `--line-style` | `line_style` | `line`, `area`, `step`, `stacked` (stacked areas, one per `series_by` value; line) |
| `--percent` | `percent` | `true`: each series as its share of the total at each X (100% stack) |
| `--horizontal` | `horizontal` | `true`: bars on their side, categories down the left (bar, stackedbar) |
| `--transform` | `transform` | `none`, `ma7`, `mean`, `ewma`, `bollinger` (line), `cum`, `index`, `pct` |
| | `uncertainty` | `none`, `sd`, `ci95`, `minmax`, `quantiles` (line), `columns` (+ `lower_name`, `upper_name`), `stderr` (+ `stderr_name`) |
| `--scale` | `scale` | `linear`, `log` |
| `--number-format` | `number_format` | `compact`, `full`, `currency`, `percent` |
| `--prefix`, `--suffix` | `prefix`, `suffix` | unit text, max 16 characters, not trimmed: type the space (`--suffix ' ETH'`) |
| `--decimals` | `decimals` | digits after the point, `0`–`20` (as text, e.g. `"2"`) |
| | `hist_view` | `counts`, `ecdf` (histogram) |
| | `range_shape` | `range`, `candle`, `box` |
| | `color_scale` | `groups`, `scale` (scatter with `series_by`) |
| | `size_by` | column (scatter dot size) |
| | `volume_name` | column (candle volume) |
| | `reference_label` | text |
| | `reference_line`, `bins`, `window`, `band_k`, `anomaly_k` | number (as text, e.g. `"2"`) |
| | `fit`, `anomalies`, `trend`, `correlation` | `true` / `false` |

`--clear KEY` (on `update-widget`) removes a key from the saved config.

## Labels (`x_label`, `y_label`, and the widget title `--label`)

- Inline Markdown: `**bold**`, `*italic*` or `_italic_`, `` `code` ``. No links, no blocks, no HTML.
- TeX: `$x$` inline, `$$\frac{a}{b}$$` display. `$` opens math only before a non-space: "$5 and $10" stays text.
- `\$` writes a dollar sign.
- Axis labels: 120 characters max, and only the charts with axes show them: `line`, `bar`, `stackedbar`,
  `linebar`, `scatter`, `histogram`, `range`.

**Always set both axis labels, in TeX.** On every chart with axes, give `--x-label` and `--y-label`, and
write each one as one inline math span with the words in `\text{…}` and the unit in brackets. KaTeX
renders it in the chart's math font, and a label in the same style on every widget makes the dashboard
look finished.

| Column | Label |
|--------|-------|
| `day` | `$\text{Day}$` |
| `token_symbol` | `$\text{Token}$` |
| `liquidated_usd` | `$\text{Liquidated (\$)}$` |
| `share` | `$\text{Share of volume (\%)}$` |
| `gas_used` | `$\text{Gas used}$` |
| `amount_eth` | `$\text{Amount }(\Xi)$` |
| `price_change` | `$\Delta\,\text{Price (\$)}$` |
| `std_fee` | `$\sigma_{\text{fee}}\ \text{(gwei)}$` |

- One span `$…$`, not display math `$$…$$`: display math is set larger and on its own line.
- Inside the math, escape the TeX specials: `\$`, `\%` (a bare `%` starts a comment and hides the rest),
  `\_`, `\&`, `\#`. A space between two math parts is `\ ` or `\,`.
- Write words, not column names: `$\text{Gas used}$`, not `gas_used`.
- In a shell, put the label in single quotes so the shell keeps `$` and `\`.
- **The title (`--label`) stays mostly plain:** the widget lists, the tab titles and the add-widget list
  show a title as text, with its TeX as source. Use Markdown (`**Daily volume**`) and TeX only for a
  symbol (`**Fee volatility** $\sigma$`).

## Timeframes and rows

`timeframe` filters the query's first time column (`timestamp…` or `date`) to the last 24h / 7d / 30d (one
calendar month) / 60d. A chart reads the newest 10,000 rows by its X column, then sorts them; a table
reads 25 rows a page. A dashboard's own time range wins over the widget's. The rows come from the query's table
through `ref()`; a query that `ref()` cannot find (no run settings) reads its text. So schedule the query
(`set-config`) for a fast widget on big data.

## Sharing and publishing

A viewer runs a widget's queries as themselves, so a public widget or dashboard needs public queries,
also the ones that it reads through `ref()`. Making a query public shows its text, rows and alerts to
everyone. **Ask the user before you share or publish.**

- `widget-private-queries --id <WID>` lists the private queries of a widget. `share-widget --id <WID>
  --public` prints them and makes them public with the widget, all or nothing. `--private` makes the
  widget private again; its queries stay public.
- `publish-dashboard --id <DID> --dry-run` lists the private queries of a dashboard; without
  `--dry-run` it makes them and the dashboard public, all or nothing (`--unlisted` hides it from the
  public list). `update-dashboard --public` fails with HTTP 400 when the dashboard reads a private query.
- A query that you cannot edit, or an example query, stops the share: the command prints it and
  changes nothing. "The private queries … changed": run the command again.

## Pictures

The web app stores a picture of each chart widget and each dashboard, one for each theme. Only the
owner's browser makes it, when the owner opens the dashboard; a table or value widget has none.
`widget-picture --id <WID>` and `dashboard-picture --id <DID>` (`--theme dark|light`, `--out PATH`)
save it as `widget-<id>-<theme>.jpg` (or `dashboard-…`) and print its age and `Stale: yes|no|unknown`
(the widget changed after the picture). No picture yet: exit 5. A picture is not proof that the chart
is correct: use `preview-widget` for the data.

## Commands (one example each)

```bash
dedaub-monitoring check-widget   --query-id 123 --type line --x day --y volume_usd --x-label '$\text{Day}$' --y-label '$\text{Volume (\$)}$'
dedaub-monitoring preview-widget --query-id 123 --type line --x day --y volume_usd --timeframe 7d
dedaub-monitoring preview-widget --id 456 --sql                       # print the SQL, do not run it
dedaub-monitoring preview-widget --id 456 --show-rows 0 --refresh     # the summary only, from the database
dedaub-monitoring render-widget  --query-id 123 --type line --x day --y volume_usd --theme light   # widget-draft-light.png
dedaub-monitoring render-widget  --id 456 --app-url http://localhost:3000 --out chart.png
dedaub-monitoring create-widget  --query-id 123 --type line --x day --y volume_usd --label '**Daily volume**' \
                                 --x-label '$\text{Day}$' --y-label '$\text{Volume (\$)}$'
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
dedaub-monitoring arrange-dashboard --id 78 [--dry-run]            # a clean grid from the widget types
dedaub-monitoring set-layout     --id 78 --layout layout.json         # [{"widget_id", "x", "y", "width", "height"}]
dedaub-monitoring set-default-dashboard --id 78
dedaub-monitoring delete-dashboard --id 78                            # widgets stay; --delete-widgets removes them
dedaub-monitoring widget-private-queries --id 456                     # what share-widget --public publishes
dedaub-monitoring share-widget   --id 456 --public                    # or --private
dedaub-monitoring publish-dashboard --id 78 --dry-run                 # list the private queries; change nothing
dedaub-monitoring widget-picture --id 456 --theme light               # widget-456-light.jpg; exit 5: no picture yet
dedaub-monitoring dashboard-picture --id 78 --out board.jpg
```

A public dashboard takes only widgets of public queries: use `publish-dashboard`. The grid has 12
columns; `x + width` ≤ 12.
