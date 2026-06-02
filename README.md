# dedaub-monitoring

Command-line interface for the [Dedaub](https://app.dedaub.com) monitoring platform. Create and manage on-chain alert queries from your terminal.

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
  --alert-template "{{sender}} sent {{eth_amount}} ETH (tx: {{tx_hash}})" \
  --unique-key "tx_hash" \
  --email
```

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

## Claude Code skills

If you use [Claude Code](https://claude.ai/code), this repo ships two skills.

### `/monitoring-cli` — AI-guided alert builder

Install it with:

```bash
dedaub-monitoring install-skill
```

Then type `/monitoring-cli` in Claude Code to start a session. The skill guides you through researching a protocol, writing alert queries, reviewing them, and deploying them.

### `/protocol-research` — generate protocol reference docs

`protocol-research` researches **every on-chain deployment** of a protocol (all contracts, all versions) across Ethereum, Base, BNB Smart Chain, Avalanche, Arbitrum, Optimism, and Polygon PoS, then writes monitoring-grade reference docs into [`monitoring_cli/skills/references/protocols/`](monitoring_cli/skills/references/protocols/). These docs feed the `/monitoring-cli` alert builder with verified event topics, function selectors, and addresses.

The skill lives at [`.claude/skills/protocol-research/`](.claude/skills/protocol-research/) and is available automatically when you open this repo in Claude Code — no install step.

**Usage** — pass the protocol name as the argument:

```
/protocol-research aave
/protocol-research uniswap
/protocol-research pendle v2 only      # optional scope hint
```

If you omit the protocol name the skill will ask for one.

**What it produces** — one Markdown file per protocol version under `protocols/<slug>/`, in the house "v2.md/v3.md" shape:

- **Topics** (chain-agnostic) — `topic0 → event signature`
- **Function signatures** (chain-agnostic) — `selector → function + returns`
- **Addresses** (per chain) — every deployed contract with a one-line description, absence noted explicitly
- **Proxies** (old & new) — pattern, EIP-1967 slots, current implementation, upgrade authority
- plus a cross-chain summary, detection gotchas, copy-paste `\x` bytea constants, and a sources section

Single-version protocols get one file (e.g. `core.md`); multi-version protocols are split per version (e.g. `v2.md`, `v3.md`) with a `README.md` index, mirroring the existing [`uniswap/`](monitoring_cli/skills/references/protocols/uniswap/) and [`morpho/`](monitoring_cli/skills/references/protocols/morpho/) references.

**How it works** — it combines two skills: `evm-expert` for on-chain verification (every topic/selector is recomputed via `keccak256`, every address existence-checked via `eth_getCode`, every proxy slot read live) and `deep-research` for multi-source discovery plus a final adversarial fact-check pass before finalizing. Expect a thorough run — it sweeps all seven chains and double-checks its own output.

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

## License

MIT
