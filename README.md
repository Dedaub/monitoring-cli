# dedaub-monitoring

**dedaub-monitoring** is a command-line interface (CLI) for the [Dedaub](https://app.dedaub.com) monitoring platform. It lets you write SQL queries against on-chain data on Ethereum and EVM-compatible chains, test them, and deploy real-time blockchain alerts — all from your terminal.

Use it to monitor on-chain activity and get notified about large transfers, fund drains, liquidations, oracle price deviations, privileged admin/owner actions, and any other event you can express in SQL. The package name is `monitoring-cli` and the installed command is `dedaub-monitoring`.

**Use cases:** smart-contract monitoring, DeFi protocol monitoring, security monitoring, on-chain alerting, and blockchain data analysis across Ethereum, Arbitrum, Base, and other EVM chains.

## Installation

Pick the path that matches what you already have — all three end with the same installed `dedaub-monitoring` command.

### From scratch — one command (recommended)

The bootstrap installer does the whole setup: it installs [uv](https://docs.astral.sh/uv/) if it's missing (uv also provides the right Python, so you don't install Python yourself), installs the CLI, installs the agent skill, and starts login. Works on macOS, Linux, and Windows. It assumes `git` is already present (uv uses it to fetch the package) and will tell you if it isn't; everything else it handles.

**macOS / Linux:**

```bash
curl -LsSf https://raw.githubusercontent.com/Dedaub/monitoring-cli/main/install.sh | sh
```

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/Dedaub/monitoring-cli/main/install.ps1 | iex"
```

Re-run any time to upgrade. The only step that isn't automated is the browser login, which prints a URL for you to open.

### Already have uv — one line

uv installs the CLI straight from the public repo over HTTPS — no clone, no SSH keys, and uv fetches the pinned Python for you:

```bash
uv tool install git+https://github.com/Dedaub/monitoring-cli
dedaub-monitoring install-skill
dedaub-monitoring login
```

### Contributors — from a clone

If you're hacking on the CLI, work from a checkout. From a clone, `make setup` runs the whole onboarding against your working tree:

```bash
git clone https://github.com/Dedaub/monitoring-cli.git
cd monitoring-cli
make setup   # uv tool install . --force  +  install-skill  +  login
```

The skill picker and the login browser flow are interactive, so you stay in control of those two steps. Re-authenticate any time with `make login`.

## Authentication

```bash
dedaub-monitoring login    # or: make login
```

This opens a browser-based OAuth2 device flow. Your credentials are stored locally and reused across sessions; run `logout` to clear them. Every command accepts `--profile/-p` to keep separate credential sets (e.g. work vs personal).

## Usage

### Browse your queries

```bash
dedaub-monitoring tree
```

### Create a query

```bash
dedaub-monitoring create-folder "/My Alerts"
dedaub-monitoring create-query "/My Alerts/large-eth-transfer"
```

### Write SQL

```bash
dedaub-monitoring write-query --id 1234 <<'SQL'
SELECT
    encode(t.tx_hash, 'hex') AS tx_hash,
    encode(t.from_a, 'hex') AS sender,
    t.callvalue / 1e18 AS eth_amount,
    t.block_number
FROM {{outer_transaction(network='ethereum')}} t
WHERE t.callvalue > 100 * 1e18
  AND t.status = true
SQL
```

### Enable alerts

```bash
dedaub-monitoring enable-alerts \
  --id 1234 \
  --frequency 300 \
  --network ethereum \
  --alert-template "{{sender}} sent {{eth_amount}} ETH (tx: {{tx_hash}})" \
  --unique-key "tx_hash" \
  --email
```

`--network` (default `ethereum`) selects the chain the alert's run config and notifications
apply to — set it to match the network used in your query's macros (e.g. `arbitrum`, `base`).
The same `--network` option is available on `set-config`, `get-config`, `disable-alerts`, and
`list-alerts`.

### Check execution logs

```bash
dedaub-monitoring get-logs --id 1234
```

### See fired alerts

```bash
dedaub-monitoring get-alerts --id 1234
```

### Test a query

```bash
dedaub-monitoring run-query --id 1234 --duration 1h --limit 20
```

### Explore the schema

```bash
dedaub-monitoring get-schema --network ethereum
dedaub-monitoring get-schema --network ethereum --macros
```

## DedaubQL

Queries use DedaubQL, a dialect of SQL with macros that handle time-bounded incremental execution. Always use macros instead of raw table names:

```sql
-- Use this
FROM {{outer_transaction(network='ethereum')}} t

-- Not this (causes full table scans and timeouts)
FROM ethereum.outer_transaction t
```

Key macros: `{{outer_transaction(network='ethereum')}}`, `{{logs(network='ethereum')}}`, `{{contracts(network='ethereum')}}`.

All address and hash columns are `bytea`. Use `\x`-prefixed literals in WHERE clauses and `encode(col, 'hex')` in SELECT for readable output:

```sql
WHERE t.to_a = '\x7a250d5630b4cf539739df2c5dacb4c659f2488d'
```

Full reference: [DedaubQL API Reference](https://docs.dedaub.com/docs/monitoring/TSQLApiReference/)

## Claude Code skill

If you use [Claude Code](https://claude.ai/code), install the `/monitoring-cli` skill to get an AI-guided alert builder:

```bash
dedaub-monitoring install-skill
```

The skill ships in the shared "Agent Skills" format, so it can install to more than just Claude. With no flags, in a terminal you get a checkbox picker; otherwise it installs to Claude plus any other supported agent already present on the machine. Choose targets explicitly with `--agent`, or install everywhere with `--all`:

```bash
dedaub-monitoring install-skill --agent claude --agent codex   # specific agents
dedaub-monitoring install-skill --all                          # claude, codex, cursor, .agents
```

Then type `/monitoring-cli` in Claude Code (or your agent) to start a session. The skill guides you through researching a protocol, writing alert queries, reviewing them, and deploying them.

## Commands

The [Usage](#usage) walkthrough above covers the common path — log in, create a query, write SQL, enable alerts. This is the full reference, grouped by what you're doing: the **Account & session** commands get you set up, and the **Operations** sub-sections cover everything you do to existing queries afterwards.

Commands that act on a query or folder take it **either** by `--id <id>` **or** by `--path /Folder/Name` (add `--entity-id` to reach another entity's tree), so once you know what you want you can edit it directly without browsing first. Every command also accepts `--profile/-p`.

### Account & session

| Command | Description |
|---------|-------------|
| `login` | Authenticate via browser (OAuth2 device flow) |
| `logout` | Remove stored credentials for a profile |
| `entities` | List entities (your user + orgs) available to you |
| `entity` | Look up an entity by username |
| `tree` | Show the query file tree for an entity |
| `install-skill` | Install the agent skill to one or more agents (`--agent`, `--all`) — see [above](#claude-code-skill) |

## Operations

### Folders

| Command | Description |
|---------|-------------|
| `create-folder` | Create a folder (intermediate folders are created automatically) |
| `rename-folder` | Rename a folder (`--new-path`) |
| `delete-folder` | Delete a folder |
| `move-folder` | Move a folder under another parent (`--to-folder-id`) |
| `subfolders` | List a folder's immediate subfolders |

### Queries — create, edit & organize

| Command | Description |
|---------|-------------|
| `create-query` | Create a new empty query |
| `write-query` | Update a query's SQL (pass as an argument or pipe via stdin) |
| `read-query` | Print a query's SQL |
| `query-metadata` | Print full query metadata as JSON |
| `move-query` | Move a query to another folder (`--to-folder-id`) |
| `star-query` / `unstar-query` | Star or unstar (favourite) a query |
| `query-by-key` | Fetch a query's metadata by its share key (`--key`) |
| `generate-query` | Generate DedaubQL from natural language via the platform generator (for direct/programmatic use) |

### Queries — inspect & validate (no execution)

| Command | Description |
|---------|-------------|
| `get-schema` | Show available tables and columns — or macros with `--macros`; filter with `--network`/`--table` |
| `preprocess-query` | Render DedaubQL macros and print the resulting SQL |
| `explain-query` | Print the query's PostgreSQL EXPLAIN plan (it plans but does not execute, so it's free) |
| `validate-query` | Fast compile check — exits 0 if the SQL is valid, else prints the PG error and exits 1 |
| `query-columns` | Print the output columns (name + type) without running the query |
| `format-query` | Pretty-print SQL (argument or stdin) |
| `query-status` | Show materialization/backfill status as JSON |
| `query-history` | List a query's saved version history |

### Running queries

| Command | Description |
|---------|-------------|
| `run-query` | Execute a query and print results (async; Ctrl-C or `--timeout` revokes the server-side task) |
| `cancel-query` | Revoke a running async query task by id (`--task-id`; idempotent) |
| `active-queries` | List the task ids of currently-running async queries |
| `download-results` | Download a completed async query's results as CSV (`--task-id`) |
| `materialize` | Trigger a materialization run for a query |
| `reset-materialization` | Reset the materialized table, forcing a full recompute on the next run |

### Materialization & alerts

| Command | Description |
|---------|-------------|
| `get-config` | Show a query's materialization/scheduling config |
| `set-config` | Set materialization/scheduling (`--materialize` TABLE/VIEW/INCREMENTAL, `--frequency`, `--incrementalization`, `--backfill`, `--immediate`) |
| `enable-alerts` | Enable incremental alerts and notifications (`--email` and/or `--webhook-id`, `--alert-template`, `--unique-key`, `--frequency`) |
| `disable-alerts` | Disable notifications (materialization is left unchanged) |
| `list-alerts` | List all queries with alerts enabled |
| `get-logs` | List execution logs (filter `--status`/`--since`, paginate with `--before`) |
| `get-alerts` | List fired alert events (filter `--since`/`--before`, paginate with `--after-id`) |

### Notifications & sharing

| Command | Description |
|---------|-------------|
| `webhook` | Manage notification webhooks: `create`, `test`, `list`, `get`, `update`, `delete` (`--secret` for signing) |
| `alert-filter` | Manage saved alert filters: `create`, `list`, `get`, `update`, `delete` (group queries/chains, `--colour`) |
| `telegram-code` | Get the Telegram bot linking code for a query's notifications |
| `share-query` / `unshare-query` | Share or unshare a query with a team (`--team-id`, `--perm` READ/WRITE) |

## FAQ

### What is dedaub-monitoring?

`dedaub-monitoring` is a command-line tool for the Dedaub monitoring platform. You write SQL (DedaubQL) queries against on-chain Ethereum and EVM data, test them, and deploy real-time alerts that notify you by email when matching activity occurs.

### How do I monitor on-chain activity from the command line?

Install the CLI (`uv tool install .`), authenticate with `dedaub-monitoring login`, create a query with `create-query`, write your SQL with `write-query`, and enable notifications with `enable-alerts`. The query runs incrementally on a schedule and fires alerts when rows match.

### How do I set up real-time alerts for large token or ETH transfers?

Write a query that selects transfers above a threshold (see the [large ETH transfer example](#write-sql) above), then run `enable-alerts` with an `--alert-template` and `--unique-key` so each transfer is reported once. Set `--frequency` to control how often the query runs.

### Which blockchains and networks are supported?

Any chain supported by the Dedaub monitoring platform, including Ethereum, Arbitrum, and Base. Select the chain with the `--network` option (default `ethereum`) and the matching network argument inside your DedaubQL macros (e.g. `{{outer_transaction(network='arbitrum')}}`).

### How do I monitor a smart contract or DeFi protocol for drains, liquidations, or admin actions?

Query the protocol's logs and calls with the `{{logs(...)}}` and `{{outer_transaction(...)}}` macros, filter for the events you care about (large withdrawals, liquidation calls, owner/admin function selectors, oracle updates), and enable alerts on the query. The Claude Code skill (`dedaub-monitoring install-skill`) can build these queries for you from a plain-language description.

### Do I write raw SQL or a special dialect?

You write **DedaubQL**, a dialect of SQL with macros for time-bounded incremental execution. Always use macros (e.g. `{{outer_transaction(network='ethereum')}}`) instead of raw table names to avoid full table scans. See [DedaubQL](#dedaubql) above.

### Is there an AI-assisted way to build alerts?

Yes. If you use [Claude Code](https://claude.ai/code), run `dedaub-monitoring install-skill` and type `/monitoring-cli` to get an AI-guided alert builder that researches a protocol, writes the query, and deploys the alert.

## License

MIT
