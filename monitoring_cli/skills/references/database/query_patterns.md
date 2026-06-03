# §5 — Query patterns (P1–P16)

Sibling of `sample_queries/common_query_patterns.md` (the hub). `§N` references point to the hub; decode
snippets are in `decode_primitives.md`. Each pattern is a template — placeholders use `{{UPPER_CASE}}`;
the protocol doc supplies the constants. Pick via the hub's §7 map or the quick-pick below.

**Quick-pick** — "find tx/call/function"→P1 · "find event/log/emits"→P2 · "who paid/sent/signed"→P5 ·
"amount/volume/USD"→P4 · "by hour/day/week, trend"→P6 · "top/leaderboard"→P7 · "network/graph/edges"→P8 ·
"multiple paths/variants"→P9 · "across chains"→P10 · "total/sum/aggregate (esp. cross-chain)"→P12 ·
"deployer/first deployed"→P11 · "hasn't happened in N"→P13 · "drained >$N in one tx"→P14 ·
"reentrancy/nested call"→P15 · "sudden drop/spike vs norm"→P16.

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
FROM {{CHAIN}}.contracts cc
WHERE cc.deployer = '{{DEPLOYER}}'::bytea;
```

The `(deployer)` index keeps this cheap. For a deployer/relayer **allowlist** (the §7 "new contracts by
relayers" row), swap the equality for `WHERE cc.deployer = ANY(ARRAY['\x…'::bytea, '\x…'::bytea])`.

### P12 — Split analytical query (row-level VIEW + aggregating reader)

> Use when: the business question is an **aggregate** (sum / total / volume / leaderboard) over a large
> row set — especially **cross-chain**. Don't compute the row scan and the aggregate in one query;
> **split them into two**.

The split:

1. **Principal VIEW (the row scan)** — one query that emits the **full per-row result, `--materialize VIEW`,
   and carries NO `LIMIT`** (the §3-rule-10 / §10-rule-11 `LIMIT 200` default is **waived here** — the
   reader must see every row to sum correctly; a `LIMIT` would silently truncate the total). This is the
   query whose id you reference (e.g. `123142`). It still obeys every other rule: indexed lead,
   `block_number`/`duration=` bound, `committed AND error IS NULL`, explicit columns, no trailing `;`.
2. **Aggregating reader (the sum)** — a **separate** query that does `FROM {{ref(query_id=123142)}}` and applies the
   `SUM`/`GROUP BY`/`ORDER BY … LIMIT`. The reader is where the `LIMIT 200` final-output default lives.

```sql
-- Principal VIEW (id 123142): full rows, NO limit, materialize VIEW.
-- One UNION ALL branch per chain; each carries its own literal chain_id + chain_name (cross-chain PK rule below).
SELECT 8453  AS chain_id, 'base'     AS chain_name, tl.token_address, -tl.value_delta AS amount_raw, lti.decimals, lti.symbol
FROM {{token_ledger(network='base', duration='24h')}} tl
JOIN base.latest_token_info lti ON lti.token_address = tl.token_address
WHERE tl.value_delta < 0 AND tl.value_delta != 0
UNION ALL
SELECT 42161 AS chain_id, 'arbitrum' AS chain_name, tl.token_address, -tl.value_delta AS amount_raw, lti.decimals, lti.symbol
FROM {{token_ledger(network='arbitrum', duration='3h')}} tl
JOIN arbitrum.latest_token_info lti ON lti.token_address = tl.token_address
WHERE tl.value_delta < 0 AND tl.value_delta != 0
-- no LIMIT
```

```sql
-- Aggregating reader (separate query): sums every row of the VIEW. PK = (token_address, chain_id).
-- Project BOTH chain_id (canonical, UI-rendered) and chain_name (human-readable) in the output.
SELECT
    r.chain_id,
    r.chain_name,
    concat('0x', encode(r.token_address, 'hex')) AS token_address,
    r.symbol,
    SUM(r.amount_raw / pow(10, r.decimals)) AS total_amount
FROM {{ref(query_id=123142)}} r
GROUP BY r.chain_id, r.chain_name, r.token_address, r.symbol
ORDER BY total_amount DESC
LIMIT 200
```

**Why split instead of one query:** the row scan is reusable and independently testable (one VIEW feeds
many readers — totals, top-N, time-buckets), and the reader stays cheap and re-runnable without
re-scanning. It also keeps the unbounded row set out of any single result payload — only the aggregate
is returned.

**Cross-chain primary key — `address + chain_id`.** The same 20-byte address recurs per chain and can even
be a **different** token on each. So the reader's `GROUP BY` key (and the unique key of any alert built on
it) is **`(address, chain_id)`**, never `address` alone — every branch projects its own literal `chain_id`.
Collapsing on bare `address` over-sums across chains and mislabels rows.

**Carry `chain_name` next to `chain_id`** in every VIEW branch (`8453 AS chain_id, 'base' AS chain_name`)
and project both (group by both — they're 1:1) so the human-readable name rides along with each summed row.
Mapping: `1` ethereum, `8453` base, `42161` arbitrum, `10` optimism, `137` polygon, `56` bnb,
`43114` avalanche, `81457` blast.

### P13 — Absence / staleness ("X hasn't happened in N")

> Use when: alert on the **non-occurrence** of an expected call/event — oracle didn't update, keeper/harvest/heartbeat didn't run. The inverse of P1/P2: you fire when nothing matched.

Anti-join a watched-address list against what was seen in the window (`NOT EXISTS` / `LEFT JOIN … IS NULL` are index-friendly):

```sql
WITH watched(address) AS (VALUES ('\x…'::bytea), ('\x…'::bytea))
SELECT address, DATE(now()) AS date_error
FROM watched
WHERE NOT EXISTS (
    SELECT 1
    FROM {{transaction_detail(network='ethereum', duration='24 hour')}} td   -- duration= works on transaction_detail too
    WHERE td.to_a = watched.address
      AND common.selector(td.calldata) = '\x<selector>'::bytea
      AND td.committed
)
```

The platform's flagship oracle-staleness alert uses the equivalent `… EXCEPT SELECT to_a FROM {{transaction_detail('transmit(…)', duration='24 hour')}}`. Unique key `(address, date_error)` → at most one alert per address per day. Bound the window to the staleness SLA (24h here), not the per-chain default.

### P14 — Protocol drain (net USD moved in one tx)

> Use when: "protocol X lost > $N in a single tx" (hack/drain). Attribute by `protocol_contract` instead of hardcoding addresses.

```sql
SELECT tx_hash(t.block_number, t.tx_index) AS tx_hash, p.protocol_name,
       SUM(<chain>.to_usd_value(t.value_delta, t.token_address)) AS net_usd
FROM {{token_ledger(network='<chain>', duration='…')}} t
JOIN <chain>.protocol_contract pc USING (address)
JOIN <chain>.protocol          p  USING (protocol_id)
GROUP BY t.block_number, t.tx_index, p.protocol_id, p.protocol_name
HAVING SUM(<chain>.to_usd_value(t.value_delta, t.token_address)) > 1000000   -- net move > $1M
```

`value_delta` is **signed**, so summing per `(tx, protocol)` **nets** inflows against outflows — a balanced swap → ~0, a real drain → a large one-sided total. `to_usd_value` works on any numeric (incl. signed `value_delta`), not just balances. **Confirm the sign direction empirically** (the flagship "Drained in a single tx" thresholds the sum `> 1e7`); flip the comparison if your chain/protocol records the drained side negative.

### P15 — Reentrancy / nested-call detection (`is_ancestor`)

> Use when: a call re-enters the same contract inside its own call tree (reentrancy), or "call B executed inside call A's frame".

```sql
SELECT tx_hash(outer_call.block_number, outer_call.tx_index)
FROM {{transaction_detail(network='ethereum', duration='…')}} AS outer_call
JOIN {{transaction_detail(network='ethereum', duration='…', inputs='0x<addr>.execute(bytes,bytes[])')}} AS inner_call
  ON {{is_ancestor("outer_call", "inner_call")}}
WHERE outer_call.to_a = inner_call.to_a       -- same callee reached again in a nested frame = reentrancy
```

`is_ancestor(a,b)` = frame `a` is an ancestor of `b` in the same tx (`is_parent` = direct parent). Related: split **top-level vs nested** callers (direct users vs router/bundler/arbitrage bots) with the call-depth `coalesce(array_length(td.caller_vm_step_stack,1),0)` — `0` is EOA-initiated top-level, `>0` is nested.

### P16 — Anomaly vs baseline (sudden drop / spike via window functions)

> Use when: "asset/TVL/volume/withdrawals dropped or spiked vs its recent norm" (sudden-asset-drop, withdrawal-spike, underperformance, transfer-volume spike).

```sql
WITH series AS (        -- one row per time bucket (P6): hourly assets / withdrawals / counts
    SELECT date_trunc('hour', <chain>.block_timestamp(block_number)) AS bucket, SUM(…) AS v
    FROM … GROUP BY bucket
)
SELECT bucket, v,
       round(100.0 * (LAG(v) OVER (ORDER BY bucket) - v)
             / NULLIF(LAG(v) OVER (ORDER BY bucket), 0), 2) AS pct_drop
FROM series
-- spike vs rolling baseline:
--   WHERE v > 3 * AVG(v) OVER (ORDER BY bucket ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING)
```

`LAG` = period-over-period % change (drop/recovery); `AVG(…) OVER (… ROWS BETWEEN n PRECEDING AND 1 PRECEDING)` = rolling baseline for a `>k×` spike or `<−x%` drop threshold. **Always `NULLIF(denominator, 0)`.** These are standard PG window functions — no macro needed; bucket with P6 first, threshold in the outer query.
