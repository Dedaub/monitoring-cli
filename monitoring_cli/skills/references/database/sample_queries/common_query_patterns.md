# Common Queries — Database Query Patterns

**Audience:** an agent translating a business question into SQL against the Watchdog blockchain schema.
**Pairs with:** a protocol knowledge-base doc (e.g. `protocols/uniswap/v2.md`, `protocols/uniswap/v3.md`).
**Status:** abstracted from x402 detection research on 2026-05-21; verified against PG18 schema for Base mainnet.

> **How to use.** The protocol doc supplies *constants* (contract addresses, function selectors, event topic0 hashes, asset addresses, special EOAs). This doc supplies *patterns* (which tables, which indexes, which joins, which filters). Pick the pattern by matching the business question to §7; substitute constants from the protocol doc into the SQL template. Never write a query that ignores §3 (indexes) or §8 (edge cases).

---

## 1. Schema cheat-sheet

Per-chain schema (`base.`, `ethereum.`, `arbitrum.`, `optimism.`, `polygon.`, `binance.`, `avalanche.`, `blast.`). All tables below exist on every chain unless noted.

| Table | PK | Purpose |
|-------|----|---------|
| `<chain>.transaction_detail` | `(block_number, tx_index, vm_step_start)` | One row per executed call frame. `from_a` = caller, `to_a` = callee, `calldata` = input bytes. |
| `<chain>.logs` | `(block_number, tx_index, vm_step)` | One row per emitted `LOG*`. `address` = emitter, `topic0..3`, `data`. |
| `<chain>.token_ledger` | `(address, block_number, tx_index, vm_step_start, vm_step)` | Parsed token balance deltas. One row per side of each transfer; `value_delta` is signed. |
| `<chain>.contract_creation` | `(address)` | One row per deployed contract. `deployer`, `block_number`. |
| `<chain>.block` | `(block_number)` | Block headers; source of truth for tip and timestamps. |

### 1.1 Index inventory (use these as leading predicates)

> **Per-chain caveat:** the table below is the **baseline guaranteed on every chain schema** (verified on Base). Older / higher-volume chains (e.g. `ethereum`, `arbitrum`) may carry **additional** indexes — notably a `topic0` index on `logs`, or a `(topic0, address, block_number)` composite. Before assuming an index is missing, run `\d+ <chain>.logs` (or query `pg_indexes WHERE schemaname = '{{CHAIN}}'`) on the target chain. If an index *does* exist, the corresponding §9 anti-pattern stops being one — the query is fast.

| Table | Indexes (baseline, present on every chain) |
|-------|--------------------------------------------|
| `transaction_detail` | `(block_number)`, `(from_a, block_number)`, `(to_a, block_number)`, `(common.selector(calldata), block_number)`, **`(to_a, common.selector(calldata), block_number)`** ← workhorse |
| `logs` | `(address, block_number DESC)`, `(block_number DESC)` — **no `topic0` index on Base; may exist on other chains** |
| `token_ledger` | `(address)`, `(address, block_number, tx_index, vm_step_start, vm_step)`, `(block_number)`, `(block_number, tx_index, vm_step_start, vm_step)` |
| `contract_creation` | `(address)`, `(block_number, tx_index, vm_step_start)`, `(deployer) INCLUDE (address)` |

### 1.2 Helper functions (PG18+)

| Helper | Returns | Use |
|--------|---------|-----|
| `common.selector(bytea)` | `bytea(4)` | First-4-byte function selector; **indexed** on `transaction_detail`. |
| `common.hex_to_numeric(text)` | `numeric` | Decode `'0x…'` hex (e.g. `logs.data` payloads) to numeric. |
| `<chain>.block_timestamp(int8)` | `timestamptz` | Block number → wall clock. Prefer over joining `<chain>.block` for time bucketing. |

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
| 3 | **For `logs`, address-first, topic0-second** *(unless the target chain has a `topic0` index — see §1.1)*. `WHERE address = … AND topic0 = …` is safe everywhere; `WHERE topic0 = …` alone is safe **only after** confirming an index exists on that chain (`\d+ {{CHAIN}}.logs` or `pg_indexes`). | The baseline schema has no `topic0` index; address is the only guaranteed-fast leading predicate. If a chain *does* index `topic0` (or `(topic0, …)`), bare topic0 filtering is fine. |
| 4 | **Prefer `transaction_detail` as the driving table for function-call detection.** | The `(to_a, selector, block_number)` composite is the cheapest entry point. |
| 5 | **Prefer `token_ledger` over decoding `logs.Transfer.data` for value analytics.** | Already parsed, signed, joined to counterparty; no TOAST hit. |
| 6 | **Don't `SELECT *`.** | `calldata`, `returndata`, `logs.data` are TOAST-stored. Project explicit columns. |
| 7 | **Join `transaction_detail` ↔ `logs` ↔ `token_ledger` on `(block_number, tx_index)`.** | All three have it indexed (directly or as a prefix). Add `vm_step` / `log_index` only when ordering inside a tx matters (multicall). |
| 8 | **`committed = true AND error IS NULL` excludes reverts.** Include both. | A revert still produces a `transaction_detail` row but no state effects. |

---

## 4. Decode primitives (cheat-sheet)

| Need | Snippet |
|------|---------|
| Selector of a call | `common.selector(td.calldata)` |
| Indexed address from `topic1`/`topic2` | `substring(log.topic1 FROM 13 FOR 20)::bytea` (right-most 20 of 32 bytes) |
| `uint256` from `log.data` | `common.hex_to_numeric('0x' || encode(log.data, 'hex'))` |
| Token amount → human units | divide by `pow(10, decimals)` (USDC = 6, WETH = 18, etc.) |
| Time-bucket | `date_trunc('hour', <chain>.block_timestamp(block_number))` |

---

## 5. Query patterns

Each pattern is a template. Placeholders use `{{UPPER_CASE}}`. The protocol doc tells you what to plug in.

### P1 — Function-call discovery (`to_a + selector`)

> Use when: business question is *"how often / by whom / against which contracts is function X being called?"*

Inputs from protocol doc: callee contract address(es), one-or-more 4-byte selectors.

```sql
SELECT
    td.block_number,
    td.tx_index,
    td.from_a,                                   -- caller (often a relayer, NOT the end user)
    td.to_a,                                     -- the contract
    common.selector(td.calldata) AS selector,
    td.gas_used,
    td.error
FROM {{CHAIN}}.transaction_detail td
WHERE td.to_a = ANY (ARRAY[
        '{{CONTRACT_1}}'::bytea
        -- , '{{CONTRACT_2}}'::bytea
      ])
  AND common.selector(td.calldata) = ANY (ARRAY[
        '{{SELECTOR_1}}'::bytea
        -- , '{{SELECTOR_2}}'::bytea
      ])
  AND td.committed AND td.error IS NULL
  AND td.block_number BETWEEN
        (SELECT MAX(block_number) FROM {{CHAIN}}.block) - {{N_BLOCKS}}
        AND (SELECT MAX(block_number) FROM {{CHAIN}}.block)
ORDER BY td.block_number DESC, td.tx_index DESC;
```

Hits the `(to_a, selector, block_number)` composite index directly.

### P2 — Event discovery (`address + topic0`)

> Use when: business question is *"how often is event E being emitted, and what data does it carry?"*

Inputs: emitter contract address, topic0 hash; optionally an indexed `topic1`/`topic2` value.

```sql
SELECT
    l.block_number,
    l.tx_index,
    l.address,
    substring(l.topic1 FROM 13 FOR 20)::bytea AS indexed_arg_1,   -- if address-typed
    l.topic2,
    common.hex_to_numeric('0x' || encode(l.data, 'hex')) AS data_uint256
FROM {{CHAIN}}.logs l
WHERE l.address = '{{EMITTER}}'::bytea
  AND l.topic0  = '{{TOPIC0}}'::bytea
  AND l.block_number BETWEEN
        (SELECT MAX(block_number) FROM {{CHAIN}}.block) - {{N_BLOCKS}}
        AND (SELECT MAX(block_number) FROM {{CHAIN}}.block);
```

### P3 — Tx ↔ logs correlation

> Use when: you need calldata-side metadata (caller, gas) AND a specific event side-effect in the same tx.

```sql
WITH calls AS (
    -- P1 template
    SELECT td.block_number, td.tx_index, td.from_a, td.to_a
    FROM {{CHAIN}}.transaction_detail td
    WHERE td.to_a = '{{CONTRACT}}'::bytea
      AND common.selector(td.calldata) = '{{SELECTOR}}'::bytea
      AND td.committed AND td.error IS NULL
      AND td.block_number BETWEEN
            (SELECT MAX(block_number) FROM {{CHAIN}}.block) - {{N_BLOCKS}}
            AND (SELECT MAX(block_number) FROM {{CHAIN}}.block)
)
SELECT c.*,
       substring(l.topic1 FROM 13 FOR 20)::bytea AS event_indexed_addr,
       l.topic2,
       l.data
FROM calls c
JOIN {{CHAIN}}.logs l
  ON l.block_number = c.block_number
 AND l.tx_index     = c.tx_index
 AND l.address      = '{{EMITTER}}'::bytea
 AND l.topic0       = '{{TOPIC0}}'::bytea;
```

The CTE narrows the join; address-leading predicate on `logs` keeps it index-resident.

### P4 — Value movement via `token_ledger`

> Use when: business question involves *amounts of a specific token moving between specific actors*.

Inputs: token address; optionally a tx filter from P1.

```sql
WITH txs AS (   -- a tx filter (P1 or P3); strip if you want ALL transfers of the token
    SELECT td.block_number, td.tx_index
    FROM {{CHAIN}}.transaction_detail td
    WHERE td.to_a = '{{CONTRACT}}'::bytea
      AND common.selector(td.calldata) = ANY (ARRAY['{{SELECTOR}}'::bytea])
      AND td.committed AND td.error IS NULL
      AND td.block_number BETWEEN
            (SELECT MAX(block_number) FROM {{CHAIN}}.block) - {{N_BLOCKS}}
            AND (SELECT MAX(block_number) FROM {{CHAIN}}.block)
)
SELECT
    tl.block_number,
    tl.tx_index,
    tl.address              AS sender,            -- the row with value_delta < 0
    tl.counterparty_address AS recipient,
    -tl.value_delta / pow(10, {{DECIMALS}}) AS amount_human
FROM txs
JOIN {{CHAIN}}.token_ledger tl
  ON tl.block_number = txs.block_number
 AND tl.tx_index     = txs.tx_index
 AND tl.token_address = '{{TOKEN}}'::bytea
 AND tl.value_delta < 0                          -- one row per Transfer (debit side)
 AND tl.value_delta != 0;                        -- defensive
```

`token_ledger` records both sides of each transfer; filtering `value_delta < 0` picks the sender row and `counterparty_address` gives you the recipient — no log decoding needed.

### P5 — Authorizer attribution (caller ≠ initiator)

> Use when: the protocol uses meta-transactions, gasless approvals, or any relayer pattern — i.e. `tx.from` is **not** the real user. Examples: EIP-3009 (`transferWithAuthorization`), EIP-2612 (`permit`), Permit2, ERC-4337 user ops, Gelato relays.

The pattern: identify the real initiator from either (a) a side-channel event whose indexed arg is the signer, or (b) the `value_delta < 0` row in `token_ledger`.

```sql
WITH txs AS (
    SELECT td.block_number, td.tx_index, td.from_a AS relayer
    FROM {{CHAIN}}.transaction_detail td
    WHERE td.to_a = '{{CONTRACT}}'::bytea
      AND common.selector(td.calldata) = ANY (ARRAY['{{META_TX_SELECTOR}}'::bytea])
      AND td.committed AND td.error IS NULL
      AND td.block_number BETWEEN
            (SELECT MAX(block_number) FROM {{CHAIN}}.block) - {{N_BLOCKS}}
            AND (SELECT MAX(block_number) FROM {{CHAIN}}.block)
)
SELECT
    t.block_number, t.tx_index, t.relayer,
    substring(au.topic1 FROM 13 FOR 20)::bytea AS initiator,    -- topic1 of the auth event
    au.topic2                                  AS auth_nonce    -- correlates to off-chain payload
FROM txs t
JOIN {{CHAIN}}.logs au
  ON au.block_number = t.block_number
 AND au.tx_index     = t.tx_index
 AND au.address      = '{{CONTRACT}}'::bytea
 AND au.topic0       = '{{AUTH_TOPIC0}}'::bytea;
```

Substitute `au.topic1` → `value_delta < 0` row from `token_ledger` if no auth event exists (e.g. Permit2 path).

### P6 — Time-bucketed aggregation

> Use when: dashboards, time-series, growth metrics.

```sql
WITH events AS (
    -- emit one row per "thing" you're measuring (use P1/P3/P4 as appropriate)
    SELECT
        date_trunc('{{BUCKET}}', {{CHAIN}}.block_timestamp(td.block_number)) AS bucket,
        tl.address              AS initiator,
        tl.counterparty_address AS counterparty,
        -tl.value_delta / pow(10, {{DECIMALS}}) AS amount_usd
    FROM {{CHAIN}}.transaction_detail td
    JOIN {{CHAIN}}.token_ledger tl
      ON tl.block_number = td.block_number
     AND tl.tx_index     = td.tx_index
     AND tl.token_address = '{{TOKEN}}'::bytea
     AND tl.value_delta < 0
    WHERE td.to_a = '{{CONTRACT}}'::bytea
      AND common.selector(td.calldata) = ANY (ARRAY['{{SELECTOR}}'::bytea])
      AND td.committed AND td.error IS NULL
      AND td.block_number BETWEEN
            (SELECT MAX(block_number) FROM {{CHAIN}}.block) - {{N_BLOCKS}}
            AND (SELECT MAX(block_number) FROM {{CHAIN}}.block)
)
SELECT
    bucket,
    COUNT(*)                                    AS tx_count,
    COUNT(DISTINCT initiator)                   AS unique_initiators,
    COUNT(DISTINCT counterparty)                AS unique_counterparties,
    ROUND(SUM(amount_usd), 2)                   AS volume,
    ROUND(AVG(amount_usd), 4)                   AS avg_size,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount_usd) AS median_size
FROM events
GROUP BY bucket
ORDER BY bucket DESC;
```

`{{BUCKET}}` = `'minute'` | `'hour'` | `'day'` | `'week'`. Widen `{{N_BLOCKS}}` proportionally — see §2.

### P7 — Top-N actors

> Use when: leaderboards (top spenders, top receivers, top contracts).

```sql
SELECT
    tl.{{ACTOR_COLUMN}} AS actor,              -- tl.address (sender) | tl.counterparty_address (recipient)
    SUM(-tl.value_delta) / pow(10, {{DECIMALS}}) AS total_amount,
    COUNT(*)                  AS event_count,
    COUNT(DISTINCT tl.{{OPPOSITE_COLUMN}}) AS unique_counterparties
FROM {{CHAIN}}.transaction_detail td
JOIN {{CHAIN}}.token_ledger tl
  ON tl.block_number = td.block_number
 AND tl.tx_index     = td.tx_index
 AND tl.token_address = '{{TOKEN}}'::bytea
 AND tl.value_delta < 0
WHERE td.to_a = '{{CONTRACT}}'::bytea
  AND common.selector(td.calldata) = ANY (ARRAY['{{SELECTOR}}'::bytea])
  AND td.committed AND td.error IS NULL
  AND td.block_number BETWEEN
        (SELECT MAX(block_number) FROM {{CHAIN}}.block) - {{N_BLOCKS}}
        AND (SELECT MAX(block_number) FROM {{CHAIN}}.block)
GROUP BY tl.{{ACTOR_COLUMN}}
ORDER BY total_amount DESC
LIMIT {{N}};
```

For "top relayers/facilitators/operators", `GROUP BY td.from_a` instead (the caller is the relayer in meta-tx protocols).

### P8 — Bipartite graph (sender → receiver)

> Use when: network/graph analysis, churn, repeat-business rates.

```sql
SELECT
    tl.address              AS sender,
    tl.counterparty_address AS receiver,
    SUM(-tl.value_delta) / pow(10, {{DECIMALS}}) AS edge_weight_amount,
    COUNT(*)                AS edge_weight_count,
    MIN({{CHAIN}}.block_timestamp(tl.block_number)) AS first_interaction,
    MAX({{CHAIN}}.block_timestamp(tl.block_number)) AS last_interaction
FROM {{CHAIN}}.transaction_detail td
JOIN {{CHAIN}}.token_ledger tl
  ON tl.block_number = td.block_number
 AND tl.tx_index     = td.tx_index
 AND tl.token_address = '{{TOKEN}}'::bytea
 AND tl.value_delta < 0
WHERE td.to_a = '{{CONTRACT}}'::bytea
  AND common.selector(td.calldata) = ANY (ARRAY['{{SELECTOR}}'::bytea])
  AND td.committed AND td.error IS NULL
  AND td.block_number BETWEEN
        (SELECT MAX(block_number) FROM {{CHAIN}}.block) - {{N_BLOCKS}}
        AND (SELECT MAX(block_number) FROM {{CHAIN}}.block)
GROUP BY sender, receiver;
```

### P9 — Multi-path / multi-contract detection

> Use when: the protocol has more than one on-chain entrypoint (e.g. x402 has Path A direct EIP-3009 + Path B Permit2 proxies; Uniswap has SwapRouter v1 + SwapRouter02 + Universal Router).

Treat each path independently (different `to_a` + `selector` set), `UNION ALL` the per-path queries, label rows with a `path` column. Aggregate downstream.

```sql
SELECT 'path_a' AS path, td.block_number, td.tx_index, td.from_a
FROM {{CHAIN}}.transaction_detail td
WHERE td.to_a = '{{CONTRACT_A}}'::bytea
  AND common.selector(td.calldata) = ANY (ARRAY['{{SEL_A1}}'::bytea, '{{SEL_A2}}'::bytea])
  AND td.committed AND td.error IS NULL
  AND td.block_number BETWEEN
        (SELECT MAX(block_number) FROM {{CHAIN}}.block) - {{N_BLOCKS}}
        AND (SELECT MAX(block_number) FROM {{CHAIN}}.block)

UNION ALL

SELECT 'path_b' AS path, td.block_number, td.tx_index, td.from_a
FROM {{CHAIN}}.transaction_detail td
WHERE td.to_a = ANY (ARRAY['{{CONTRACT_B1}}'::bytea, '{{CONTRACT_B2}}'::bytea])
  AND common.selector(td.calldata) = ANY (ARRAY['{{SEL_B1}}'::bytea])
  AND td.committed AND td.error IS NULL
  AND td.block_number BETWEEN
        (SELECT MAX(block_number) FROM {{CHAIN}}.block) - {{N_BLOCKS}}
        AND (SELECT MAX(block_number) FROM {{CHAIN}}.block);
```

### P10 — Cross-chain unification

> Use when: business question is *"on which chains is protocol X live?"* or *"what's the aggregate across all chains?"*

Same patterns, different schemas. The protocol doc must give you the per-chain address/selector triplet — typically selectors are chain-agnostic (a contract's ABI is the same wherever it's deployed), but addresses differ unless deployed via the deterministic `0x4e59b…` deployer.

```sql
SELECT 'ethereum' AS chain, /* P1 against ethereum.* */
UNION ALL
SELECT 'base'     AS chain, /* P1 against base.* */
UNION ALL
SELECT 'arbitrum' AS chain, /* P1 against arbitrum.* */
-- …
```

Wrap downstream aggregation outside the UNION. Note: `block_number` is **not** comparable across chains — convert to `block_timestamp(block_number)` first for any time-aligned join.

### P11 — Contract discovery

> Use when: business question is *"who deployed X?"* or *"find all contracts deployed by address Y."*

```sql
SELECT cc.address, cc.block_number, {{CHAIN}}.block_timestamp(cc.block_number) AS deployed_at
FROM {{CHAIN}}.contract_creation cc
WHERE cc.deployer = '{{DEPLOYER}}'::bytea;
```

`(deployer) INCLUDE (address)` makes this an index-only scan.

---

## 6. What to extract from a protocol doc

To plug into the patterns above, the agent should pull the following from the paired knowledge-base doc:

| Variable | Source in knowledge-base doc | Plug into |
|----------|------------------------------|-----------|
| `{{CHAIN}}` | The "Scope" or "Addresses" section | All patterns |
| `{{CONTRACT}}` (callee) | "Addresses" table — pick the entrypoint(s) the user is asking about | P1, P3, P4, P5, P6, P7, P9 |
| `{{SELECTOR}}` (4 bytes, `'\x........'`) | "Function selectors" / "Function signatures" table | P1, P3, P4, P5, P6, P7 |
| `{{EMITTER}}` (event source) | Usually same as the callee, occasionally a downstream proxy | P2, P3, P5 |
| `{{TOPIC0}}` (32 bytes) | "Event signatures & topic0 hashes" table | P2, P3, P5 |
| `{{TOKEN}}` + `{{DECIMALS}}` | "Addresses" — asset row (USDC=6, WETH=18, USDT=6, WBTC=8, etc.) | P4, P6, P7, P8 |
| `{{AUTH_TOPIC0}}` (signer-revealing event) | Look for an event whose `topic1` is the off-chain signer (e.g. `AuthorizationUsed`, `OrderFilled`, `UserOperationEvent`) | P5 |
| Multi-path contract set | "Protocol architecture" section — Path A / Path B / Universal Router / etc. | P9 |
| Deny-list contracts / noise | "Edge cases" / "Open questions" section — e.g. Coinbase Commerce, MEV bots | §8 noise filter |

If the protocol doc does not provide a value, **stop and ask** — never guess a selector or topic0; both are 1-in-2^32 / 2^256 collision spaces but the wrong constant returns silent zero rows.

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
| "Who deployed contract X?" | P11 | deployer address |
| "When was contract X first active?" | P11 + P1 with `ORDER BY block_number ASC LIMIT 1` | callee |
| "Match an off-chain event ID to an on-chain settlement" | P5 (use `auth_nonce` from `topic2`) | callee, auth-event topic0 |
| "Detect new contracts being deployed by relayers" | P12 with `WHERE deployer = ANY(known_relayers)` | known relayer EOAs |

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
| 9 | Sequencer drift | Block-window predicates are approximate; if exact wall-clock matters, use `block_timestamp(...)` predicate (see §2) |

---

## 9. Anti-patterns (will be slow or wrong)

> **Network-dependent caveat:** some rows below are anti-patterns **only on chains where the underlying index is missing**. The baseline (verified on Base) is the assumption — but on chains where the relevant index exists (see §1.1), the pattern is fine. Confirm via `\d+ {{CHAIN}}.<table>` before assuming a query will be slow. Rows tagged *"chain-dependent"* below have known per-chain variance.

| Anti-pattern | Why it's bad | Use instead |
|--------------|-------------|-------------|
| `WHERE topic0 = '\x…'` (alone on `logs`) *(chain-dependent)* | On Base and other baseline schemas, no `topic0` index → full table scan. On chains that **do** index `topic0` (verify in §1.1 or via `pg_indexes`), this is fine. | Default to adding `address = '\x…'` as leading predicate; skip the address constraint only after confirming a `topic0`-leading index exists on the target chain. |
| `SELECT *` from `logs` / `transaction_detail` | `data`/`calldata` are TOAST; bloats network | Project explicit columns |
| `WHERE tx_hash = '\x…'` | `tx_hash` may not be indexed on every table | Use `(block_number, tx_index)` if known |
| Decoding `logs.Transfer.data` for amounts | Slow + complicated when `token_ledger` has it parsed | P4 |
| Treating `td.from_a` as the end user | Wrong in any relayer/meta-tx protocol | P5 (use auth event or `token_ledger` initiator) |
| `JOIN` without `block_number` predicate on both sides | Joins explode; PG may pick a bad plan | Push `block_number BETWEEN …` into both subqueries (or apply once in a CTE used on both sides) |
| Querying without a block-range filter | Full table scan | Always include `block_number BETWEEN …` |
| Reading the impl contract's logs to attribute to the proxy | Impl never emits; proxies do | Filter `address` by the proxy |
| Trusting `Transfer.to == authorization.to` | True on direct paths; false on aggregator/witness paths | Trust `Transfer.to` from `token_ledger` |

---

## 10. Sanity checklist before running a generated query

1. Every `WHERE` column either has an index (§1.1) or sits inside an indexed range.
2. There is a `block_number BETWEEN …` filter.
3. `committed AND error IS NULL` is present (unless you specifically want reverts).
4. Addresses are lowercase `bytea` literals; topic hashes are full 32-byte literals.
5. For value math: `tl.value_delta < 0` selects sender rows; otherwise you'll double-count.
6. For aggregations: time-bucket via `<chain>.block_timestamp(block_number)`, not by joining `<chain>.block`.
7. Cross-chain queries `UNION ALL` per chain — they never JOIN on `block_number` directly.

---

## Appendix A — Quick recipe lookup

| If the user asks… | Run pattern |
|-------------------|-------------|
| "find tx" / "find call" / "find function" | P1 |
| "find event" / "find log" / "emits" | P2 |
| "who paid / sent / signed" | P5 |
| "amount" / "volume" / "USD" | P4 |
| "by hour/day/week" / "growth" / "trend" | P6 |
| "top" / "leaderboard" / "ranking" | P7 |
| "network" / "graph" / "edges" | P8 |
| "multiple paths" / "all variants" | P9 |
| "across chains" | P10 |
| "deployer" / "first deployed" | P11 |
