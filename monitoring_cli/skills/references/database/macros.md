# DedaubQL Macros — the query surface

One Postgres. DedaubQL = SQL + macros that wrap each table for time-bounded incremental execution.
**Always use macros, never raw `<chain>.<table>`** (raw = full-scan + timeout). Every table is real and
macro-wrapped; every `common_query_patterns.md` pattern is valid.

```bash
dedaub-monitoring get-schema --macros          # live macro/table list
dedaub-monitoring preprocess-query --id <ID>   # render macro→SQL (settle "what does this do" empirically)
```
`explain-query --id <ID>` = the **real PG `EXPLAIN` plan** (same plan app.dedaub.com shows), free — it plans
but doesn't execute. Read it for *index lead / `Seq Scan` vs index scan*, not its inflated `cost=`/`rows=`
(§9). ({{ref()}} dependency analysis is a separate backend call, not a CLI command.)

**Companion — `common_query_patterns.md`** (the SQL craft to this file's macro surface; most queries need
both): §1 schema/indexes · §2 block-times · §3 perf rules · §7 question→pattern · §8 edge cases · §9
anti-patterns. Its two siblings hold the bulk: **`query_patterns.md`** (§5 P1–P16 templates) and
**`decode_primitives.md`** (§4 decode/enrich cheat-sheet).

## Table macros

| Macro | Grain | Use for |
|-------|-------|---------|
| `{{outer_transaction(network=,duration=)}}` | 1 / top-level tx | `tx_hash`,`callvalue`,`status`,`from_a`/`to_a`,`input` — entry-call, ETH value |
| `{{transaction_detail(network=,duration=,inputs=)}}` | 1 / call frame | `from_a`/`to_a`/`calldata`/`callvalue`/`error`/`caller_vm_step_stack` — internal calls, selectors. Takes `duration=` + `inputs=` like `logs`. |
| `{{logs(network=,duration=,inputs=)}}` | 1 / emitted log | events by topic0 + emitter |
| `{{token_ledger(...)}}` / `{{token_transfers(...)}}` | parsed token deltas | value analytics (`value_delta` signed) > decoding `logs.data` |
| `{{contracts(...)}}` / `{{contract_list(...)}}` | deployed contracts | deployer / is-contract lookups |
| `{{block(...)}}` | block headers | tip, timestamps |

`outer_transaction` (`status`) vs `transaction_detail` (`committed`/`error`) = granularities, not rivals.

## Structural macros

- **`{{ref(query_id=<id>)}}`** / **`{{ref(table="/Folder/Name")}}`** — pull another query's output
  (VIEW/TABLE) by id or path (path form = shared `/lib/...` lists). How an INCREMENTAL alert or P12 reader
  gets a reusable lookup. Resolves on the **ethereum slot** (deploy-playbook §"Execution slot").
- **`{{eth_call("<addr>.fn(argtype arg)", outputs="( rettype output0 )", network='<c>')}}`** — live
  on-chain view call at tip → `<chain>.eth_call(addr,'sig(returns)',args_jsonb)`; returns a tuple
  (`output0`/`[0]`). **One RPC/row** → small sets only; for balances use `token_balance`.
- **`{{is_ancestor("a","b")}}` / `{{is_parent("a","b")}}`** — call-frame ancestry predicates joining two
  `transaction_detail` aliases in one tx (`a` is ancestor / direct parent of `b`). Reentrancy / nested-call
  (§5 P15). *Not incremental control.*
- **`{{is_backfilling}}`** — true during a backfill run (incremental control).
- **Parameterized queries** — `{{param}}`/`{{params}}` + the template system for user-configurable alerts:
  header `/* Parameters: … Category: ALERT|VIEW|MATERIALIZED */` declares typed params (`address`,
  `array<address>`, `array<function>`, `array<log>`, `number`, …); `{{net_config(ethereum={…}, base={…})}}`
  sets per-network defaults (incl. per-chain constant maps);
  `{% for network in networks('ethereum','base') %} … {% if not loop.last %}union all{% endif %} {% endfor %}`
  expands per network. Read `{{network.param("x")}}`, chain literal `{{network.get_chain_id()}}`,
  address→bytea via `address_to_bytea(x)::ethaddress` or `| to_address`. The hand-written per-chain
  `UNION ALL` (§5 P10) is the param-free equivalent.
- **Off-chain HTTP** (`http_get_json`, `common.http_post`) exists but is demo-grade (external dependency,
  secrets-in-SQL) — prefer `to_usd_value`/`network_token_info` for price, `eth_call` for state; reserve for
  genuine off-chain data, never secrets (§9).

## Event filtering: lead with `topic0` (no `inputs=` needed)

Monitoring queries decode by hand (`substring`/`get_byte`/`hex_to_numeric` — §4), so the lean default is to
filter `topic0` and let `{{logs}}` add `committed` + the window:
```sql
FROM {{logs(network='arbitrum', duration='7d')}} l
WHERE l.topic0 = '\x<event_topic0>'::bytea
```
This sidesteps the `indexed` footgun, is lighter than `inputs=` (which expands to the same `topic0=` plus an
unused `decode_event` join), and catches a protocol **and all forks** at once (one `PoolCreated` topic0
surfaced 6 V3 forks on Arbitrum).

**topic0 index — verify per chain.** Most chains carry a `(topic0, block_number, address)` btree on `logs`
(topic0-first is index-fast); **Base was observed without it** → on Base lead with `address`. Check with
`get-schema --network <c> --table logs` (or §1.1). Pair topic0 with a `duration=`/block bound regardless.

### `inputs=` — three forms (when you want the ABI decoder or a single-contract anchor)
1. `inputs='0x<addr>.Event(types)'` — contract-specific; adds `address=` → index-fast everywhere. Go-to for one known contract.
2. `inputs='Event(type indexed,…)'` — global topic0 form; mostly redundant with raw `topic0=` (extra `decode_event`). Prefer raw topic0.
3. Not indexed anywhere → proxy: filter a co-occurring indexed event (e.g. an incoming ERC-20 `Transfer`); note it in a comment.

**`indexed` is load-bearing in `inputs=`:** the macro maps params to topic vs `data` by the `indexed` flag.
Omit it on an indexed param → macro folds `topicN IS NULL` → **silent 0 rows**. Confirm with
`preprocess-query` (render must show `topicN is not null` + `"indexed": true`). Another reason raw `topic0=`
is the safer default.

## Materialization (`set-config --materialize`)

- **`VIEW`** — non-materialized, re-evaluated each run. The reusable lookup layer (with `ref`).
- **`TABLE`** — materialized snapshot, refreshed on schedule. For history-spanning sets. **Caveat:**
  materialization + `{{ref()}}` resolution run on the **ethereum/chain_id=1 slot** — a TABLE/VIEW configured
  only on a non-ethereum slot won't materialize and its `ref` fails. Prefer the in-tx `token_ledger` lookup
  (§4) where the datum is in the triggering tx. See deploy-playbook §"Execution slot".
- **`INCREMENTAL`** — incremental block processing + dedup on the unique key. The alert output
  (`enable-alerts` forces it; `--incrementalization IGNORE`|`UPSERT`).

`tx_hash` in results: native on `outer_transaction`; the others carry `(block_number,tx_index)` → JOIN
`outer_transaction` (1:1) or Arbitrum `arbitrum.tx_hash(block_number,tx_index)`. Readable `0x`:
`concat('0x', encode(col,'hex'))` (§4).

## CLI behavior notes (verified live)

- `run-query`/`preprocess-query`/`explain-query` require `--id`; omit SQL to use stored text (an `--id`-only
  call returns immediately rather than blocking on idle stdin). A macro's explicit `duration='…'`
  **overrides** `run-query --duration`.
- **No `delete-query`**; `delete-folder` (`--path`) refuses non-empty folders → can't clean up. Fix in place
  via `write-query`; reuse one `/_scratch/probe` for probing. (`create-folder` = positional PATH;
  `delete-folder`/`rename-folder` = `--path`/`--new-path`.)
- Materialization/notify config is **per-network** (`--network` on `set-config`/`get-config`/`enable-alerts`/
  `disable-alerts`/`list-alerts`). For a **network-agnostic** query (no `network=` — slot injects the chain)
  `--network` is the data chain. But a query hard-coding `network=` (incl. cross-chain `UNION`) fixes its data
  chain in SQL while the materializer/scheduler runs on **chain_id=1** → deploy on the **`ethereum` slot** or
  it silently never runs (`Unable to locate query … chain_id=1`). `materialize` takes no `--network` (always
  chain_id=1); `reset-materialization` is broken (POSTs no body → 422). See deploy-playbook §"Execution slot".
- `run-query --timeout <s>` kills the run by revoking the **server** task (prints task id). **Ctrl-C** or
  `cancel-query --task-id <id>` also revokes. `--timeout 30` for the gate (Step 5), 120 max with user OK;
  default (no flag) is long (30m).
