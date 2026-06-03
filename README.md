# dedaub-monitoring

**dedaub-monitoring** is a command-line interface (CLI) for the [Dedaub](https://app.dedaub.com) monitoring platform. It lets you write SQL queries against on-chain data on Ethereum and EVM-compatible chains, test them, and deploy real-time blockchain alerts — all from your terminal.

Use it to monitor on-chain activity and get notified about large transfers, fund drains, liquidations, oracle price deviations, privileged admin/owner actions, and any other event you can express in SQL. The package name is `monitoring-cli` and the installed command is `dedaub-monitoring`.

**Use cases:** smart-contract monitoring, DeFi protocol monitoring, security monitoring, on-chain alerting, and blockchain data analysis across Ethereum, Arbitrum, Base, and other EVM chains.

## Installation

Requires Python 3.13. Install from source (recommended via [uv](https://docs.astral.sh/uv/)):

```bash
git clone https://github.com/Dedaub/monitoring-cli.git
cd monitoring-cli
uv tool install . # or: pipx install .
```

## Authentication

```bash
dedaub-monitoring login
```

This opens a browser-based OAuth2 device flow. Your credentials are stored locally and reused across sessions.

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

Then type `/monitoring-cli` in Claude Code to start a session. The skill guides you through researching a protocol, writing alert queries, reviewing them, and deploying them.

## Commands

| Command | Description |
|---------|-------------|
| `login` | Authenticate via browser |
| `entities` | List your user and org accounts |
| `tree` | Show your query file tree |
| `create-folder` | Create a folder |
| `create-query` | Create an empty query |
| `write-query` | Update a query's SQL |
| `read-query` | Print a query's SQL |
| `query-metadata` | Print full query metadata as JSON |
| `get-schema` | Show available tables and columns |
| `run-query` | Execute a query and print results |
| `get-config` | Show materialization config |
| `set-config` | Set materialization config |
| `enable-alerts` | Enable incremental alerts for a query |
| `disable-alerts` | Disable alert notifications |
| `list-alerts` | List all queries with alerts enabled |
| `get-logs` | Show execution logs |
| `get-alerts` | Show fired alert events |
| `preprocess-query` | Expand DedaubQL macros and print the result |
| `explain-query` | Print query dependency analysis |
| `install-skill` | Install the Claude Code skill |

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
