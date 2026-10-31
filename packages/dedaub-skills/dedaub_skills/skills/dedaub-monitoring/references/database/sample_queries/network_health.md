# Network health — a validated 9-chain sample set (P18)

Sibling of `common_query_patterns.md` (the hub). Pattern: `../query_patterns.md` P18. Edge cases: hub §8.13–§8.19.

These queries were written, gated and run on the live engine (October 2026). They cover Ethereum, Base,
Arbitrum, Optimism, Polygon, BNB, Avalanche, Robinhood and Arc. Use them as a start for a chain-health
dashboard, or copy one branch for a single chain. Warm run times: snapshot ~3 s, 24h series ~6 s,
activity and tx-type mix ~5 s each.

## Folder layout

Each query has its own folder. The `ref()` readers sit in the folder of the query that they read.

| Folder | Query | Grain | Run settings |
|--------|-------|-------|--------------|
| `/<Root>/NetworkSnapshot-AllChains` | `Query` | one row per chain, last 1h | none (query mode, `LIMIT 200`) |
| `/<Root>/NetworkSeries-AllChains` | `Query` | one row per chain and hour, 24h | **VIEW** (`set-config --network ethereum --materialize VIEW`), so that `ref()` finds it |
| `/<Root>/NetworkSeries-AllChains` | `L1`, `L2` | the series, one layer only | none |
| `/<Root>/NetworkSeries-AllChains` | `Totals` | one row per hour, all chains | none |
| `/<Root>/TxActivity-AllChains` | `Query` | one row per chain, last 1h | **VIEW** |
| `/<Root>/TxActivity-AllChains` | `Totals` | one row, all chains | none |
| `/<Root>/TxTypes-AllChains` | `Query` | one row per chain and tx kind, last 1h | none |
| `/<Root>/BlockBuilders-Ethereum` | `Query` | one row per builder (top 7 + Other), 24h | none |

A VIEW carries no `ORDER BY` and no `LIMIT` (hub §3 rule 10).

## Why the chain list is a Jinja list of tuples

Each query starts with `{% set nets = [ (schema, label, chain_id, …), … ] %}` and loops over it with
`{{ block(duration=…, network=schema) }}` or `{{ outer_transaction(duration=…, network=schema) }}`. A
`networks()` loop refuses `.get_chain_id()`, so the tuple carries the literal `chain_id`. The schema of
BNB is `binance`. The tuple also carries the gas-token price source (hub §8.16–§8.17) and, in the tx
queries, the system-tx predicate of the chain (hub §8.13).

## Snapshot — block headers, last 1h

KPI table and per-chain bar charts. `head_age_s` shows how far the indexed data is behind the chain tip.

```sql
-- Network health snapshot from block headers: block rate, TPS, gas/s, gas use, base fee (gwei + USD), head age · 9 chains · last 1h
{#- schema, label, chain_id, gas token, price schema, wrapped-native price token (none = pin to $1) -#}
{% set nets = [
  ('ethereum',  'Ethereum',  1,     'ETH',  'ethereum',  '\\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),
  ('base',      'Base',      8453,  'ETH',  'ethereum',  '\\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),
  ('arbitrum',  'Arbitrum',  42161, 'ETH',  'ethereum',  '\\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),
  ('optimism',  'Optimism',  10,    'ETH',  'ethereum',  '\\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),
  ('polygon',   'Polygon',   137,   'POL',  'polygon',   '\\x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270'),
  ('binance',   'BNB',       56,    'BNB',  'binance',   '\\xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c'),
  ('avalanche', 'Avalanche', 43114, 'AVAX', 'avalanche', '\\xb31f66aa3c1e785363f0875a1b74e27b85fd66c7'),
  ('robinhood', 'Robinhood', 4663,  'ETH',  'ethereum',  '\\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),
  ('arc',       'Arc',       5042,  'USDC', none,        none)
] %}
WITH per_chain AS (
  {% for schema, label, chain_id, gas_token, price_schema, price_token in nets %}
  SELECT
      '{{ label }}' AS network,
      {{ chain_id }} AS chain_id,
      '{{ gas_token }}' AS gas_token,
      {% if price_token %}
      (SELECT nti.last_price FROM {{ price_schema }}.network_token_info nti WHERE nti.token_address = '{{ price_token }}'::bytea) AS gas_token_usd,
      {% else %}
      1.0::double precision AS gas_token_usd,
      {% endif %}
      count(*) AS blocks,
      max(b.block_number) AS head_block,
      max(b.ts) AS head_ts,
      extract(epoch FROM max(b.ts) - min(b.ts)) AS span_s,
      sum(cardinality(b.transactions)) AS txs,
      sum(b.gas_used) AS gas_used,
      sum(b.gas_limit) AS gas_limit,
      avg(b.base_fee_per_gas) AS avg_base_fee_wei,
      max(b.base_fee_per_gas) AS max_base_fee_wei,
      sum(b.base_fee_per_gas * b.gas_used) AS base_fee_paid_wei
  FROM {{ block(duration='1h', network=schema) }} b
  {% if not loop.last %}

  UNION ALL
  {% endif %}
  {% endfor %}
)
SELECT
    network,
    -- Polygon PoS is grouped with the L1s (sidechain with its own consensus)
    CASE WHEN network IN ('Base', 'Arbitrum', 'Optimism', 'Robinhood') THEN 'L2' ELSE 'L1' END AS layer,
    chain_id,
    gas_token,
    head_block,
    round(extract(epoch FROM now() - head_ts)::numeric, 0) AS head_age_s,
    blocks,
    round((span_s / nullif(blocks - 1, 0))::numeric, 3) AS block_time_s,
    round(((blocks - 1) / nullif(span_s, 0))::numeric, 3) AS blocks_per_sec,
    txs,
    round((txs * (blocks - 1) / blocks / nullif(span_s, 0))::numeric, 2) AS tps,
    round((gas_used * (blocks - 1) / blocks / nullif(span_s, 0) / 1e6)::numeric, 2) AS mgas_per_sec,
    -- Arbitrum-style chains set a placeholder block gas limit (~1.1e15): utilization is not meaningful there
    CASE
      WHEN gas_limit / blocks < 1e12 THEN round((100 * gas_used / nullif(gas_limit, 0))::numeric, 2)
    END AS gas_used_pct,
    round((avg_base_fee_wei / 1e9)::numeric, 9) AS avg_base_fee_gwei,
    round((max_base_fee_wei / 1e9)::numeric, 9) AS max_base_fee_gwei,
    round(gas_token_usd::numeric, 4) AS gas_token_usd,
    -- base-fee cost of a plain 21,000-gas transfer (no priority fee, no L1 data fee)
    round((avg_base_fee_wei * 21000 / 1e18 * gas_token_usd::numeric)::numeric, 8) AS transfer_base_fee_usd,
    round((base_fee_paid_wei / 1e18 * gas_token_usd::numeric)::numeric, 2) AS base_fee_paid_usd_1h
FROM per_chain
ORDER BY tps DESC
LIMIT 200
```

## Hourly series — block headers, 24h (VIEW)

The source of the L1, L2 and Totals readers. `hour` is the first column, so a widget `timeframe` filters on it. The `layer` column splits the chains into 5 L1s and 4 L2s, because a chart draws at most 8 series (see the recipe).

```sql
-- Hourly network health (VIEW, read by L1 / L2 / Totals via ref) from block headers: block rate, TPS, gas/s, gas use, base fee · 9 chains · last 24h
{#- schema, label, chain_id, gas token, price schema, wrapped-native price token (none = pin to $1) -#}
{% set nets = [
  ('ethereum',  'Ethereum',  1,     'ETH',  'ethereum',  '\\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),
  ('base',      'Base',      8453,  'ETH',  'ethereum',  '\\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),
  ('arbitrum',  'Arbitrum',  42161, 'ETH',  'ethereum',  '\\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),
  ('optimism',  'Optimism',  10,    'ETH',  'ethereum',  '\\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),
  ('polygon',   'Polygon',   137,   'POL',  'polygon',   '\\x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270'),
  ('binance',   'BNB',       56,    'BNB',  'binance',   '\\xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c'),
  ('avalanche', 'Avalanche', 43114, 'AVAX', 'avalanche', '\\xb31f66aa3c1e785363f0875a1b74e27b85fd66c7'),
  ('robinhood', 'Robinhood', 4663,  'ETH',  'ethereum',  '\\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),
  ('arc',       'Arc',       5042,  'USDC', none,        none)
] %}
WITH per_hour AS (
  {% for schema, label, chain_id, gas_token, price_schema, price_token in nets %}
  SELECT
      date_trunc('hour', b.ts) AS hour,
      '{{ label }}' AS network,
      {{ chain_id }} AS chain_id,
      {% if price_token %}
      (SELECT nti.last_price FROM {{ price_schema }}.network_token_info nti WHERE nti.token_address = '{{ price_token }}'::bytea) AS gas_token_usd,
      {% else %}
      1.0::double precision AS gas_token_usd,
      {% endif %}
      count(*) AS blocks,
      extract(epoch FROM max(b.ts) - min(b.ts)) AS span_s,
      sum(cardinality(b.transactions)) AS txs,
      sum(b.gas_used) AS gas_used,
      sum(b.gas_limit) AS gas_limit,
      avg(b.base_fee_per_gas) AS avg_base_fee_wei,
      sum(b.base_fee_per_gas * b.gas_used) AS base_fee_paid_wei
  FROM {{ block(duration='24h', network=schema) }} b
  GROUP BY 1
  {% if not loop.last %}

  UNION ALL
  {% endif %}
  {% endfor %}
)
SELECT
    hour,
    network,
    -- Polygon PoS is grouped with the L1s (sidechain with its own consensus)
    CASE WHEN network IN ('Base', 'Arbitrum', 'Optimism', 'Robinhood') THEN 'L2' ELSE 'L1' END AS layer,
    chain_id,
    blocks,
    txs,
    round((span_s / nullif(blocks - 1, 0))::numeric, 3) AS block_time_s,
    round(((blocks - 1) / nullif(span_s, 0))::numeric, 3) AS blocks_per_sec,
    round((txs * (blocks - 1) / blocks / nullif(span_s, 0))::numeric, 2) AS tps,
    round((gas_used * (blocks - 1) / blocks / nullif(span_s, 0) / 1e6)::numeric, 2) AS mgas_per_sec,
    -- Arbitrum-style chains set a placeholder block gas limit (~1.1e15): utilization is not meaningful there
    CASE
      WHEN gas_limit / blocks < 1e12 THEN round((100 * gas_used / nullif(gas_limit, 0))::numeric, 2)
    END AS gas_used_pct,
    round((avg_base_fee_wei / 1e9)::numeric, 9) AS avg_base_fee_gwei,
    -- hourly rate (partial hours scaled), valued at the current gas-token price
    round((base_fee_paid_wei / 1e18 * gas_token_usd::numeric * 3600 / nullif(span_s, 0))::numeric, 2) AS base_fee_usd_per_hour
FROM per_hour
WHERE blocks > 1
  AND hour > now() - interval '24 hours'
```

## Series reader — L1 chains

The `L2` reader is the same query with `WHERE q.layer = 'L2'`.

```sql
-- Hourly network health, L1 chains only (max 8 chart series) · reads the 9-chain series via ref · last 24h
SELECT
    q.hour,
    q.network,
    q.chain_id,
    q.blocks_per_sec,
    q.block_time_s,
    q.tps,
    q.mgas_per_sec,
    q.gas_used_pct,
    q.avg_base_fee_gwei,
    q.base_fee_usd_per_hour
FROM {{ ref("Query") }} q
WHERE q.layer = 'L1'
ORDER BY q.hour, q.network
```

## Series reader — hourly totals

The source of the headline tiles. A `value` widget shows the newest row by its X column, the change from the row before it, and a sparkline.

```sql
-- Hourly totals over all 9 chains (headline tiles): blocks/s, TPS, Mgas/s, base-fee spend · reads the series via ref · last 24h
SELECT
    q.hour,
    count(*) AS networks,
    sum(q.blocks_per_sec) AS blocks_per_sec,
    sum(q.tps) AS tps,
    sum(q.mgas_per_sec) AS mgas_per_sec,
    sum(q.base_fee_usd_per_hour) AS base_fee_usd_per_hour
FROM {{ ref("Query") }} q
GROUP BY q.hour
ORDER BY q.hour
```

## Activity — top-level txs, last 1h (VIEW)

User TPS without system txs, active senders, failure rate, deploys, EIP-7702 and blob txs, median and total execution fee in USD.

```sql
-- Chain activity (VIEW, read by Totals via ref) from top-level txs: user TPS (system txs removed), active senders, failure rate, deploys, EIP-7702/blob use, fees · 9 chains · last 1h
{#- schema, label, chain_id, gas token, price schema, wrapped-native price token (none = pin to $1), system-tx predicate -#}
{% set weth = '\\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2' %}
{% set nets = [
  ('ethereum',  'Ethereum',  1,     'ETH',  'ethereum',  weth, 'false'),
  ('base',      'Base',      8453,  'ETH',  'ethereum',  weth, 't.tx_type = 126 AND t.tx_index = 0'),
  ('arbitrum',  'Arbitrum',  42161, 'ETH',  'ethereum',  weth, 't.tx_type = 106'),
  ('optimism',  'Optimism',  10,    'ETH',  'ethereum',  weth, 't.tx_type = 126 AND t.tx_index = 0'),
  ('polygon',   'Polygon',   137,   'POL',  'polygon',   '\\x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270', 'false'),
  ('binance',   'BNB',       56,    'BNB',  'binance',   '\\xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c', "t.to_a = '\\x0000000000000000000000000000000000001000'::bytea AND t.gas_price = 0"),
  ('avalanche', 'Avalanche', 43114, 'AVAX', 'avalanche', '\\xb31f66aa3c1e785363f0875a1b74e27b85fd66c7', 'false'),
  ('robinhood', 'Robinhood', 4663,  'ETH',  'ethereum',  weth, 't.tx_type = 106'),
  ('arc',       'Arc',       5042,  'USDC', none,        none, 'false')
] %}
{#- system txs: OP-stack L1-attributes deposit (type 126 at index 0), ArbitrumInternalTx (type 106), BNB validator-set call (0x…1000, zero gas price) -#}
WITH per_chain AS (
  {% for schema, label, chain_id, gas_token, price_schema, price_token, is_system in nets %}
  SELECT
      '{{ label }}' AS network,
      {{ chain_id }} AS chain_id,
      {% if price_token %}
      (SELECT nti.last_price FROM {{ price_schema }}.network_token_info nti WHERE nti.token_address = '{{ price_token }}'::bytea)::numeric AS gas_token_usd,
      {% else %}
      1.0 AS gas_token_usd,
      {% endif %}
      extract(epoch FROM {{ schema }}.block_timestamp(max(t.block_number)) - {{ schema }}.block_timestamp(min(t.block_number))) AS span_s,
      count(*) AS txs,
      count(*) FILTER (WHERE {{ is_system }}) AS system_txs,
      count(*) FILTER (WHERE NOT ({{ is_system }})) AS user_txs,
      count(DISTINCT t.from_a) FILTER (WHERE NOT ({{ is_system }})) AS active_senders,
      count(*) FILTER (WHERE NOT ({{ is_system }}) AND NOT t.status) AS failed_txs,
      count(*) FILTER (WHERE t.contract_address IS NOT NULL) AS contract_deploys,
      count(*) FILTER (WHERE t.tx_type = 4) AS setcode_7702_txs,
      count(*) FILTER (WHERE t.tx_type = 3) AS blob_txs,
      percentile_cont(0.5) WITHIN GROUP (ORDER BY t.gas_used * t.gas_price) FILTER (WHERE NOT ({{ is_system }}) AND t.gas_price > 0) AS median_fee_wei,
      sum(t.gas_used * t.gas_price) FILTER (WHERE NOT ({{ is_system }})) AS fees_wei
  FROM {{ outer_transaction(duration='1h', network=schema) }} t
  {% if not loop.last %}

  UNION ALL
  {% endif %}
  {% endfor %}
)
SELECT
    p.network,
    p.chain_id,
    p.txs,
    p.system_txs,
    p.user_txs,
    round(100.0 * p.system_txs / nullif(p.txs, 0), 2) AS system_tx_pct,
    round((p.user_txs / nullif(p.span_s, 0))::numeric, 2) AS user_tps,
    p.active_senders,
    round(100.0 * p.failed_txs / nullif(p.user_txs, 0), 2) AS failed_pct,
    p.contract_deploys,
    p.setcode_7702_txs,
    p.blob_txs,
    -- execution fee only (gas_used * gas_price): excludes OP-stack L1 data fees
    round((p.median_fee_wei::numeric / 1e18 * p.gas_token_usd)::numeric, 6) AS median_fee_usd,
    round((p.fees_wei / 1e18 * p.gas_token_usd)::numeric, 2) AS fees_usd_1h
FROM per_chain p
```

## Activity reader — totals

Headline tiles for user TPS and active senders. `active_senders` is a sum of per-chain counts: an address that is active on two chains counts two times.

```sql
-- Activity totals over all 9 chains (headline tiles): user TPS, active senders (summed per chain), fees · reads the activity view via ref · last 1h
SELECT
    count(*) AS networks,
    sum(a.user_txs)::bigint AS user_txs,
    sum(a.user_tps) AS user_tps,
    sum(a.active_senders)::bigint AS active_senders,
    round(100.0 * sum(a.system_txs) / nullif(sum(a.txs), 0), 2) AS system_tx_pct,
    sum(a.setcode_7702_txs)::bigint AS setcode_7702_txs,
    sum(a.fees_usd_1h) AS fees_usd_1h
FROM {{ ref("Query") }} a
```

## Transaction-type mix — last 1h

Exactly 8 kinds, so a stacked bar with `series_by = tx_kind` shows every kind without an `Other` group.

```sql
-- Transaction-type mix per chain (legacy / 1559 / blob / 7702 / L2 system & deposit txs) · 9 chains · last 1h
{#- schema, label, chain_id, gas token, price schema, wrapped-native price token (none = pin to $1), system-tx predicate -#}
{% set weth = '\\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2' %}
{% set nets = [
  ('ethereum',  'Ethereum',  1,     'ETH',  'ethereum',  weth, 'false'),
  ('base',      'Base',      8453,  'ETH',  'ethereum',  weth, 't.tx_type = 126 AND t.tx_index = 0'),
  ('arbitrum',  'Arbitrum',  42161, 'ETH',  'ethereum',  weth, 't.tx_type = 106'),
  ('optimism',  'Optimism',  10,    'ETH',  'ethereum',  weth, 't.tx_type = 126 AND t.tx_index = 0'),
  ('polygon',   'Polygon',   137,   'POL',  'polygon',   '\\x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270', 'false'),
  ('binance',   'BNB',       56,    'BNB',  'binance',   '\\xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c', "t.to_a = '\\x0000000000000000000000000000000000001000'::bytea AND t.gas_price = 0"),
  ('avalanche', 'Avalanche', 43114, 'AVAX', 'avalanche', '\\xb31f66aa3c1e785363f0875a1b74e27b85fd66c7', 'false'),
  ('robinhood', 'Robinhood', 4663,  'ETH',  'ethereum',  weth, 't.tx_type = 106'),
  ('arc',       'Arc',       5042,  'USDC', none,        none, 'false')
] %}
{#- system txs: OP-stack L1-attributes deposit (type 126 at index 0), ArbitrumInternalTx (type 106), BNB validator-set call (0x…1000, zero gas price) -#}
WITH per_kind AS (
  {% for schema, label, chain_id, gas_token, price_schema, price_token, is_system in nets %}
  SELECT
      '{{ label }}' AS network,
      {{ chain_id }} AS chain_id,
      CASE
        WHEN {{ is_system }} THEN 'System (L2 / validator)'
        WHEN t.tx_type = 0 THEN 'Legacy'
        WHEN t.tx_type = 1 THEN 'EIP-2930 access list'
        WHEN t.tx_type = 2 THEN 'EIP-1559'
        WHEN t.tx_type = 3 THEN 'EIP-4844 blob'
        WHEN t.tx_type = 4 THEN 'EIP-7702 set-code'
        WHEN t.tx_type = 126 THEN 'L1 deposit (bridge)'
        ELSE 'Other L2 type'
      END AS tx_kind,
      count(*) AS txs
  FROM {{ outer_transaction(duration='1h', network=schema) }} t
  GROUP BY 1, 2, 3
  {% if not loop.last %}

  UNION ALL
  {% endif %}
  {% endfor %}
)
SELECT
    network,
    chain_id,
    tx_kind,
    txs,
    round(100.0 * txs / sum(txs) OVER (PARTITION BY network), 3) AS pct_of_chain
FROM per_kind
ORDER BY network, txs DESC
LIMIT 200
```

## Ethereum block builders — 24h

Builder tag from `extra_data` (hub §8.19). The top 7 builders, then one `Other` row, so that a pie chart stays readable.

```sql
-- Ethereum block-builder market share (fee recipient + extra_data tag): blocks, share, txs/block, gas use, ETH burned · Ethereum · last 24h
WITH per_builder AS (
  SELECT
      b.coinbase,
      -- readable builder tag from extra_data; binary tags fall back to the fee-recipient address
      coalesce(
        mode() WITHIN GROUP (ORDER BY substring(encode(b.extra_data, 'escape') FROM '^[A-Za-z0-9 ._()/:-]{4,}')),
        concat('0x', left(encode(b.coinbase, 'hex'), 6), '…', right(encode(b.coinbase, 'hex'), 4))
      ) AS builder_tag,
      count(*) AS blocks,
      avg(cardinality(b.transactions)) AS avg_txs_per_block,
      avg(100 * b.gas_used / nullif(b.gas_limit, 0)) AS avg_gas_used_pct,
      sum(b.base_fee_per_gas * b.gas_used) AS burned_wei
  FROM {{ ethereum.block(duration='24h') }} b
  GROUP BY b.coinbase
),
ranked AS (
  SELECT
      *,
      row_number() OVER (ORDER BY blocks DESC) AS rnk
  FROM per_builder
)
SELECT
    CASE WHEN rnk <= 7 THEN trim(builder_tag) ELSE 'Other' END AS builder,
    CASE WHEN rnk <= 7 THEN concat('0x', encode(coinbase, 'hex')) END AS fee_recipient,
    1 AS chain_id,
    sum(blocks)::bigint AS blocks,
    round(100.0 * sum(blocks) / sum(sum(blocks)) OVER (), 2) AS share_pct,
    round(sum(avg_txs_per_block * blocks) / sum(blocks), 1) AS avg_txs_per_block,
    round(sum(avg_gas_used_pct * blocks) / sum(blocks), 2) AS avg_gas_used_pct,
    round(sum(burned_wei) / 1e18, 4) AS eth_burned
FROM ranked
GROUP BY 1, 2
ORDER BY blocks DESC
LIMIT 200
```

## Dashboard recipe

The dashboard grid has 12 columns. Create the widgets in the order of the table below, then run
`arrange-dashboard --id <DID>` one time. It gives the places in the last column (see `widgets.md`,
"Dashboard layout"). To change a place, edit its `--dry-run` JSON and give that to `set-layout`.

| Row (y) | Widget | Query | Type and axes | Place (x · width × height) |
|---------|--------|-------|---------------|----------------------------|
| 0 | TPS, blocks/s, Mgas/s, base-fee USD/h | series `Totals` | `value`, `--x hour --y <col>`, `timeframe 24h` | 2 × 2 each |
| 0 | User TPS, active senders | activity `Totals` | `value`, `--y <col>` (no time column: no sparkline) | 2 × 2 each |
| 2 | TPS · L1s, TPS · L2s | series `L1`, `L2` | `line`, `--x hour --y tps --series-by network`, `scale log` | 0 and 6 · 6 × 5 |
| 7 | User TPS by chain, block time by chain | activity, snapshot | `bar`, `--x network`, `order_by y`; block time with `scale log` | 0 and 6 · 6 × 4 |
| 11 | Gas used % · L1s, base-fee spend · L2s | series `L1`, `L2` | `line`; gas with `reference_line 50` (Ethereum target), fee with `scale log` and `number_format currency` | 0 and 6 · 6 × 5 |
| 16 | Transaction-type mix | tx-type mix | `stackedbar`, `--x network --y pct_of_chain --series-by tx_kind` | 0 · 8 × 4 |
| 16 | Ethereum block builders | builders | `pie`, `--x builder --y blocks` | 8 · 4 × 4 |
| 20 | Snapshot, activity | snapshot, activity | `table` | 0 · 12 × 6 each |

Rules that this recipe follows:

- **At most 8 series in one chart.** With more, the chart keeps 7 and adds the remaining series together
  as `Other`. A sum of TPS or of a percentage is wrong, so split the chains (here L1 and L2) or filter.
- **Log scale** when the chains differ by orders of magnitude: block time (0.1 s to 12 s), TPS (2 to 200),
  base-fee spend (0.01 to 5,000 USD per hour).
- **Base fee in USD, not gwei,** for a cross-chain chart (hub §8.16). BNB shows 0 (hub §8.15).
- **Gas used % is NULL** on Arbitrum and Robinhood (hub §8.14). The L1 chart has no such chain.
- In a widget label, write `\$` for a dollar sign.
