# DedaubQL Macros — the query surface

The monitoring engine is **one Postgres**. Queries use DedaubQL: SQL with macros that wrap each
table for **time-bounded incremental execution**. The README is explicit: use macros, never raw
`<chain>.<table>` (raw tables full-scan and time out). There is **no "dialect A vs B"** — every
table below is real and macro-wrapped; `common_query_patterns.md`'s patterns are all valid.

Get the live list any time: `dedaub-monitoring get-schema --macros`. See any macro's expansion:
```bash
dedaub-monitoring preprocess-query --id <ID> <<'SQL'
SELECT * FROM {{logs(network='ethereum', duration='5m', inputs='0x<addr>.Transfer(address,address,uint256)')}}
SQL
```
`preprocess-query` renders macro → SQL (settle any "what does this do" empirically). `explain-query`
is **dependency analysis** (which queries this references via `ref`) — **not** a PG plan.

> **Companion doc — `common_query_patterns.md`** (in `sample_queries/`). This file is the *macro surface*;
> that one is the *SQL craft*, and most real queries need both. Reach for it for: **§1.1** index inventory
> (which column to lead with, per chain) · **§2** block-time table (`duration=` ↔ blocks per min/hour/day,
> per chain) · **§3** performance rules · **§4** decode primitives (`substring` topics, `hex_to_numeric`,
> readable `concat('0x', encode(…))`) · **§5** ready-made patterns **P1–P11** · **§8** edge cases (multicall
> → unique key on `log_index`; exclude reverts) · **§9** anti-patterns (incl. the chain-dependent
> `topic0`-alone caveat).

## Table macros (pick by what you need)

| Macro | Grain | Use for |
|-------|-------|---------|
| `{{outer_transaction(network=,duration=)}}` | one row per top-level tx | `tx_hash`, `callvalue`, `status`, `from_a`/`to_a`, `input` — entry-call detection, ETH value |
| `{{transaction_detail(...)}}` | one row per **internal call frame** | call-frame `from_a`/`to_a`/`calldata` — internal calls, selector detection |
| `{{logs(network=,duration=,inputs=)}}` | one row per emitted log | events by topic0 + emitter |
| `{{token_ledger(...)}}` / `{{token_transfers(...)}}` | parsed token deltas | value analytics (`value_delta` signed) — beats decoding `logs.data` |
| `{{contracts(...)}}` / `{{contract_list(...)}}` | deployed contracts | deployer / is-contract lookups |
| `{{block(...)}}` | block headers | tip, timestamps |

`outer_transaction` vs `transaction_detail` are **different granularities, not rivals** — that's why
their columns differ (`status` vs `committed`/`error`). Use the one the question needs.

## Structural macros

- **`{{ref(...)}}`** — reference another query's output (a VIEW or TABLE). This is how a final
  INCREMENTAL alert reads a reusable lookup layer. (See Step 4: CTE / VIEW+ref / TABLE+ref.)
- `{{param(...)}}` / `{{params(...)}}` — parameterize.
- `{{is_backfilling}}` / `{{is_ancestor}}` / `{{is_parent}}` — incremental-execution control.

## When the macro features win

| Feature | Beats | Why |
|---------|-------|-----|
| `duration='5m'` | `block_number BETWEEN (SELECT MAX(block_number) FROM <chain>.block) - N AND MAX` | one param, tied to refresh cadence |
| `inputs='0x<addr>.Event(types)'` | address scan + topic0 filter | uses the ABI index to pre-filter logs at storage level |

### Filtering events: lead with the `topic0` constant (no `inputs=` needed)

Monitoring queries decode fields by hand (`substring`/`get_byte` over `topic1..3`/`data` — see the
companion doc **§4** for the decode primitives), so they don't need the macro to decode anything. The lean, robust default is to filter on **`topic0`** — the
event-signature hash your protocol ref already lists — and let `{{logs(...)}}` supply `committed` + the
window:

```sql
FROM {{logs(network='arbitrum', duration='7d')}} l
WHERE l.topic0 = '\x<event_topic0_hash>'::bytea     -- the constant straight from the protocol doc
```

This consumes the topic0 the refs already carry (no per-doc churn), sidesteps the `indexed` footgun
entirely (no decoder to match), and is strictly lighter — `inputs=` expands to the **same** `topic0 =`
filter **plus** a `decode_event(...)` join you don't use. It's also how you catch a protocol **and all
its forks** at once: every contract emitting that exact signature matches (one `PoolCreated` topic0
surfaced 6 V3-fork factories on Arbitrum).

**Chain note — `topic0` is indexed on all 8 chains today.** Every supported chain (`ethereum`, `base`,
`arbitrum`, `optimism`, `polygon`, `binance`, `avalanche`, `blast`) carries a `(topic0, block_number,
address)` btree on `logs`, so topic0-first is index-fast everywhere — just pair it with a
`duration=`/block-range bound so the time window is indexed too. Indexes can change: verify with
`get-schema --network <chain> --table logs` (or `common_query_patterns.md` §1.1) before assuming. If a
chain ever lacks it, add `address = '\x<contract>'` as the leading predicate. `EXPLAIN` is blocked
through the CLI; confirm the plan in the web console **Visualize** tab.

### `inputs=` — when you actually want it (three forms)
Reach for `inputs=` when you want the ABI **decoder** (`e.input` typed fields), or a single-contract
anchor that stays fast even on chains without a `topic0` index:
1. `inputs='0x<contractaddr>.EventName(type1,type2,...)'` — contract-specific; adds `address =`, so it's
   index-fast on every chain. The go-to for **one** known contract.
2. `inputs='EventName(type1 indexed,type2,...)'` — global topic0 form. Mostly redundant with a raw
   `topic0 =` filter (same index, extra `decode_event` overhead) — prefer raw topic0 unless you want the
   decoded record.
3. Not indexed anywhere → **proxy approach**: filter a co-occurring efficiently-indexed event (e.g. an
   incoming ERC-20 `Transfer` to the contract). Document the proxy in a comment.

**If you use `inputs=`, `indexed` is load-bearing — not cosmetic.** The macro maps each param to a topic
vs `data` by its `indexed` flag, so the signature must match the ABI exactly. Omit `indexed` on a param
that *is* indexed and the macro assumes that topic is unused and folds `topic1/2/3 IS NULL` into the
WHERE — **silently returning 0 rows, no error**. Confirm with `preprocess-query`: the render must show
`topicN is not null` + `decode_event('… "indexed": true …')`, never `topicN is null`. (One more reason
the raw `topic0 =` filter above is the safer default.)

## Materialization (set via `set-config --materialize`)

- **`VIEW`** — non-materialized; re-evaluated each run. The reusable lookup layer (pair with `ref`).
- **`TABLE`** — materialized snapshot, refreshed on a schedule. For expensive history-spanning sets.
- **`INCREMENTAL`** — incremental block processing + dedup on the unique key. **The alert output.**
  `enable-alerts` forces this; `--incrementalization IGNORE` (skip dup keys) or `UPSERT` (update).

`tx_hash` on `logs`: JOIN `outer_transaction` on `(block_number, tx_index)`; on Arbitrum use
`arbitrum.tx_hash(block_number, tx_index)` to skip the JOIN. Readable `0x` SELECT output: see
`common_query_patterns.md` §4 (`concat('0x', encode(col,'hex'))`).

## CLI behavior notes (verified live)

- `run-query`/`preprocess-query`/`explain-query` **require `--id`**; omit SQL to use stored text. They
  read piped SQL only when bytes are actually waiting on stdin, so an `--id`-only call from an agent or
  subprocess returns immediately instead of blocking on an idle stdin. A macro's explicit `duration='…'`
  **overrides** `run-query --duration` (the flag is only a default for macros with no window).
- **No `delete-query` exists**, and `delete-folder` (use `--path`, not positional) **refuses non-empty
  folders** → a query can't be cleaned up. Fix wrong queries **in place** via `write-query`; for
  query-mode probing reuse one persistent `/_scratch/probe`. (`create-folder` takes a **positional**
  PATH; `delete-folder`/`rename-folder` use `--path`/`--new-path`.)
- Materialization/notify config is **per-network**; pass `--network` on `set-config`/`get-config`/
  `enable-alerts`/`disable-alerts`/`list-alerts` to match the chain your query's macros read.
