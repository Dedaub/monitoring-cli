# Incident queries (P19–P21)

When a contract is drained, three questions come first: who lost what (P19), who else runs the same
code (P20), and where the money went (P21). Each query below ran on the live platform on 2026-11-12
against a real drain: a market maker drained on 7 May 2026 on Ethereum by the account
`0xc3ebddea4f69df717a8f5c89e7cf20c1c0389100` (helper `0xd4d5db5ec65272b26f756712247281515f211e95`).
The source of the queries is Neville Grech's query guide for the Rust CLI, changed to this platform's
syntax (chain prefixes, `\x` literals, `common.code`, `common.normalised_md5`, `common.listed_contracts`,
`pow(10::numeric, …)`).

The example is months old, so it bounds the blocks with numbers. In a live incident write
`> ethereum.get_historical_block_number('2 day')` (or the window of the attack) in each place. Find the
attacker: the `eoa_deployer` of the exploit contract in `<chain>.contracts`. Run these through the probe
query (`query-mode.md` §1): they are investigation, not stored queries.

## P19 — Who gained and who lost

Every token movement inside the attacker's transactions, netted per address and token. 2.6 s.

```sql
WITH a AS MATERIALIZED (
    SELECT o.block_number, o.tx_index
    FROM ethereum.outer_transaction o
    WHERE o.from_a = '\xc3ebddea4f69df717a8f5c89e7cf20c1c0389100'::bytea
      AND o.block_number BETWEEN 25039000 AND 25100000
    ORDER BY o.block_number, o.tx_index
)
SELECT concat('0x', encode(x.address, 'hex')) AS address,
       (SELECT k.contract_name FROM ethereum.contracts c JOIN common.code k USING (md5_bytecode) WHERE c.address = x.address LIMIT 1) AS name,
       n.symbol, x.transfers, round(x.net / pow(10::numeric, n.decimals), 4) AS net,
       round((x.net * n.last_price / pow(10::numeric, n.decimals))::numeric) AS usd_now
FROM (
    SELECT l.address, l.token_address, count(*) AS transfers, -sum(l.value_delta) AS net
    FROM ethereum.token_ledger l
    JOIN a USING (block_number, tx_index)
    WHERE l.block_number BETWEEN 25039000 AND 25100000
    GROUP BY l.address, l.token_address
    HAVING sum(l.value_delta) <> 0
) x
JOIN ethereum.network_token_info n USING (token_address)
ORDER BY abs(x.net * n.last_price / pow(10::numeric, n.decimals)) DESC NULLS LAST
LIMIT 12
```

- Result: the victim `0x9ba0…da31` shows −1,291.16 WETH, −1,268,771 USDC, −16.94 WBTC and −206,282 USDT,
  the published figures.
- The transactions are collected first in position order, then the ledger is joined on
  `(block_number, tx_index)` under the same block bound (cost rule 4).
- For one transaction no CTE is needed:
  `WHERE (l.block_number, l.tx_index) = (SELECT o.block_number, o.tx_index FROM ethereum.outer_transaction o WHERE o.tx_hash = '\x…'::bytea)`.
- Read the ETH rows with care: a native transfer in the ledger can be the value that a DELEGATECALL
  inherits. Here a Tornado Cash hasher shows +404 ETH that never moved.

## P20 — Who else runs the code, and what it holds

The contracts whose bytecode equals the vulnerable one up to its constants, and the proxies in front of
them, ranked by what they hold. The example is Aave's aToken implementation. 2.6 s.

```sql
WITH code AS MATERIALIZED (
    SELECT c.address
    FROM ethereum.contracts c
    WHERE c.md5_bytecode = ANY (ARRAY(
              SELECT m.md5_bytecode::bytea
              FROM ethereum.contracts x
              JOIN common.normalised_md5 v USING (md5_bytecode)
              JOIN common.normalised_md5 m USING (normalised_md5)
              WHERE x.address = '\xadc45df3cf1584624c97338bef33363bf5b97ada'::bytea))
      AND c.block_number_destroyed IS NULL
), holder AS MATERIALIZED (
    SELECT address FROM code
  UNION
    SELECT p.proxy_address
    FROM ethereum.proxy_implementation_latest p
    WHERE p.implementation_address = ANY (ARRAY(SELECT address::bytea FROM code))
       OR p.transitive_address = ANY (ARRAY(SELECT address::bytea FROM code))
)
SELECT concat('0x', encode(h.address, 'hex')) AS holder, count(*) AS tokens,
       round(sum(least(b.value * n.last_price / pow(10::numeric, n.decimals), n.last_cap))::numeric) AS usd,
       (array_agg(n.symbol ORDER BY b.value * n.last_price / pow(10::numeric, n.decimals) DESC))[1:3]::text AS largest
FROM holder h
JOIN ethereum.token_balance b ON b.owner_address = h.address
JOIN ethereum.network_token_info n USING (token_address)
WHERE b.value > 0
  AND n.last_cap > 0
GROUP BY h.address
ORDER BY usd DESC NULLS LAST
LIMIT 8
```

- Result: the aToken markets, from the weETH market at 3.05 billion USD down.
- Each set goes in as an array (cost rule 8). With plain joins the same query timed out after more than
  100 s: the planner scanned the proxy table.
- `normalised_md5` joined to itself gives the family of bytecodes that differ only in their constants. It
  says nothing for a tiny stub: a runtime of 68 bytes shares its value with many unrelated contracts.
- A proxy runs the code at `implementation_address` or, behind a beacon, at `transitive_address`: match both.
- `least(…, n.last_cap)` caps a position at the token's market cap, so worthless tokens with made-up
  prices do not lead the sums.

## P21 — Where the money went

A walk forward from the attacker's addresses, one hop at a time, three hops deep. 63 s on the first run;
faster when the rows are cached.

```sql
WITH RECURSIVE node AS (
    SELECT 0 AS hop, s.a AS address, 25039670::bigint AS since, true AS follow
    FROM (VALUES ('\xc3ebddea4f69df717a8f5c89e7cf20c1c0389100'::bytea), ('\xd4d5db5ec65272b26f756712247281515f211e95'::bytea)) s(a)
  UNION
    SELECT t.hop + 1, o.to_a, o.since,
           (SELECT count(*) FROM (
                SELECT 1 FROM ethereum.token_ledger q
                WHERE q.address = o.to_a AND q.block_number > 25030000
                  AND q.block_number BETWEEN o.since - 7200 AND o.since - 1
                LIMIT 51) busy) <= 50
    FROM node t
    CROSS JOIN LATERAL (
        SELECT l.counterparty_address AS to_a, min(l.block_number) AS since
        FROM ethereum.token_ledger l
        JOIN ethereum.network_token_info n USING (token_address)
        WHERE l.address = t.address AND l.block_number > 25030000 AND l.block_number >= t.since
          AND l.value_delta > 0
        GROUP BY l.counterparty_address
        HAVING sum(l.value_delta * n.last_price / pow(10::numeric, n.decimals)) > 10000
    ) o
    WHERE t.follow AND t.hop < 2
), followed AS MATERIALIZED (
    SELECT address, min(hop) AS hop, min(since) AS since FROM node WHERE follow GROUP BY address
)
SELECT t.hop + 1 AS hop, concat('0x', encode(t.address,'hex')) AS from_a, concat('0x', encode(e.to_a,'hex')) AS to_a,
       CASE WHEN EXISTS (SELECT 1 FROM ethereum.contracts c WHERE c.address = e.to_a) THEN 'contract' ELSE 'account' END AS kind,
       (SELECT string_agg(DISTINCT cl.list_name, ', ') FROM common.listed_contracts lc JOIN common.contract_list cl USING (list_id)
        WHERE lc.address = e.to_a
          AND cl.list_name IN ('exchange', 'Deposit Address', 'Kraken', 'Coinbase', 'Binance',
                               'tornado_cash_addresses', 'hack-phish-related')) AS labels,
       n.symbol, e.transfers, e.amount / pow(10::numeric, n.decimals) AS amount,
       round((e.amount * n.last_price / pow(10::numeric, n.decimals))::numeric) AS usd_now, ethereum.block_timestamp(e.first_block) AS first_time
FROM followed t
CROSS JOIN LATERAL (
    SELECT l.counterparty_address AS to_a, l.token_address, count(*) AS transfers, sum(l.value_delta) AS amount,
           min(l.block_number) AS first_block
    FROM ethereum.token_ledger l
    WHERE l.address = t.address AND l.block_number > 25030000 AND l.block_number >= t.since
      AND l.value_delta > 0
    GROUP BY l.counterparty_address, l.token_address
) e
JOIN ethereum.network_token_info n ON n.token_address = e.token_address
WHERE e.amount * n.last_price / pow(10::numeric, n.decimals) > 10000
ORDER BY hop, usd_now DESC
LIMIT 80
```

- `node` holds the accounts the money passed through, each with the block at which it was first paid;
  only its transfers from that block on are read. The final `SELECT` lists what they sent.
- An account is followed only if it was quiet before it was paid: at most 50 ledger rows in the 7,200
  blocks (one day) before. A busy one is an exchange wallet, a bridge or a pool, where the money mixes:
  it shows as a receiver and the walk stops there. Without this test the walk timed out.
- Only a receiver of 10,000 USD or more is followed, so dust sent to bystanders does not pull them in.
- Labels come last, on the printed rows only, from `common.contract_list` and `common.listed_contracts`.
  Name the lists: many public lists were made by users.
- Result: hop 1 shows the attacker's accounts (labelled `hack-phish-related`); hop 2 shows 1,174 ETH
  reaching an `exchange` address on 2026-08-18.
