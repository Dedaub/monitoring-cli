---
name: dedaub-monitoring
description: >
  Generate blockchain SQL queries and create monitoring alerts on the Dedaub platform
  using the dedaub-monitoring CLI. Use when the user wants to query on-chain activity
  (volumes, top actors, event/call discovery) OR set up alerts for it (large transfers,
  drains, liquidations, admin actions, oracle deviations). Routes: query mode (generate +
  validate SQL) and alert mode (generate + materialize + notify).
---

# Dedaub Monitoring Skill

You are the orchestrator. You turn a user's question into **PG SQL** that runs on the Dedaub
engine — either returned as a one-off **query** or deployed as a recurring **alert**.

Both modes hit Postgres via DedaubQL — **macros over the full table set** (always use macros, never raw
`<chain>.<table>`; see `references/database/macros.md`). `common_query_patterns.md` is the canonical
pattern/rule base. **Mode does not change the dialect — only the tail of the flow (deploy-or-not,
materialize-or-not).**

**CLI invocation:** try `dedaub-monitoring <cmd>` first; if "command not found", use
`uv run dedaub-monitoring <cmd>` from the project root. Decide once at session start, reuse all session.

---

## Step 0 — Session setup (always)

1. Confirm the CLI works and you are logged in:
   ```bash
   dedaub-monitoring entities
   ```
   If this fails, ask the user to `dedaub-monitoring login` and stop.

2. Pull the schema locally — **do not WebFetch docs for this**:
   ```bash
   dedaub-monitoring get-schema --macros            # available DedaubQL macros (the full table set)
   dedaub-monitoring get-schema --network ethereum  # tables + columns (repeat per target network)
   ```
   **`get-schema` is the authoritative source for tables/columns for a given chain.** The protocol
   refs supply *constants + patterns only* — never treat a ref (or `common_query_patterns.md`) as the
   schema. Verify column names/types live per chain; coverage differs by network.

3. Create a session workspace (only needed in alert mode, but cheap):
   ```bash
   SESSION_DIR=$(mktemp -d /tmp/monitoring-skill-XXXXXX); echo "$SESSION_DIR"
   ```

4. **Pick the mode** (ask if not obvious from the request) — use the `AskUserQuestion` pop-up:
   > "Do you want a **query** (run it and show results) or an **alert** (deploy it to fire on a schedule)?"

5. **Alert mode only — collect targeting + notification prefs.** Ask **in this order**, and use the
   `AskUserQuestion` tool (a pop-up) for **everything except the alert condition itself**. Collect the
   notification/frequency prefs once and reuse them for every alert this session.

   **(a) What to alert on** — *free text, no pop-up.* Ask the user to type the condition (protocol +
   event/threshold is ideal, e.g. "large USDC transfers > \$1M", "any owner/admin change on Aave v3",
   "Curve pool drain", "liquidations on Morpho"). This is the one thing you can't enumerate, so let
   them write it.

   **(b) Target network** — pop-up, **only if the network was not already named in the initial
   request.** `multiSelect: true` (one alert deploys to one `--network` slot, but the user may want
   coverage across several — see below). The **full supported set** (each is a valid `--network` slug):

   | Network | slug | | Network | slug |
   |---------|------|-|---------|------|
   | Ethereum | `ethereum` | | Polygon | `polygon` |
   | Base | `base` | | BNB | `bnb` |
   | Arbitrum | `arbitrum` | | Avalanche | `avalanche` |
   | Optimism | `optimism` | | | |

   The pop-up caps a question at 4 options, so surface the **4 most relevant** for this alert — when the
   protocol's chain coverage is known (from its ref / `get-schema`) offer exactly those; otherwise
   default to `ethereum, base, arbitrum, polygon`. The remaining slugs reach the user via the auto
   **"Other"** field. If the user picks **multiple** networks, build **one query that `UNION`s the
   per-network table sets in a CTE** (each network is its own `get-schema` schema) rather than N copies;
   deploy under the primary network slot.

   **(c) Frequency** — pop-up, asked **before** notifications. The platform accepts **only** this fixed
   enum; map the chosen label to `--frequency` **seconds** and store `DEFAULT_FREQUENCY_SECONDS`:

   | Label | seconds | | Label | seconds |
   |-------|---------|-|-------|---------|
   | 30 seconds | `30` | | 10 minutes | `600` |
   | 1 minute | `60` | | 1 hour | `3600` |
   | 2 minutes | `120` | | 4 hours | `14400` |
   | 5 minutes | `300` | | 24 hours | `86400` |
   | | | | 3 days | `259200` |

   4-option cap: offer 4 sensible defaults (`5 minutes`, `1 hour`, `24 hours`, `3 days`) and **list the
   full enum in the question text** so an "Other" pick stays within the supported set — reject any value
   not in the table.

   **(d) Notifications** — pop-up (`multiSelect: true`): "Email" (`--email`) and/or "Webhook". If they
   pick Webhook, collect the integer **webhook ID** (`--webhook-id`) via the "Other" field or a quick
   follow-up; neither selected = no notifications.

---

## Step 1 — Read the patterns, then classify the problem

**Always read first:** `references/database/sample_queries/common_query_patterns.md`
(block-times §2, index inventory §1.1, patterns P1–P11 §5, business-question→pattern map §7,
anti-patterns §9, sanity checklist §10) and skim `references/database/macros.md`.

There is **one macro dialect** over the whole table set (confirmed via `get-schema --macros`):
`outer_transaction`, `transaction_detail`, `logs`, `token_ledger`, `token_transfers`, `contracts`,
`block`, plus structural macros (`ref`, `param`/`params`, `is_backfilling`). `outer_transaction`
(one row per top-level tx: `tx_hash`, `callvalue`, `status`) and `transaction_detail` (one row per
internal call frame) are **different granularities, not rival dialects** — pick by what you need.

Then classify the user's question along four axes — this decides *what to grep and how to write it*:

| Axis | Options | Decides |
|------|---------|---------|
| **Data source** | `logs` (events) / `outer_transaction` (top-level tx) / `transaction_detail` (call frames) / `token_ledger`,`token_transfers` (value) | which table + primitive |
| **Primitive** | topic0 (event) / 4-byte selector (call) / token+decimals (value) / address | what to grep from the protocol ref |
| **Scope** | specific deployment / all-forks (ecosystem-wide) | the collision guard (see Step 3) |
| **Pattern** | P1–P11 from §7 business-question→pattern map | the SQL skeleton |

If the question needs a protocol's constants, go to Step 2. If it's protocol-agnostic
(e.g. "all large ETH transfers on ethereum"), skip to Step 4.

---

## Step 2 — Find the protocol constants (grep the least)

**Local refs are authoritative; web is a gap-filler only** (Step 2c).

**2a. Discover the file (glob + filename convention):**
```bash
ls references/protocols/<name>/
```
- **Multi-version dir** (curve, morpho, aave, uniswap, lido, fluid, sushiswap, euler, balancer,
  compound, maple, chainlink, pancakeswap, rocketpool, aerodrome, native): read its
  `README.md` **first** — it gives the version→file table, chain coverage, and the
  **topic0 collisions / gotchas** you must not miss. Pick the right version file.
- **Single-file dir** (spark, moonwell, 40acres, dodo): open the lone file directly.

**2b. Surgically grep the version file for exactly the primitive you need** — never read the
whole file:
```bash
# topic0 for an event:
grep -n -i "EventName" references/protocols/<name>/<file>.md
# 4-byte selector for a call:
grep -n -i "functionName\|SEL_" references/protocols/<name>/<file>.md
# an address on a chain:
grep -n -i "<chain>\|FACTORY\|ROUTER" references/protocols/<name>/<file>.md
```
The `## Quick-copy detection constants (bytea-ready for PG)` block holds topics, selectors and
per-chain addresses as `\x`-literals with self-documenting names — usually the only block you need.

**Always also pull the file's `## Detection invariants & gotchas` section** (small) as a
collision guardrail — this is where wrong-but-plausible queries are prevented (e.g. Curve's
`TokenExchange` topic0 collides across pool families; Morpho has three `AccrueInterest` topics).

**2c. Web fallback — only when:** no local ref covers the protocol, OR a user-supplied address
isn't in the doc, OR the event isn't listed. Dispatch `references/agents/web-fallback.md`.
Never re-verify what a local ref already states.

---

## Step 3 — Apply the scope guard (collision safety)

- **Specific deployment** → filter on **`topic0` AND `address`** (and/or `to_a` + selector).
  Collisions are harmless because the emitter address disambiguates.
- **All-forks / ecosystem-wide** → **`topic0` alone** is correct by design (the event signature
  hashes identically across forks; you *want* every fork's address). BUT if that chain's `logs`
  has **no `topic0` index** (verify in §1.1 or `\d+ <chain>.logs`), you **must** add a
  `block_number` block-range predicate so the block index carries the query and it finishes in
  time. Use the **per-chain default lookback** below.

### Per-chain default look-back window (scaled by throughput)

A **fixed wall-clock window scans far more blocks on a high-throughput chain** than on a slow one, so
the same `24h` that returns in a second on Ethereum can crawl on Base or Arbitrum. Scale the window
**inversely with block time** to hold the scan budget ≈ constant — target **~50k blocks (≈ one
Ethereum-week)** so a default run costs about the same everywhere. These are the **default initial
look-backs** (derived from §2 blocks-per-hour):

| Chain | Block time | Default window | ≈ blocks |
|-------|-----------|----------------|----------|
| Ethereum (1) | 12 s | **7 d** | 50,400 |
| BNB (56) | 3 s | **2 d** | 57,600 |
| Polygon (137) | ~2 s | **24 h** | 43,200 |
| Optimism (10) | 2 s | **24 h** | 43,200 |
| Base (8453) | 2 s | **24 h** | 43,200 |
| Avalanche (43114) | ~2 s | **24 h** | 43,200 |
| Arbitrum (42161) | ~0.25 s | **3 h** | 43,200 |

In alert mode this window is the macro `duration=` / refresh cadence; in query mode it's the
`block_number BETWEEN MAX-N AND MAX` predicate (§2).

**Escalate if empty:** the empirical-gate `run-query` (Step 5) may return **0 rows** simply because
nothing matched in the default window — *not* because the SQL is wrong. When that happens, **widen the
window stepwise** (×2 → ×4 → …, e.g. Ethereum `7d → 14d → 28d`) and re-run, up to a sane cap, until
rows appear or you're confident the condition is genuinely quiet. **Always report the window that
actually produced the rows** — and for alerts, surface the final look-back to the user *before* you
deploy (see Step 5).

---

## Step 4 — Choose the structure (alert mode)

The **final alert output is always INCREMENTAL** — `enable-alerts` forces it, and it dedups on the
unique key (`--incrementalization IGNORE|UPSERT`). You don't choose that. The choice is only the
**lookup layer** (the "incremental piece") feeding the alert — three tiers:

| Tier | Use when | How |
|------|----------|-----|
| **CTE** (inline `WITH`) | trivial, single-use lookup computable in the scan window | non-materialized, re-evaluated every run; default |
| **VIEW + `{{ref()}}`** | reusable lookup, re-evaluated each run, shared across alerts / independently testable | a query set to `--materialize VIEW`, pulled in via the `ref` macro. **Not materialized** — this is the "view, read every run" model |
| **TABLE + `{{ref()}}`** | expensive **history-spanning** set (factory-enumerated pools, full watched-address list) where recompute-each-run is too costly and staleness is acceptable | a query set to `--materialize TABLE` (refreshed on a schedule), pulled in via `ref` |

**Rule of thumb:** inline a CTE; promote to **VIEW+ref** when the lookup is reused or worth testing
on its own; use **TABLE+ref** only when the set spans history and recompute is too expensive. Lead
the alert's own scan with the `address` index so each incremental run stays cheap.

Query mode has no materialization — it's an ad-hoc `run-query` (Step 5 tail).

---

## Step 5 — Generate, validate, then deploy

Write PG SQL using the §5 pattern skeleton, the grepped constants, the scope guard, and the Step 4
structure. Hard rules (from §3, §8, §9 + macros.md):

- Lead with an **indexed predicate** (`address`, `to_a`, selector) + a `block_number` range / `duration=`.
  Never bare `topic0` on a chain without a topic0 index.
- Exclude reverts (`outer_transaction.status = true`, or `committed AND error IS NULL` on
  `transaction_detail`) unless reverts are the point.
- Addresses **lowercase `\x` bytea** in WHERE; topic hashes full 32-byte literals; even hex digits (40 addr, 64 word).
- **`0x`-prefix readable output:** `concat('0x', encode(col,'hex'))` for any address/hash/tx_hash in
  SELECT — bare `encode()` lacks `0x` (WHERE literals stay `\x` bytea). See patterns §4.
- **Always surface `tx_hash` in the result** — it's what makes a hit actionable (click-through to the
  tx) and a natural unique-key component. `outer_transaction` has it natively; for
  `logs`/`transaction_detail`/`token_ledger`/`token_transfers` JOIN `outer_transaction` on
  `(block_number, tx_index)` (1:1, no fan-out), or on Arbitrum call `arbitrum.tx_hash(block_number,
  tx_index)`. Recipe in patterns §4.
- **Always project a literal `chain_id` column** matching the target network (e.g. `8453 AS chain_id`
  for base) — the UI uses it to render the default chain for the result. Mapping: ethereum `1`,
  base `8453`, arbitrum `42161`, optimism `10`, polygon `137`, bnb `56`, avalanche `43114`,
  blast `81457`. In a cross-network `UNION`, give **each branch its own literal** so rows stay
  attributable to their chain.
- Project explicit columns — never `SELECT *` (TOAST: `calldata`, `data`, `returndata`).
- **No trailing `;`** — the platform UI rejects a query that ends in a semicolon. End on the last
  token (or a comment). See patterns §3.
- Value math via `token_ledger.value_delta` (signed) over hand-decoding `logs.data`.
- Macros where they win: `duration=` for the window; for events, filter the protocol's `topic0`
  directly (the macro adds `committed`) — use `inputs='0x<addr>.Event(...)'` only to anchor a single
  contract by address or when you want `decode_event`'s typed output. See `macros.md`.
- Every column used in a unique key / alert template must appear in SELECT.

### Empirical gate (replaces mechanical review)

Don't *guess* whether the SQL is correct/cheap — **prove it** before any LLM review:
```bash
dedaub-monitoring preprocess-query --id <ID>   # see the macro→SQL expansion (sanity, not a plan)
dedaub-monitoring run-query --id <ID> --duration <window> --limit 25   # must execute + return sane rows
```
- `run-query` proves it executes (catches missing columns, bad literals, type errors) and its
  **latency is the index signal** — fast within the window = good lead; slow/timeout = it's scanning,
  fix the lead. (`explain-query` is **dependency analysis only** — use it to confirm `ref` deps
  resolve, NOT as a query plan.)
- Index correctness is *predicted* from §1.1 + the anti-pattern checklist, then *confirmed* by latency.

### Mode tail

**Query mode** — ad-hoc, no deploy. Reuse **one persistent probe** (`/_scratch/probe`) — it can't be
torn down anyway (macros.md CLI notes), so create it once and reuse its id forever:
```bash
dedaub-monitoring create-folder "/_scratch"            # positional PATH; no-op if it exists
dedaub-monitoring create-query "/_scratch/probe"       # once → reuse this id for ALL probes
dedaub-monitoring write-query --id <SCRATCH_ID> <<'SQL'
<your SQL>
SQL
dedaub-monitoring run-query --id <SCRATCH_ID> --limit 25   # put the real window in the macro's duration=
```
Show the user results + SQL; reuse the same probe next time.

**Alert mode** — validate in-place on the real target query, then review semantics, then deploy:
1. `create-folder`/`create-query` the **real** `/<AlertName>/<QueryName>`, `write-query` the SQL,
   run the **empirical gate** on it. On failure, iterate `write-query` on the **same id** — never
   spawn siblings (queries can't be deleted; see macros.md CLI notes).
2. Write the draft to `$SESSION_DIR/query_<safe_name>.md` (`references/handoff-schemas.md`).
3. Dispatch the **Reviewer subagent** (`references/agents/reviewer.md`) — **semantic-only** now
   (does it detect the right thing? right threshold/scope/collision family? readable template?).
   It writes `$SESSION_DIR/review_<safe_name>.md`. On REJECT, revise (≤2 rounds) and re-review.
4. On APPROVE, **tell the user the look-back window you settled on** — the per-chain default from
   Step 3 and whether you had to widen it to surface rows (e.g. "validated on Base over the last 24h;
   widened to 48h to catch a sample event"). This is the scan window the empirical gate ran on; the
   user should know it before the alert goes live. Then follow `references/deploy-playbook.md`
   (`enable-alerts --network <net>` → smoke-test via `get-logs` → set final frequency or park if at
   the materialization limit).

### Alert mode sub-branch — protocol coverage (suite of alerts)

If the user wants to *cover a protocol* rather than build one specific alert: read the protocol
ref's `## Detection invariants & gotchas` + key events, **propose 3–6 high-signal security alerts**
(drains, liquidations, admin/owner/role changes, oracle deviations, pause/upgrade, collisions-as-signal),
**reject low-signal noise** (new-pool-created, daily TVL), confirm the list with the user, then loop
the generate→gate→review→deploy pipeline per confirmed alert. Proposals come from the **local ref**,
not web research.

---

## Step 6 — Summary

Print what was produced. Alert mode: a table of alert | path | query id | network | frequency | status,
plus `query-metadata`/`get-alerts`/`get-logs` follow-ups. Clean up the temp dir: `rm -rf "$SESSION_DIR"`.
The `/_scratch/probe` query is intentionally left in place for reuse (it can't be deleted anyway).

---

## Reference map (read on demand, not up front)

| File | Read when |
|------|-----------|
| `references/database/sample_queries/common_query_patterns.md` | **always**, Step 1 — patterns, indexes, anti-patterns |
| `references/database/macros.md` | Step 1/5 — full macro list, VIEW/`ref`/INCREMENTAL, CLI behavior notes |
| `references/protocols/<name>/README.md` | Step 2a — multi-version disambiguation + collisions |
| `references/protocols/<name>/<file>.md` | Step 2b — surgical grep for constants |
| `references/agents/reviewer.md` | Alert mode, Step 5 — semantic review subagent |
| `references/agents/web-fallback.md` | Step 2c — only when no local ref covers the protocol |
| `references/handoff-schemas.md` | Alert mode — draft + review doc shapes |
| `references/review-criteria.md` | Alert mode — the reviewer's checklist |
| `references/deploy-playbook.md` | Alert mode, Step 5 — CLI deploy, smoke-test, timeout diagnosis |
