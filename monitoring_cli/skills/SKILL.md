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

**Must-read first — protocol map.** Skim `references/protocols/INDEX.md`: the category/chain → protocol
lookup (which slugs are bridges / DEXs / lending / LST / restaking / perps / oracle, and which of the 7
chains each covers). Use it to turn a **category or chain** ask ("bridge volume X→Y", "all DEXs on Base",
"lending on Arbitrum") into the right `<slug>/` set before Step 2. It's an index only — never a source of
constants; always open the named `<slug>/<file>.md` for the actual topics/selectors/addresses.

1. **Auth:** `dedaub-monitoring entities` — if it fails, ask the user to `login` and stop.
2. **Schema (don't WebFetch):**
   ```bash
   dedaub-monitoring get-schema --macros            # macro/table set
   dedaub-monitoring get-schema --network <net>     # tables+columns per target net; scope with --table <t>
   ```
   `get-schema` is authoritative for tables/columns; refs supply *constants only*. Verify per chain
   (coverage varies). For money/token asks: `network_token_info` (PK `token_address`) carries
   `last_price`+`symbol`+`decimals`+`logo_*`+`presentation_symbol` — **the canonical USD-price source, kept
   up to date; LEFT JOIN it for prices** (`latest_token_info` is metadata, no price), but `last_price` is
   **NULL for stablecoins** (USDC/USDT/DAI are the USD quote unit → `to_usd_value` returns **0** for them;
   pin to \$1 by address — §5 USD rule).
   `logs.topic0` is indexed on most chains but **not Base** →
   on Base lead with `address`, never bare `topic0`.
3. **Pick mode** — query (run + show) vs alert (deploy on schedule). **If the user didn't explicitly name
   the mode, ask via `AskUserQuestion` — do not infer it from phrasing.** "summarize …", "show me …",
   "what are the …" can be a one-off read *or* the spec for a recurring feed; the same protocol+event ask
   is valid in both modes. Skip the question only when the words pick the mode ("alert me", "notify",
   "set up monitoring", "every N min" → alert; "run a query", "show me now", "one-off" → query).

   **Explicit choices win.** When the user names a network/chain, mode, address, threshold, or window, use it
   verbatim — don't re-identify or override it. If on-chain identity suggests otherwise (e.g. the address
   resolves as an Arbitrum pool, not the Ethereum one asked for), surface the conflict **once** in chat and
   proceed on the user's stated value unless they correct you — never silently switch or silently re-ask.
4. **Alert mode — collect prefs once (reuse all session), in order. `AskUserQuestion` for all but (a).**
   These (a)–(d) are the **complete clarifying set — invent no others**; in particular the materialization
   tier (CTE / VIEW+`ref` / TABLE+`ref`) is **agent-decided from the Step 4 table, never a user pop-up** —
   apply it the same way every run.

   **(a) Condition** — free text. User types protocol + event/threshold (e.g. "USDC transfers > \$1M",
   "Aave v3 admin change", "Morpho liquidations"). The one thing you can't enumerate. **Invite specifics:**
   they may paste a **contract address / event sig / topic0 / function sig / selector**, or **name a whole
   protocol** for a 3–6 alert suite (Step 5 sub-branch). A supplied **signal identity** (topic0 / event sig /
   selector) means you already hold the constant → **skip Step 2**, feed it into Step 3/5 (identity-only →
   all-forks; identity + address → pinned; bare address alone doesn't skip). Trust it; the Step 5 gate catches
   a wrong constant.

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
| **Data source** | `logs` (events) / `outer_transaction` (tx) / `transaction_detail` (call frames + `caller_vm_step_stack` depth, `is_ancestor`) / `token_ledger`,`token_transfers` (value) / `token_balance` (holder balances) / `eth_call` (live state) / `protocol_contract` (attribute to a protocol) / `dex_pool` (token-pair → pool / V4 PoolId resolution — §4) |
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

Local refs authoritative; web only as fallback (2c). **Skip this whole step** when the user supplied a
**signal identity** at intake (Step 0(4a)) — topic0 / event sig / selector — you already hold the constant;
go straight to Step 3 with it. (A bare contract address doesn't skip: it pins the deployment but you still
need the event/call identity, so look that up here.)

**2a. Find the file.** Category/chain ask (not a named protocol)? Resolve the slug set via
`references/protocols/INDEX.md` first (§1 category→protocols reverse-map + §2 chain table). Then:
`ls references/protocols/<name>/`
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

**Start at the default, escalate stepwise autonomously up to ×4** (Base 24h→48h→96h); beyond ×4 — toward
the 30d cap — only with user OK (Step 5 tuning loop). 0 rows usually means "nothing matched", not "wrong
SQL". **Look-back ≠ semantic interval:** a condition like "upgraded within 5s of deploy" is a WHERE
predicate, not the window — a *rare* conjunction needs **more** look-back to ever see an instance, and
**0 rows can be its valid steady state** for a deployed alert. Report the window that produced rows;
surface it before deploy. Each test run <30s (120s max, only with user OK).

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
(`ORDER BY … LIMIT N` only when top-N is the semantics — Step 5 mode-scoped rule).
Cross-chain key = **`(address, chain_id)`**, never bare `address` (same address recurs —
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
- **Signal identity — prefer signature form; annotate any raw literal.** Write event/call filters with the
  signature-string macro forms (`inputs='0x<addr>.Event(type indexed name,…)'`,
  `{{<chain>.transaction_detail("fnName(type name,…)")}}`) so the SQL names what it watches — `indexed`
  flags must be exact (macros.md footgun). Raw `\x` topic0/selector literals stay for **all-forks** scans
  (one topic0 = every fork) — but EVERY raw literal carries an inline `-- EventName(types)` /
  `-- fnName(types)` comment, no exceptions.
- **Call monitoring filters `call_opcode = 'CALL'`** by default (`transaction_detail` has one row per
  *frame*: a proxy call also yields a DELEGATECALL frame with the same calldata → double-counted proxies,
  implementation addresses matched). Drop it deliberately — and say so in the header comment — when the
  delegatecall surface (self-upgrades, diamond facets) is in scope (§8).
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
- No `SELECT *` (TOAST: `calldata`/`data`/`returndata`). **No trailing `;`** (UI rejects it).
- **`LIMIT 200` / `ORDER BY` are mode-scoped.** Query mode + gate/test runs: final `SELECT` ends with
  `LIMIT 200` (cap 500; + `ORDER BY` for display; never on inner CTEs). **Deployed alerts and materialized
  queries carry NEITHER** — a `LIMIT` silently drops alert rows in a busy refresh / truncates a registry,
  and the sort is wasted work; dedup is the unique-key's job, bounding is the frequency window's job.
  Strip both before deploy. Exception: top-N-by-design (leaderboard reader) keeps `ORDER BY … LIMIT N` —
  there it IS the semantics.
- Value math via `token_ledger.value_delta` (signed), not decoding `logs.data`.
- **Metadata:** `latest_token_info` (PK, 1:1) → `symbol`/`token_name`/`decimals`. **USD price — LEFT JOIN
  `network_token_info`:** `LEFT JOIN <chain>.network_token_info nti ON nti.token_address = token`, read
  `nti.last_price` (double, **kept up to date — the canonical price source**):
  `round((raw / pow(10, nti.decimals) * nti.last_price)::numeric, 2)`. LEFT JOIN so rows survive a missing
  price (NULL, not a silent 0). `<chain>.to_usd_value(raw, token)` is the one-call convenience (decimals +
  price internally) but **silently returns 0 for any unpriced token** — reserve it for quick one-offs where
  every token is known-priced. **Stablecoins carry NO price** — `last_price` is **NULL** for USDC/USDT/DAI (the
  USD quote unit), so `to_usd_value` returns **0** for them (silently zeroing the commonest collateral). Pin
  stables to \$1 **by address**: `COALESCE(nti.last_price::numeric, CASE WHEN token = ANY(ARRAY['\x…usdc…'::bytea,
  '\x…usdt…'::bytea]) THEN 1.0 END)` — **never** a blanket `COALESCE(…, 1)` (misvalues a genuinely unpriced
  *volatile* token at \$1). Verify per chain which collaterals are NULL before trusting a USD sum.
  **Now vs then:** `last_price` is *current* price; for value **at the time of an event** or **over time**
  (historical/backtested USD, stablecoin depeg, mcap/supply trends) use `common.historical_token_price`
  (as-of nearest-prior `ts`, §4) — which **does** price stablecoins.
- **Token not in the event** → resolve in-tx from `token_ledger` (the moved token's row whose
  `value_delta` = the event amount), not a registry. Prefer this over TABLE+ref.
- Macros: `duration=` for the window; signature forms preferred (the signal-identity rule above; macro adds
  `committed`); raw `topic0` filtering for all-forks scans, always annotated.
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
2. Sub-30s: ≥1 row → gate passed (that's your validated window). 0 rows → **auto-widen stepwise to ×4 of
   the per-chain default (Step 3), then STOP and ask the user**, offering: (a) widen further (toward
   120s / 30d max), (b) temporarily loosen the rare qualifiers to prove the *base* event fires — e.g. drop
   the "≤5s after deploy" / "non-deployer" predicates, confirm `upgradeToAndCall` calls appear, restore
   them — or (c) accept 0 rows and deploy: for a rare conjunction, **0 rows IS the expected steady state**,
   not a broken query. Don't burn run after run optimizing toward a row that may not exist.
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
| `…/protocols/INDEX.md` | **Step 0 (startup) + Step 2a** — category & chain → protocol(slug) lookup map; resolve a category/chain ask to the right `<slug>/` |
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
