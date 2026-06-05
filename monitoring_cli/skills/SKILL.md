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

Turn the user's question into **PG SQL** on the Dedaub engine — a one-off **query** or a deployed
**alert**. Both use DedaubQL **macros over the full table set** (never raw `<chain>.<table>`; see
`macros.md`). `common_query_patterns.md` is the canonical pattern/rule base. Mode changes only the tail
(deploy/materialize), not the SQL.

**CLI:** try `dedaub-monitoring <cmd>`; on "command not found" use `uv run dedaub-monitoring <cmd>` from
repo root. Decide once, reuse all session.

---

## Step 0 — Session setup (always)

1. **Auth:** `dedaub-monitoring entities` — if it fails, ask the user to `login` and stop.
2. **Schema (don't WebFetch):**
   ```bash
   dedaub-monitoring get-schema --macros            # macro/table set
   dedaub-monitoring get-schema --network <net>     # tables+columns per target net; scope with --table <t>
   ```
   `get-schema` is authoritative for tables/columns; refs supply *constants only*. Verify per chain
   (coverage varies). For money/token asks: `network_token_info` (PK `token_address`) carries
   `last_price`+`symbol`+`decimals`+`logo_*`+`presentation_symbol` — **the only USD-price source**
   (`latest_token_info` is metadata, no price). `logs.topic0` is indexed on most chains but **not Base** →
   on Base lead with `address`, never bare `topic0`.
3. **Pick mode** — query (run + show) vs alert (deploy on schedule). **If the user didn't explicitly name
   the mode, ask via `AskUserQuestion` — do not infer it from phrasing.** "summarize …", "show me …",
   "what are the …" can be a one-off read *or* the spec for a recurring feed; the same protocol+event ask
   is valid in both modes. Skip the question only when the words pick the mode ("alert me", "notify",
   "set up monitoring", "every N min" → alert; "run a query", "show me now", "one-off" → query).
4. **Alert mode — collect prefs once (reuse all session), in order. `AskUserQuestion` for all but (a):**

   **(a) Condition** — free text. User types protocol + event/threshold (e.g. "USDC transfers > \$1M",
   "Aave v3 admin change", "Morpho liquidations"). The one thing you can't enumerate.

   **(b) Network** — pop-up only if not already named; `multiSelect`. Slugs: `ethereum, base, arbitrum,
   optimism, polygon, bnb, avalanche`. Surface the 4 most relevant (the protocol's chains, else
   `ethereum/base/arbitrum/polygon`); the rest reach the user via "Other". Multiple picks → **one
   `UNION ALL` query** (Step 4), deployed under the primary slot.

   **(c) Frequency** — pop-up, before notifications. Map label → `--frequency` seconds; **only these
   values**: `30, 60, 120, 300, 600` (10m), `3600` (1h), `14400` (4h), `86400` (24h), `259200` (3d).
   Offer 4 defaults (5m / 1h / 24h / 3d), list the full enum in the question, reject anything off-list.
   Store as `DEFAULT_FREQUENCY_SECONDS`.

   **(d) Notifications** — pop-up, `multiSelect`:
   - **Email** → `--email`.
   - **Webhook** → existing id via "Other" (`--webhook-id`); if none, set up inline:
     ```bash
     dedaub-monitoring webhook test   --url <URL> [--secret <S>]        # prove it fires first
     dedaub-monitoring webhook create --name <Alert> --url <URL> [--secret <S>]   # prints id
     ```
     (`webhook list` shows existing.) Use the id on `enable-alerts`; only create after the test succeeds.
   - **Don't notify (refresh-only)** → no `--email`/`--webhook-id`. Tell the user: still goes live, keeps
     refreshing (`INCREMENTAL`), results viewable in UI; toggle notifications later at the UI link (Step 6).

   "Don't notify" / nothing ⇒ notify-off; else pass the chosen flags.

---

## Step 1 — Read patterns, classify

**Read first:** `common_query_patterns.md` — the hub (rulebook + index: §1 schema/indexes, §2 block-times,
§3 perf rules, §5 P1–P16 index, §7 question→pattern, §8 edge cases, §9 anti-patterns, §10 checklist); skim
`macros.md`. When writing SQL, open the two siblings it indexes: **`query_patterns.md`** (full P1–P16
templates) and **`decode_primitives.md`** (decode/enrich cheat-sheet — topics, USD, `eth_call`, …).

One macro dialect: `outer_transaction` (1/top-level tx: `tx_hash`,`callvalue`,`status`),
`transaction_detail` (1/call frame), `logs`, `token_ledger`/`token_transfers`, `contracts`, `block`, plus
structural `ref`/`param`/`is_backfilling`/`is_ancestor`/`eth_call`/`net_config`/`networks`.
`outer_transaction` vs `transaction_detail` are granularities, not rivals.

Classify:

| Axis | Options |
|------|---------|
| **Data source** | `logs` (events) / `outer_transaction` (tx) / `transaction_detail` (call frames + `caller_vm_step_stack` depth, `is_ancestor`) / `token_ledger`,`token_transfers` (value) / `token_balance` (holder balances) / `eth_call` (live state) / `protocol_contract` (attribute to a protocol) |
| **Primitive** | topic0 / 4-byte selector / token+decimals / address |
| **Mode** | presence (P1/P2/…) vs **absence** (didn't happen in N — P13) |
| **Scope** | specific deployment vs all-forks (Step 3 collision guard) |
| **Pattern** | P1–P16 (§7 map) |

Pattern menu: P1–P12 = event/call/value/aggregate; **P13** absence/staleness, **P14** drain (net USD
out/tx), **P15** reentrancy (`is_ancestor`), **P16** anomaly (window drop/spike). §4 primitives: holders
(`token_balance`), live state (`eth_call`), USD (`to_usd_value`), price drift.

Needs protocol constants → Step 2. Protocol-agnostic → Step 4.

---

## Step 2 — Protocol constants (grep the least)

Local refs authoritative; web only as fallback (2c).

**2a. Find the file:** `ls references/protocols/<name>/`
- Multi-version dir (curve, morpho, aave, uniswap, lido, fluid, sushiswap, euler, balancer, compound,
  maple, chainlink, pancakeswap, rocketpool, aerodrome, native): read `README.md` first (version→file
  table, chain coverage, topic0 collisions), then pick the version file.
- Single-file dir (spark, moonwell, 40acres, dodo): open it directly.

**2b. Surgically grep** — never the whole file:
```bash
grep -n -i "EventName"               references/protocols/<name>/<file>.md   # topic0
grep -n -i "functionName\|SEL_"      references/protocols/<name>/<file>.md   # selector
grep -n -i "<chain>\|FACTORY\|ROUTER" references/protocols/<name>/<file>.md  # address
```
The `## Quick-copy detection constants` block has topics/selectors/per-chain addresses as `\x`-literals —
usually all you need. Always also read `## Detection invariants & gotchas` (collision guardrail, e.g.
Curve `TokenExchange` collides across pool families; Morpho has three `AccrueInterest` topics).

**2c. Web fallback** — only if no local ref covers the protocol, a user-supplied address isn't in the doc,
or the event isn't listed. Dispatch `references/agents/web-fallback.md`. Never re-verify what a ref states.

---

## Step 3 — Scope guard + look-back

- **Specific deployment** → filter `topic0` AND `address` (and/or `to_a` + selector). Collisions harmless.
- **All-forks** → `topic0` alone (every fork hashes identically — you want them all). If the chain's
  `logs` has no topic0 index (§1.1), add a `block_number` range so the block index carries it.
- **Whole category** ("all lending / all DEXs") → **triage members by USD-fidelity**: keep events whose
  value leg is priceable (underlying token + raw amount, or in-tx-recoverable per §4); **exclude the rest
  with a one-line reason** (wrapper/share/ID units, token neither emitted nor moved, not really the
  category, no such event). A sum that folds in unpriceable/wrong-unit rows is wrong — transparency beats
  false completeness.

**Per-chain default look-back** (scaled inversely with block time → ~50k blocks ≈ constant scan cost):

| Chain | Block | Window | ≈ blocks |
|-------|-------|--------|----------|
| Ethereum | 12s | **7d** | 50,400 |
| BNB | 3s | **2d** | 57,600 |
| Polygon / Optimism / Base / Avalanche | ~2s | **24h** | 43,200 |
| Arbitrum | ~0.25s | **3h** | 43,200 |

Alert mode: this is the macro `duration=`. Query mode: the `block_number BETWEEN MAX-N AND MAX` predicate (§2).

**Start at the default, escalate stepwise** (×2 → ×4: Base 24h→48h→96h). 0 rows usually means "nothing
matched", not "wrong SQL" — widen until rows appear or it's genuinely quiet. Report the window that
produced rows; surface it before deploy. Each test run <30s (120s max, only with user OK).

**High-volume-token caveat (value/threshold scans).** A `≥\$X`/percentile filter on a busy token
(USDC/USDT/WETH) is **not index-backed** — you scan *every* transfer of that token in the window to find
the large ones, so **token volume, not window length, is the limiter**. On the busiest chains this blows the
**120s cap well inside 30d**: USDC ≥\$1M over **7d times out on Base & Arbitrum** (ETH 7d ≈94s; Base ≈125k
USDC transfers/h ≈21M/7d). **Warm doesn't save you** — only ~the latest day of chunks stays cached, so Base
**24h ≈9s but 7d still times out** (super-linear). Won't fit → **shrink the window** to what one run clears,
**split per-chain** (separate runs, merge in chat), **materialize** (P12 incremental TABLE), or hand the
user the validated SQL for the **web UI** (no 120s cap). Also: the planner often **won't take the
`(address,block_number)` composite** for a dominant token (it flips to `block_number_idx` at short windows;
on Base at *any* window) and OFFSET-0/VALUES-join/`inputs=`/literal-bounds don't reliably force it — don't
burn runs fighting it.

**Hard ceiling 30d** (platform max; `1000d` is wrong). If a lookup needs >30d (e.g. every market ever
created): **first try to recover it from the triggering tx** — a token moved in the event's own tx is in
`token_ledger` for that block (Step 5 / §4), no history needed. Only if truly unrecoverable, promote to
**TABLE + `{{ref()}}`** (Step 4) — but materialization runs on the **ethereum/chain_id=1 slot** only
(deploy-playbook), so prefer in-tx. The alert's event scan stays at the per-chain default.

---

## Step 4 — Structure (alert mode)

Alert output is always **INCREMENTAL** (`enable-alerts` forces it; dedup via
`--incrementalization IGNORE|UPSERT`). You only choose the **lookup layer**:

| Tier | When |
|------|------|
| **CTE** (inline `WITH`) | trivial single-use lookup computable in-window — default |
| **VIEW + `{{ref()}}`** | reusable/testable lookup, re-evaluated each run (`--materialize VIEW`) |
| **TABLE + `{{ref()}}`** | history-spanning (>30d) set the inline cap can't reach (`--materialize TABLE`) |

Lead the alert's own scan with the `address` index.

**Aggregates → split (P12).** For any total/sum/leaderboard, esp. cross-chain: materialize the full
per-row scan as `--materialize VIEW` with **NO `LIMIT`**, then a separate reader does `SUM`/`GROUP BY`
(+ `LIMIT 200`). Cross-chain key = **`(address, chain_id)`**, never bare `address` (same address recurs —
even as a different token — per chain). Carry literal `chain_id` + `chain_name` per branch. See §5 P12.
**Query mode does this inline in ONE query** — inner CTE for the per-row `UNION ALL` scan, outer `SELECT`
with `GROUP BY`/`SUM` + final `LIMIT 200`; the VIEW/reader split is an alert-mode materialization concern.

**Combine signals with `UNION ALL`.** Multiple topic0s/addresses/selectors and/or chains → one query, one
branch per signal (same columns, own indexed lead + window + literal `chain_id`). `block_number` is **not**
cross-chain comparable — never JOIN on it; aggregate outside the UNION over `block_timestamp(...)`.
**Deploy slot:** a cross-chain UNION (or any query hard-coding `network=` in its macros) must deploy on the
**`ethereum`/chain_id=1 slot**, else it silently never fires (deploy-playbook §"Execution slot"). Confirm
via `get-logs`/`query-status`.

Query mode = ad-hoc `run-query`, no materialization.

---

## Step 5 — Generate, validate, deploy

Write PG SQL from the §5 skeleton + grepped constants + scope guard + Step 4 structure. **Hard rules:**

- **Indexed lead** (`address`/`to_a`/selector) + `block_number`/`duration=`. Never bare `topic0` on a
  no-topic0-index chain. Never cast/wrap an indexed column in WHERE (kills the index — cast the literal).
- **Exclude reverts:** `outer_transaction.status=true` or `committed AND error IS NULL` (unless reverts
  are the point).
- Addresses lowercase `\x` bytea in WHERE; topics full 32-byte; even hex digits (40 addr / 64 word).
- **Readable output:** `concat('0x', encode(col,'hex'))` for addresses/hashes (bare `encode` lacks `0x`;
  WHERE literals stay `\x`).
- **Layout — expanded, never minified.** Reproduce the §5 templates' vertical style; the engine preserves
  whitespace and humans read these. `SELECT` sits alone on its line; **one projected column/expression per
  line**, indented 4 spaces past the `SELECT` keyword's column (so a `SELECT` at 2-space CTE indent has
  columns at 6). `FROM`/`JOIN`/`LEFT JOIN`/`WHERE`/`GROUP BY`/`ORDER BY`/`LIMIT` align to that `SELECT`'s
  column; continued `AND`/`OR` indent +2 under `WHERE`; nested CTE/subquery bodies indent +2 from their `(`.
  **Blank line before each `UNION ALL`.** Never crowd several columns onto one line or collapse the query to
  save space (long single expressions like a wrapped `round(...)` may stay on their own one line).
- **Always project `tx_hash`** (actionable + unique-key part): native on `outer_transaction`; on
  `logs`/`token_ledger`/`transaction_detail` prefer **`<chain>.tx_hash(block_number,tx_index)`** (verified on
  all 7 chains — avoids a JOIN *and* keeps the large `outer_transaction` out of the cold set), falling back to
  a `{{outer_transaction}}` JOIN on `(block_number,tx_index)` (1:1) only if that function is ever absent.
- **Always project literal `chain_id`** (UI default chain): eth 1, base 8453, arb 42161, op 10,
  polygon 137, bnb 56, avax 43114, blast 81457. Per-branch literal in a UNION.
- No `SELECT *` (TOAST: `calldata`/`data`/`returndata`). **No trailing `;`** (UI rejects it). **Final
  `LIMIT 200`** (cap 500; not on inner CTEs, not on a P12 VIEW).
- Value math via `token_ledger.value_delta` (signed), not decoding `logs.data`.
- **Metadata:** `latest_token_info` (PK, 1:1) → `symbol`/`token_name`/`decimals`. **USD:**
  `<chain>.to_usd_value(raw, token)` (decimals + price in one call) or `network_token_info.last_price` when
  you need the fields — `round((… * last_price)::numeric, 2)` (last_price is double). LEFT JOIN so rows
  survive a missing price.
- **Token not in the event** → resolve in-tx from `token_ledger` (the moved token's row whose
  `value_delta` = the event amount), not a registry. Prefer this over TABLE+ref.
- Macros: `duration=` for the window; filter `topic0` directly (macro adds `committed`); `inputs='0x<addr>.Event(...)'`
  only to anchor one contract or get typed `decode_event` output.
- Every unique-key / template column must appear in SELECT.
- **Header comment (provenance) on every created query — both modes.** Lead the SQL with a comment:
  ```sql
  -- Created <UTC ISO8601 — from `date -u +%Y-%m-%dT%H:%M:%SZ`> · <query|alert> · dedaub-monitoring v<pyproject version>
  -- <one line: what it answers + protocol(s) / chain(s) / look-back window>
  ```
  Comments are preserved by the engine and satisfy the no-trailing-`;` rule (a query may *end* on a
  comment, and may freely *begin* with one). Keep it to ≤2 lines; it is the only in-SQL record of why
  the query exists and when it was made.

### Empirical gate (prove, don't guess) — validate first, then run
```bash
dedaub-monitoring validate-query   --id <ID>     # instant compile check: syntax/columns/types/macros
dedaub-monitoring explain-query    --id <ID>     # FREE real PG plan (plans, doesn't run) — verify index lead + no seq-scans BEFORE paying for a run
dedaub-monitoring preprocess-query --id <ID>     # only if validate fails: macro→SQL expansion
dedaub-monitoring run-query --id <ID> --duration <w> --limit 200 --timeout 30   # exec; killed at 30s
```
Iterate `write-query` → `validate-query` on the **same id** until valid before paying for a run.
**`explain-query --id <ID>` returns the real PG plan** (the same one app.dedaub.com shows) — run it in the
gate right after `validate`: it's **free** (plans, doesn't execute) and catches the planner mistakes that
otherwise cost you a run. **Read it for STRUCTURE, not magnitudes:** confirm each branch leads with the
intended index (`Index Scan using …logs_topic0…` / `…_address…` / selector) and that no big table gets a
`Seq Scan` (especially `latest_token_info`); the `cost=`/`rows=` numbers are **inflated** — the planner
can't constant-fold `get_historical_block_number()` so it assumes *all* chunks (§9) — so never read runtime
off them. Quick scan: `explain-query --id <ID> | grep -iE 'Seq Scan|Index Scan using logs_'`. Then confirm
real runtime with `run-query` latency + cheap `count(*)` probes.

**Tuning loop (each run <30s and ≥1 row):**
1. `--timeout 30`. If killed, **re-run** — first-run timeouts are usually cold cache (seen: 30s cold →
   ~5–7s warm). **Multi-chain UNIONs warm slowly:** the cold working set is ~K× a single-chain query
   (K chains' log chunks + each chain's `latest_token_info`/`outer_transaction`), so the *first 1–2* runs
   can both exceed 30s while the query is actually fine. Warm each branch first with a cheap `count(*)`
   probe (this also gives you the row counts), **or** use `--timeout 120` on the first run, then time the
   warm run. Shrink the cold set too: prefer `<chain>.tx_hash()` over an `outer_transaction` JOIN (§4).
   Only a timeout that **persists once warm** means real work, not cold cache → fix the lead (§3), shrink
   `--duration`, **or** recognise that a combined cross-chain UNION's runtime ≈ **sum** of its branch scans
   (shared worker pool, not the max), so one heavy branch (a busy-token value scan) busts 120s even warm →
   **split per-chain** (separate runs, merge in chat) or shrink the window.
2. Sub-30s: ≥1 row → gate passed (that's your validated window). 0 rows → window too narrow for a rare
   event; **ask the user** before widening `--duration` + `--timeout` (120s / 30d max).
3. Still 0 at 120s/30d → genuinely quiet; tell the user (valid, just hasn't fired).

Mid-run **Ctrl-C** / `cancel-query --task-id <id>` revokes the server task.

### Mode tail

**Query mode** — **own folder per query** (same discipline as alert mode; never dump into a shared
`/_scratch`). Name the folder with the **same canonical slug** `<Signal>-<Subject>-<Chain>` as alert mode
(see the Alert-mode §1 slug rules below) — multiple protocols or chains join with `+` in Step 0(b) priority
order (`Liquidations-AaveV3-Base+Arbitrum`). **The query inside takes a short role name only — never the
slug:** a single query → `Query`; a P12 split → `Detail` (row VIEW) + `Summary` (reader). The folder carries
the identity; the SQL name stays short.
```bash
dedaub-monitoring create-folder "/<slug>"            # e.g. /Liquidations-AaveV3-Base+Arbitrum
dedaub-monitoring create-query  "/<slug>/Query"      # role name only → /<slug>/Query; reuse the id all session (no deletes)
dedaub-monitoring write-query --id <ID> <<'SQL'
-- Created <UTC, `date -u +%Y-%m-%dT%H:%M:%SZ`> · query · dedaub-monitoring v<ver>
-- <one line: what it answers + protocol(s)/chain(s)/window>
<SQL>
SQL
dedaub-monitoring validate-query --id <ID>           # gate (above) — iterate write→validate on the same id
dedaub-monitoring run-query      --id <ID> --limit 200 --timeout 30
```
A re-run of the *same* question overwrites its own folder's query (idempotent); a *new* question gets a new
slug+folder. Show results + SQL + the query path/id + UI link (Step 6).

**Alert mode:**
1. **Own folder per alert** (never share). **Name it with the canonical slug
   `<Signal>-<Subject>-<Chain>`** — fixed token order, PascalCase tokens, single `-` between tokens:
   - *Signal* ∈ {`Liquidations`, `LargeTransfers`, `Drains`, `AdminChange`, `RoleChange`,
     `OracleDeviation`, `PauseUpgrade`, `Mints`, `Swaps`} (extend in the same style only when none fit).
   - *Subject* = protocol **with version, no spaces/inner hyphens** (`AaveV3`, `MorphoBlue`, `CompoundV2`,
     `Chainlink`); for a protocol-agnostic ask use the asset instead (`USDC`, `WETH`); for a
     **cross-protocol category** ask ("all lending / all DEXs") use the category noun (`Lending`, `DEX`,
     `Bridge`), not an enumerated `+`-join.
   - *Chain* = canonical Title-case name (`Ethereum`/`Base`/`Arbitrum`/`Optimism`/`Polygon`/`BNB`/
     `Avalanche`) — **never** ad-hoc abbreviations (`Arbitrum`, not `Arb`/`ArbBase`); multi-chain →
     priority-ordered `+`-join in the Step 0(b) order (`Base+Arbitrum`).
   - **Drop redundant/duplicate tokens** (no bare `USD`, no chain named twice). One token per slot.

   e.g. `Liquidations-MorphoBlue-Base`, `Liquidations-AaveV3-Arbitrum`, `Drains-AaveV3-Base+Arbitrum`,
   `LargeTransfers-USDC-Ethereum`. Then `create-folder "/<slug>"` → `create-query "/<slug>/<Name>"` where
   **`<Name>` is the query's short role only — never the slug** (the folder already carries it): a single
   alert → `Alert`; a P12 split → `Detail` (row VIEW) + `Summary` (reader); each `{{ref()}}` lookup → a
   short role noun (`View`/`Tbl`, or e.g. `Markets`). So `/Liquidations-MorphoBlue-Base/Alert`, not
   `/Liquidations-MorphoBlue-Base/Liquidations-MorphoBlue-Base`. `write-query`, run the gate
   (validate → run), iterate on the **same id** (no deletes). Before deploy, `query-columns --id <ID>` and
   confirm every `--unique-key` and every `--alert-template {{var}}` is in the output (most common deploy failure).
2. **Reviewer subagent** (`references/agents/reviewer.md`) — semantic only (right thing? scope/collision/
   threshold? readable template?). Draft inline (`references/handoff-schemas.md`); verdict is its final
   message. REJECT → revise (≤2 rounds).
3. APPROVE → tell the user the look-back window settled on, then follow `references/deploy-playbook.md`
   (`enable-alerts` → `get-logs` smoke-test → set final frequency / park).

**Protocol-coverage sub-branch** (cover a protocol, not one alert): from the ref's gotchas + key events,
propose **3–6 high-signal alerts** (drains, liquidations, admin/role changes, oracle deviations,
pause/upgrade), reject noise (new-pool, daily TVL), confirm with the user, then loop
generate→gate→review→deploy per alert (each its own folder). Proposals from the local ref, not web.

---

## Step 6 — Summary (chat only, no hand-off doc)

Alert mode: a table of alert | path | query id | network | frequency | status, plus `query-metadata` /
`get-alerts` / `get-logs` to manage, and the UI link `https://app.dedaub.com/tx-monitor?queryId=<id>` per
alert (call it out for notify-off: keeps refreshing, toggle notifications there). Query mode: results +
final SQL + the query's folder path & id + its UI link `https://app.dedaub.com/tx-monitor?queryId=<id>`
(the query persists in its own slug-named folder — no deletes; re-running the same question overwrites it).

---

## Reference map (read on demand)

| File | When |
|------|------|
| `…/sample_queries/common_query_patterns.md` | always (Step 1) — hub: schema, indexes, perf rules, pattern index, anti-patterns, checklist |
| `…/database/query_patterns.md` | Step 5 — full P1–P16 SQL templates (indexed by the hub §5) |
| `…/database/decode_primitives.md` | Step 5 — decode/enrich cheat-sheet (hub §4) |
| `…/database/macros.md` | Step 1/5 — macros, VIEW/`ref`/INCREMENTAL, CLI notes |
| `…/protocols/<name>/README.md` | Step 2a — version disambiguation + collisions |
| `…/protocols/<name>/<file>.md` | Step 2b — constants |
| `…/agents/reviewer.md` | Step 5 — semantic review |
| `…/agents/web-fallback.md` | Step 2c — no local ref |
| `…/handoff-schemas.md` | Step 5 — reviewer draft/verdict shapes |
| `…/review-criteria.md` | Step 5 — reviewer checklist |
| `…/deploy-playbook.md` | Step 5 — deploy, smoke-test, execution slot, timeout diagnosis |
