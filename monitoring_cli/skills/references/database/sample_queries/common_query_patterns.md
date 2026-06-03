# Common Queries — Database Query Patterns (hub)

**Audience:** an agent translating a business question into SQL against the blockchain schema.
**Pairs with:** a protocol knowledge-base doc (e.g. `protocols/uniswap/v3.md`) for *constants*.

This file is the **rulebook + index**: schema (§1), block-times (§2), perf rules (§3), the pattern
catalogue (§5 index), routing (§7), edge cases (§8), anti-patterns (§9), checklist (§10). Two heavy
sections live in siblings and are pulled when you actually write SQL:

- **`../decode_primitives.md`** (§4) — the decode/enrich cheat-sheet (topics, `hex_to_numeric`, USD, `eth_call`, …).
- **`../query_patterns.md`** (§5) — the full P1–P16 SQL templates.

> **How to use.** The protocol doc supplies *constants* (addresses, selectors, topic0 hashes, assets).
> Pick the pattern via §7 (or the §5 index), open `query_patterns.md` for the template, substitute
> constants, and obey §3 (indexes) + §8 (edge cases). `§N` references resolve here regardless of which
> sibling file you're reading.

> **Macro-wrap.** Templates show raw `<chain>.<table>` for clarity, but DedaubQL runs them through
> **macros** — `{{logs(...)}}`, `{{outer_transaction(...)}}`, `{{transaction_detail(...)}}`,
> `{{token_ledger(...)}}`, … — never bare `<chain>.<table>` (full-scans, times out). The
> `block_number BETWEEN (SELECT MAX…) - N AND MAX` predicate (§2) collapses to the macro's `duration=`.
> See `../macros.md`.

---

## 1. Schema cheat-sheet

Per-chain schema (`base.`, `ethereum.`, `arbitrum.`, `optimism.`, `polygon.`, `binance.`, `avalanche.`, `blast.`). All tables below exist on every chain unless noted.

| Table | PK | Purpose |
|-------|----|---------|
| `<chain>.outer_transaction` | `(block_number, tx_index)` | One row per **top-level tx**. `tx_hash`, `from_a`/`to_a`, `callvalue` (wei → ETH value), `status` (`false` = reverted), `input`. Entry-call / ETH-value detection. |
| `<chain>.transaction_detail` | `(block_number, tx_index, vm_step_start)` | One row per executed call frame. `from_a` = caller, `to_a` = callee, `calldata` = input bytes. Also: `callvalue`, `error`, `call_opcode`, and **`caller_vm_step_stack` (int[])** — the call-frame stack, so `coalesce(array_length(caller_vm_step_stack,1),0)` = **call depth** (0 = top-level/EOA-initiated, >0 = nested via router/bundler/contract). |
| `<chain>.logs` | `(block_number, tx_index, vm_step)` | One row per emitted `LOG*`. `address` = emitter, `topic0..3`, `data`. |
| `<chain>.token_ledger` | `(address, block_number, tx_index, vm_step_start, vm_step)` | Parsed token balance deltas. One row per side of each transfer; `value_delta` is signed. |
| `<chain>.token_transfers` | `(block_number, tx_index, vm_step_start, vm_step)` | One row per token transfer: `token_address`, `from_a`, `to_a`, `value` (unsigned). Lighter than `token_ledger` when you don't need signed deltas / counterparty. |
| `<chain>.contracts` | `(address)` | One row per deployed contract. `deployer`, `block_number`. |
| `<chain>.block` | `(block_number)` | Block headers; source of truth for tip and timestamps. |
| `<chain>.token_balance` | `(token_address, owner_address)` | **Current** ERC-20 balance per holder: `value` (numeric, raw units), `block_number` (last update). Indexed on `owner_address` and `token_address`-leading PK → both "holders of token X" and "balances of address Y" are index-fast. Holder/concentration/whale analytics — no log replay needed. Referenced raw (no macro). |
| `<chain>.protocol_contract` | `(protocol_id, address)` | Maps a contract `address` → `protocol_id` for **Watchdog-supported** protocols. JOIN `token_ledger`/`logs`/`transaction_detail` `USING (address)` to attribute activity to a protocol without hardcoding its address set. Pair with `<chain>.protocol (protocol_id, protocol_name)` for the readable name. Referenced raw. |

### 1.1 Index inventory (use these as leading predicates)

> **Per-chain caveat:** indexes vary by chain. **`logs.topic0` is indexed on most chains** (`(topic0, block_number, address)` btree → topic0-first is index-fast) but **Base was observed without it** — there, lead with the `address` index. Before assuming an index is present or missing, run `get-schema --network <chain> --table <t>` (or `\d+ <chain>.<t>`). Where the index exists, the matching §9 anti-pattern stops being one.

| Table | Indexes (baseline, present on every chain) |
|-------|--------------------------------------------|
| `transaction_detail` | `(block_number)`, `(from_a, block_number)`, `(to_a, block_number)`, `(common.selector(calldata), block_number)`, **`(to_a, common.selector(calldata), block_number)`** ← workhorse |
| `logs` | `(address, block_number DESC)`, `(block_number DESC)`, **`(topic0, block_number, address)`** — topic0 indexed on most chains, **not Base** (verify per chain) |
| `token_ledger` | `(address)`, `(address, block_number, tx_index, vm_step_start, vm_step)`, `(block_number)`, `(block_number, tx_index, vm_step_start, vm_step)` |
| `contracts` | `(address)` [pkey], `(deployer)`, `(block_number)` |
| `token_balance` | `(token_address, owner_address)` [pkey], `(owner_address)`, `(block_number)` — lead with `token_address` for holders-of-a-token, `owner_address` for balances-of-an-address |

### 1.2 Helper functions (PG18+)

| Helper | Returns | Use |
|--------|---------|-----|
| `common.selector(bytea)` | `bytea(4)` | First-4-byte function selector; **indexed** on `transaction_detail`. |
| `common.hex_to_numeric(text)` | `numeric` | Decode `'0x…'` hex (e.g. `logs.data` payloads) to numeric. |
| `<chain>.block_timestamp(int8)` | `timestamptz` | Block number → wall clock. Prefer over joining `<chain>.block` for time bucketing. |
| `<chain>.to_usd_value(numeric, token)` | `numeric` | Raw amount → USD (decimals + price handled). See `decode_primitives.md`. |
| `<chain>.get_chain_id()` | `int` | Numeric chain id literal. |
| `<chain>.tx_hash(int8, int)` | `ethword` | `(block_number, tx_index)` → tx hash (confirmed on ethereum/arbitrum). |

### 1.3 Custom types

| Type | Definition | Literal form |
|------|------------|--------------|
| `common.ethaddress` | `bytea` (20) | `'\x833589fcd6edb6e08f4c7c32d4f71b54bda02913'::bytea` |
| `common.ethword` | `bytea` (32) | `'\xddf252ad…b3ef'::bytea` |

Addresses in literals must be **lowercased** (no checksum casing) and prefixed `\x`.

---

## 2. Block-time conversions

| Chain | Block time | Blocks per minute | Per hour | Per day | Per week |
|-------|-----------|-------------------|----------|---------|----------|
| Ethereum (1) | 12 s | 5 | 300 | 7,200 | 50,400 |
| Base (8453) | 2 s | 30 | 1,800 | 43,200 | 302,400 |
| Optimism (10) | 2 s | 30 | 1,800 | 43,200 | 302,400 |
| Arbitrum One (42161) | ~0.25 s | 240 | 14,400 | 345,600 | 2,419,200 |
| Polygon PoS (137) | ~2 s | 30 | 1,800 | 43,200 | 302,400 |
| BNB (56) | 3 s | 20 | 1,200 | 28,800 | 201,600 |
| Avalanche C (43114) | ~2 s | 30 | 1,800 | 43,200 | 302,400 |
| Blast (81457) | 2 s | 30 | 1,800 | 43,200 | 302,400 |

**Rolling block-window predicate** (always block-indexed, fastest):

```sql
WHERE block_number BETWEEN
        (SELECT MAX(block_number) FROM <chain>.block) - {{N_BLOCKS}}
        AND (SELECT MAX(block_number) FROM <chain>.block)
```

**Exact-time predicate** (slower; loses block-index leading column — use only for SLA/billing):

```sql
WHERE <chain>.block_timestamp(block_number) BETWEEN now() - interval '{{X}}' AND now()
```

---

## 3. Performance rules (non-negotiable)

| # | Rule | Why |
|---|------|-----|
| 1 | **Always lead with an indexed column.** `address`, `to_a`, `from_a`, `common.selector(calldata)`, `block_number`. | Sequential scans over `logs` / `transaction_detail` are minutes-to-hours. |
| 2 | **Always include a block-range filter.** | Without one, even the best index scans the whole table. |
| 3 | **For `logs`, `topic0` is indexed on most chains (not Base)** — where present, `WHERE topic0 = …` alone is index-fast (and catches every fork); add `address = …` to pin one deployment. On Base (no topic0 index) lead with `address`. Verify per chain (§1.1). | A `(topic0, block_number, address)` btree carries it — always pair with a `block_number`/`duration=` bound so the window is indexed too. |
| 4 | **Prefer `transaction_detail` as the driving table for function-call detection.** | The `(to_a, selector, block_number)` composite is the cheapest entry point. |
| 5 | **Prefer `token_ledger` over decoding `logs.Transfer.data` for value analytics.** | Already parsed, signed, joined to counterparty; no TOAST hit. |
| 6 | **Don't `SELECT *`.** | `calldata`, `returndata`, `logs.data` are TOAST-stored. Project explicit columns. |
| 7 | **Join `transaction_detail` ↔ `logs` ↔ `token_ledger` on `(block_number, tx_index)`.** | All three have it indexed (directly or as a prefix). Add `vm_step` / `log_index` only when ordering inside a tx matters (multicall). |
| 8 | **`committed = true AND error IS NULL` excludes reverts.** Include both. | A revert still produces a `transaction_detail` row but no state effects. |
| 9 | **Never end a query with a trailing `;`.** End on the last token (or a comment). | The platform UI **rejects** a query terminated by a semicolon — applies to every query and `{{ref()}}`'d lookup. |
| 10 | **Default the final result to `LIMIT 200`.** End the outer/final `SELECT` with `LIMIT 200` unless the user asks for more (cap 500) or an aggregate returns one row. | Keeps result payloads bounded; 200 is the house default for the final output (not inner CTE/lookup scans). |

---

## 4. Decode primitives → `../decode_primitives.md`

Full cheat-sheet in the sibling file. Inventory (what's covered): selector · indexed-topic→address ·
`uint256`/packed-`uint24` from `data` · readable `0x` output · `tx_hash` in result · amount→human ·
ERC20 metadata (`latest_token_info`) · **USD `to_usd_value`** · price/logo (`network_token_info`) ·
**live state `eth_call`** · **holders `token_balance`** · is-contract / contract-creation ·
`get_chain_id()` · **mint/burn (zero-address)** · **price drift (÷0-safe)** · 1:1 `LATERAL` enrich ·
**token-not-in-event → resolve in-tx via `token_ledger`** · `chain_id` literal · time-bucket.

---

## 5. Query patterns (P1–P16) → `../query_patterns.md`

Full SQL templates in the sibling file. Index (pick via this table or §7, then open `query_patterns.md`):

| P | Pattern | Use when |
|---|---------|----------|
| P1 | Function-call discovery (`to_a`+selector) | how often / by whom / against which contracts is fn X called |
| P2 | Event discovery (`address`+topic0) | how often is event E emitted, what data it carries |
| P3 | Tx ↔ logs correlation | calldata-side metadata (caller/gas) + an event side-effect in the same tx |
| P4 | Value movement (`token_ledger`) | amounts of a token moving between actors |
| P5 | Authorizer attribution | caller ≠ initiator (meta-tx / permit / Permit2 / 4337 / relayer) |
| P6 | Time-bucketed aggregation | dashboards, time-series, growth |
| P7 | Top-N actors | leaderboards (top spenders/receivers/contracts/relayers) |
| P8 | Bipartite graph | sender→receiver edges, churn, repeat-business |
| P9 | Multi-path / multi-contract | >1 entrypoint — `UNION ALL` per path |
| P10 | Cross-chain unification | which chains / aggregate across chains — `UNION ALL` per chain |
| P11 | Contract discovery | who deployed X / contracts by deployer |
| P12 | Split analytical (VIEW + reader) | sum / total / volume / leaderboard, esp. cross-chain |
| P13 | Absence / staleness | X hasn't happened in N (oracle stale, keeper/heartbeat missed) |
| P14 | Protocol drain | net USD out of a protocol in one tx |
| P15 | Reentrancy (`is_ancestor`) | a call nested inside another call (same callee re-entered) |
| P16 | Anomaly vs baseline | sudden drop / spike vs recent norm (window `LAG`/rolling `AVG`) |

§4 primitives also stand alone as "patterns" for: holders/concentration (`token_balance`), live state
(`eth_call`), mint/burn, price drift.

---

## 6. What to extract from a protocol doc

To plug into the patterns, pull the following from the paired knowledge-base doc:

| Variable | Source in knowledge-base doc | Plug into |
|----------|------------------------------|-----------|
| `{{CHAIN}}` | The "Scope" or "Addresses" section | All patterns |
| `{{CONTRACT}}` (callee) | "Addresses" table — pick the entrypoint(s) asked about | P1, P3, P4, P5, P6, P7, P9 |
| `{{SELECTOR}}` (4 bytes, `'\x........'`) | "Function selectors" / "Function signatures" table | P1, P3, P4, P5, P6, P7 |
| `{{EMITTER}}` (event source) | Usually same as the callee, occasionally a downstream proxy | P2, P3, P5 |
| `{{TOPIC0}}` (32 bytes) | "Event signatures & topic0 hashes" table | P2, P3, P5 |
| `{{TOKEN}}` + `{{DECIMALS}}` | "Addresses" — asset row (USDC=6, WETH=18, USDT=6, WBTC=8, …) | P4, P6, P7, P8 |
| `{{AUTH_TOPIC0}}` (signer-revealing event) | An event whose `topic1` is the off-chain signer (`AuthorizationUsed`, `OrderFilled`, `UserOperationEvent`) | P5 |
| Multi-path contract set | "Protocol architecture" — Path A / Path B / Universal Router / etc. | P9 |
| Deny-list contracts / noise | "Edge cases" / "Open questions" — e.g. Coinbase Commerce, MEV bots | §8 noise filter |

If the protocol doc lacks a value, **stop and ask** — never guess a selector or topic0; the wrong constant returns silent zero rows.

---

## 7. Business question → pattern map

| Business question | Pattern(s) | Required protocol inputs |
|-------------------|-----------|--------------------------|
| "How many txs per day does protocol X do?" | P1 + P6 | callee, selectors |
| "What's the volume of X?" | P1 + P4 + P6 | callee, selectors, token, decimals |
| "Who are the top users / customers?" | P5 + P7 | callee, selectors, auth-event topic0 (or token+decimals) |
| "Who are the top sellers / receivers?" | P4 + P7 (`GROUP BY counterparty`) | callee, selectors, token, decimals |
| "Which relayers / facilitators dominate?" | P1 + P7 (`GROUP BY td.from_a`) | callee, selectors |
| "Track a single user's activity" | P5 with `WHERE initiator = …` | callee, selectors, auth-event topic0 |
| "What's the activity over the last N hours/days?" | P1 + P6 with `BUCKET` | callee, selectors |
| "Bipartite payer↔seller graph" | P8 | callee, selectors, token, decimals |
| "Are there reverted attempts? Abuse?" | P1 with `td.error IS NOT NULL` | callee, selectors |
| "Detect the protocol across multiple on-chain paths" | P9 | per-path callee + selector set |
| "Multi-chain aggregate" | P10 (UNION ALL per chain) | per-chain `{{CHAIN}}` + addresses |
| "Total / sum / volume aggregate (esp. cross-chain)" | **P12** (row-level VIEW + `{{ref()}}` reader) | as the underlying P4/P7/P10 row scan needs |
| "Who deployed contract X?" | P11 | deployer address |
| "When was contract X first active?" | P11 + P1 with `ORDER BY block_number ASC LIMIT 1` | callee |
| "Match an off-chain event ID to an on-chain settlement" | P5 (use `auth_nonce` from `topic2`) | callee, auth-event topic0 |
| "Detect new contracts being deployed by relayers" | P11 with `WHERE deployer = ANY(known_relayers)` | known relayer EOAs |
| "X hasn't happened in N hours" (oracle stale, keeper missed, heartbeat) | **P13** (absence / anti-join) | watched addresses, expected selector/topic0, SLA window |
| "Protocol drained / lost >$N in one tx" | **P14** (drain, net USD per tx) | protocol_id (via `protocol_contract`) or its addresses, USD threshold |
| "Reentrancy / call nested inside another call" | **P15** (`is_ancestor`) | callee address + the re-entered selector |
| "Sudden drop / spike vs recent norm" (TVL, withdrawals, volume) | **P16** (window LAG / rolling AVG) | the metric + bucket + threshold |
| "Holders / concentration / whale balance" | `token_balance` (§4) | token address (+ N) |
| "Live contract state (supply, price, config)" | `eth_call` (§4) | contract + view-fn signature |
| "Mint / burn / supply change" | §4 zero-address `token_ledger` | token address |
| "Oracle/price drift between two sources" | §4 drift formula + `to_usd_value`/`eth_call` | the two price sources |

---

## 8. Edge cases (always apply)

| # | Rule | Filter to add |
|---|------|---------------|
| 1 | Exclude reverts | `committed AND error IS NULL` |
| 2 | Zero-value transfers | `value_delta != 0` |
| 3 | Multicall batching — multiple events per tx | Use `(block_number, tx_index, log_index)` PK instead of just `(block_number, tx_index)` if you need 1 row per event |
| 4 | Smart-contract initiators (EIP-1271 / EIP-7598 packed-sig variants) | Include the packed-sig selector variant — don't filter to only `(v,r,s)` selector |
| 5 | Proxy aliases — the emitter is the proxy, not the implementation | Always filter `address` by the proxy address; never the impl |
| 6 | Protocol noise (e.g. Coinbase Commerce mixed into x402) | Maintain a deny-list of `seller`/`counterparty` contracts; or filter `relayer` to a known allowlist |
| 7 | Sequential vs random nonces | EIP-3009 nonce is **random `bytes32`**; ERC-2612 / smart-account nonces are sequential `uint256` |
| 8 | Path-specific events | Path B / aggregator paths may emit no auth event → fall back to `token_ledger` (P4) for initiator |
| 9 | Sequencer drift | Block-window predicates are approximate; if exact wall-clock matters, use `block_timestamp(...)` predicate (§2) |

---

## 9. Anti-patterns (will be slow or wrong)

> Some rows are anti-patterns **only where the underlying index is missing** (see §1.1) — confirm via `get-schema --network <c> --table <t>` before assuming a query is slow.

| Anti-pattern | Why it's bad | Use instead |
|--------------|-------------|-------------|
| `WHERE topic0 = '\x…'` (alone on `logs`) **without a block-range** | where topic0 is indexed the lookup is fine, but with no `block_number`/`duration=` bound it still scans all history for that topic0 (and on Base there's no topic0 index at all). | Keep `WHERE topic0 = …` (all-forks pattern) **plus** a `block_number`/`duration=` bound; add `address = …` to pin one deployment (and as the lead on Base). |
| `SELECT *` from `logs` / `transaction_detail` | `data`/`calldata` are TOAST; bloats network | Project explicit columns |
| `WHERE tx_hash = '\x…'` | `tx_hash` may not be indexed on every table | Use `(block_number, tx_index)` if known |
| Decoding `logs.Transfer.data` for amounts | Slow + complicated when `token_ledger` has it parsed | P4 |
| Treating `td.from_a` as the end user | Wrong in any relayer/meta-tx protocol | P5 (auth event or `token_ledger` initiator) |
| `JOIN` without `block_number` predicate on both sides | Joins explode; PG may pick a bad plan | Push `block_number BETWEEN …` into both subqueries (or a shared CTE) |
| Querying without a block-range filter | Full table scan | Always include `block_number BETWEEN …` |
| Reading the impl contract's logs to attribute to the proxy | Impl never emits; proxies do | Filter `address` by the proxy |
| Trusting `Transfer.to == authorization.to` | True on direct paths; false on aggregator/witness paths | Trust `Transfer.to` from `token_ledger` |
| **Casting/wrapping an indexed column in `WHERE`** (`block_number::text=…`, `lower(addr)=…`, `address::bytea` when already bytea) | A function/cast on the **column side** defeats its btree index → seq scan. | Cast the **literal** instead (`addr = '\x…'::bytea`); compare same types (addresses are already `bytea`). |
| Embedding external API calls (`http_get_json`/`http_post`) for prices in an alert | Couples to a rate-limited external service, bakes a secret into SQL, non-deterministic (demo-grade). | `to_usd_value` / `network_token_info.last_price` for USD, `eth_call` for state. Reserve `http_*` for genuine off-chain data, never secrets. |

---

## 10. Sanity checklist before running a generated query

1. Every `WHERE` column has an index (§1.1) or sits in an indexed range; no cast on the column side (§9).
2. There is a `block_number BETWEEN …` / `duration=` filter, and it's **≤ 30d** (history beyond 30d → materialized TABLE, not a wide scan).
3. `committed AND error IS NULL` present (unless you want reverts).
4. Addresses are lowercase `\x` bytea literals; topics full 32-byte; SELECT output for addresses/hashes is `concat('0x', encode(col,'hex'))`.
5. Value math: `tl.value_delta < 0` selects sender rows (don't double-count).
6. Aggregations time-bucket via `<chain>.block_timestamp(block_number)`, not by joining `<chain>.block`.
7. Cross-chain → `UNION ALL` per chain; never JOIN on `block_number`; row key / `GROUP BY` is **`(address, chain_id)`** (P12).
8. **No trailing `;`** (§3 rule 9).
9. **`tx_hash`** and a literal **`chain_id`** are projected (§4).
10. **Final `SELECT` ends with `LIMIT 200`** (cap 500) — unless single-row aggregate. **Exception:** a P12 principal VIEW carries **NO `LIMIT`** (the reader has it).
11. **Expanded layout (§5 house style), never minified:** `SELECT` alone on its line, **one projected item per line** (4-space indent past the `SELECT` keyword), `FROM`/`JOIN`/`WHERE`/`GROUP BY`/`ORDER BY`/`LIMIT` left-aligned to that `SELECT`, continued `AND`/`OR` indented +2, and a **blank line before each `UNION ALL`**. Never crowd multiple columns onto one shared line.
