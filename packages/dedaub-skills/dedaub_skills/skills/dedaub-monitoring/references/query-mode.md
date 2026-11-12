# Query mode — one page

Read this page first in query mode. The rest of the skill still applies (constants from the protocol
refs, the SQL rules of Step 5, the decode gate). This page gives the flow and the facts that cost runs.
All numbers here were measured on the live platform on 2026-11-12.

## 1. Flow: explore without storing, store only the final query

1. **Login, once:** `dedaub-monitoring status`. Exit 3 = not logged in: tell the user to run
   `dedaub-monitoring login` and stop (a retry will not help).
2. **The probe query (one per entity, shared by every session):** get its id with
   `dedaub-monitoring query-metadata --path /_cli/Probe`. If it is not found, make it once:
   `create-folder "/_cli"` then `create-query "/_cli/Probe"`. Run every exploration and probe statement
   through it with the SQL on stdin — SQL given to `run-query` is run, **not stored**:
   ```bash
   dedaub-monitoring run-query --id <PROBE_ID> --network <chain> --format tsv --limit 50 <<'SQL'
   SELECT …
   SQL
   ```
   Always send SQL on stdin (a heredoc): as an argument, SQL that starts with a `--` comment is read as
   an option. Never `write-query` to the probe: other sessions use it. Never make a folder or a query for a question
   that you only explore.
3. **The final query:** when the SQL gives the right rows, make the slug folder and its `Query`
   (SKILL.md "Mode tail"), `write-query` the final SQL (header comment, readable `0x` columns), then
   `validate-query`, one `run-query`, and the decode gate. Give the user the link
   `https://app.dedaub.com/tx-monitor?queryId=<id>`.

## 2. CLI output and the query slots

- **`--format tsv`** (or `json`, one object per line) prints every row exact and uncut. `table` (the
  default) is for a person: in a pipe it cuts each cell to fit 80 characters.
- The CLI already prints `bytea`, address and hash columns as `0x…`. While you explore, select them raw;
  keep `concat('0x', encode(col, 'hex'))` for the stored final query.
- The API sends numbers as JSON floats: an integer from 2^53 up loses its last digits (the CLI prints a
  note). Select exact amounts as text: `amount::text`.
- **Two result columns with the same name lose one value** (the API returns each row as an object). Give
  each aggregate its own alias: `max(a) AS max_a, max(b) AS max_b`.
- More than 50 rows: write them to a file (`> rows.tsv`) and work on the file. Notes go to stderr.
- **The account runs 3 queries at a time.** `run-query` waits for a free slot by itself (`--wait`,
  default 300 s) and exits 4 when none frees in time. Do not write sleep or retry loops. Do not cancel a
  task that you did not start: it can belong to another session.
- **Hash helpers:** `selector('transfer(address,uint256)')`, `topic0('Transfer(address,address,uint256)')`
  and `keccak256('text')` with a string argument are replaced by the CLI with the hash literal and a
  comment, because the server has no keccak. `selector(d.calldata)` (a column) is the server's function.

## 3. Signature macros: three traps

- **Indexed flags.** `logs('0x….Event(type indexed name, …)')` matches topics by the `indexed` flags. Wrong
  flags return 0 rows with no error. Copy the flagged signature from the protocol ref (`## 1. Topics`), and
  write ABI types: a ref's Solidity types are not ABI types (`PoolId` → `bytes32`, `Currency`/`IHooks` →
  `address`, an enum → `uint8`, a struct → its tuple `(…)`).
  When a query returns 0 rows, `run-query` counts the logs of that topic0 by any emitter (forks too) and
  says whether the flags, the address or the window is the cause.
- **Signed integers decode wrongly.** For every `intN` parameter (`int24`, `int128`, `int256`, …) of a
  `logs(...)` or `transaction_detail(...)` signature, the platform reads the decimal value as hex. Positive
  values are wrong too (16202927503 comes back as 1520461575427). The CLI prints a warning for every
  such parameter in the SQL; a column that you do not select is harmless, but never select one. Decode these
  words by hand (exact for any `int128` and for an `int256` below 2^127 in size):
  ```sql
  -- word k (0-based) of l.data, as a signed integer
  ('x' || encode(substring(l.data FROM 32*k + 17 FOR 8), 'hex'))::bit(64)::bigint::numeric * power(2::numeric, 64)
    + ('x' || encode(substring(l.data FROM 32*k + 25 FOR 8), 'hex'))::bit(64)::bigint::numeric
    + CASE WHEN get_byte(l.data, 32*k + 24) >= 128 THEN power(2::numeric, 64) ELSE 0 END
  -- int24 … int64 (tick, tickSpacing): the last 8 bytes are enough
  ('x' || encode(substring(l.data FROM 32*k + 25 FOR 8), 'hex'))::bit(64)::bigint
  ```
  Do not use `common.hex_to_numeric` for a signed word: it is not exact from 2^128 up, and a negative
  word is close to 2^256. Address, bool and bytes parameters decode correctly, and so do unsigned ones
  below 2^128; the macro reads an unsigned value with `hex_to_numeric` too, so a value from 2^128 up
  (a `type(uint184).max` cap, an "unlimited" approval) loses its last digits. For those, decode the word
  as four 64-bit parts, each made unsigned (`+ 2^64` when its first byte is 128 or more).
- **Column names.** The macro names a decoded column in lower case (`collateralAsset` → `collateralasset`;
  a struct field → `marketparams_loantoken`). `preprocess-query` shows them.

## 4. Cost rules

1. **Bound the blocks of every table** (`duration=` in a macro, or
   `block_number > get_historical_block_number('2 day')` on a bare table).
2. **The topic0 index differs per chain.** Ethereum `(topic0, block_number)`, Arbitrum
   `(topic0, block_number, address)`, Base none. `get-schema --network <chain> --table logs` lists them.
3. **A filter, sort or aggregate on a column outside the index reads every row of the window.** Start
   with 2 days or less on a busy contract.
4. **Do not join the big tables to each other, and never join into `transaction_detail`.** For the hash
   and the time use `tx_hash(block_number, tx_index)` and `block_timestamp(block_number)`. For other
   transaction fields: collect the rows in a `MATERIALIZED` CTE ordered by `(block_number, tx_index)`,
   then join `outer_transaction` on those two columns under the same block bound.
5. **`outer_transaction` has no index on `to_a` and no `input` column.** The transactions sent to a
   contract are its frames at `vm_step_start = 0` in `transaction_detail`; their `calldata` is the input.
6. **An event of many emitters on a chain with no topic0 index (Base):** lead with the calls. Find the
   calls through the `(to_a, selector)` or `(selector)` index of `transaction_detail`, then read the logs of
   each such transaction in a `CROSS JOIN LATERAL (… WHERE x.block_number = c.block_number AND x.tx_index =
   c.tx_index AND x.vm_step_start = c.vm_step_start OFFSET 0)`. A join of a call CTE to the logs macro read
   all Base logs of 7 days and timed out; the call-led form took 2 to 19 s. In this form, annotated raw
   topic0/selector literals are fine (and a hand decode): the signature macros do not fit inside it. Make
   the call CTE `MATERIALIZED`: with an outer `ORDER BY … LIMIT` the planner otherwise walks the whole
   `transaction_detail` key in block order (two timeouts at 60 s, then 2.6 s).
7. **Frames older than about 3 months are stored by contract.** Read old frames by `to_a` (2.7 s), not by
   block alone (12 to 61 s). Old `logs` and `token_ledger` read by block were still fast (about 3 s).
8. **Give the planner a small set as an array:** `WHERE c.md5_bytecode = ANY (ARRAY(SELECT …))`. As a
   join or `IN`, the planner expects a large set and may scan a table of 60 million rows (2.6 s with the
   array, a timeout with the join).
9. **Read `common.code` by `md5_bytecode` only** (through `<chain>.contracts`): a condition on
   `contract_name` scans all rows (27 s against 3.7 s).
10. **Proxies:** the code a proxy runs is at `proxy_implementation_latest.implementation_address`, or
    behind a beacon at `transitive_address`. Match both.
11. **Decode at volume with `::bit(64)`** (§3), not `hex_to_numeric`: 3.6 s against 9.1 s on 146,000 logs.
12. **`eth_call`:** the target contract is a `bytea` column (`'\x…'::bytea`; as text the call fails with
    "function eth_call(text, …) does not exist"). An `address` argument goes as `'0x…'` text and a `uint` as
    a JSON number (a numeric column, not a string). A `bytes32` argument cannot be passed (always "Unable to complete eth_call").
    Write bare column names in the macro (`oracle.getAssetPrice(address asset)`, not `t.oracle`). A
    revert gives NULL. A macro with several outputs returns several columns: use it in `FROM … LATERAL`.
13. **`transaction_detail.vm_steps` is 0 on every chain** (do not use step ranges). A log carries the
    frame that emitted it: `logs.vm_step_start` = that frame's `vm_step_start`, in the same
    `(block_number, tx_index)`.
14. **One-to-one lookups by token (`latest_token_info`, `network_token_info`):** when the row estimate of
    the outer query is high, a plain `LEFT JOIN` can become a hash join over a sequential scan of 15.6
    million rows. Write `LEFT JOIN LATERAL (SELECT … WHERE t.token_address = x.token LIMIT 1) t ON true`
    and check `explain-query` for `Seq Scan`.
15. **Base makes a block every 0.2 s** (measured 2026-11-12; 18,000 blocks an hour). A window of one day on
    Base holds about 10 times the blocks of a day on a 2-s chain: an address-led scan of a busy Base
    contract that is fast for 1 day can time out for 4.

## 5. Prices

- `network_token_info.last_price` is the newest point of `common.historical_token_price`, and that feed
  has single outliers: AAVE showed 25.57 for about an hour on 2026-11-12, against about 117. For a USD
  figure that matters, check one row against a second source: the other leg of a swap, the protocol's own
  oracle (`eth_call`), or the median of the last 6 hours of `common.historical_token_price`.
- **USD at the time of an event:** take the nearest sample of `common.historical_token_price` on either
  side of the block time (within a few hours), not the nearest earlier one: in a fast market the earlier
  sample can be an hour old (wstETH 2591 against 2515 in a crash, collateral 3% too high). Some tokens have
  no sample for days (USDG, RLUSD, BTC.b, MKR): fall back to `last_price` and say so in the header.
- **Symbol:** `latest_token_info.symbol` is empty for a token with a `bytes32` symbol (MKR): use
  `COALESCE(NULLIF(lti.symbol, ''), nti.symbol)`.
- Stablecoins have prices: USDC, USDT and DAI are about 0.9998 on all chains, and `to_usd_value` works
  for them. Keep a `$1` pin by address only as the fallback for a NULL price.
- Spoof tokens get prices too (a fake "Tether" gave one pool a volume of 790 billion USD). For swap
  volume, price only the leg that is a known quote asset (WETH, USDC, USDT, DAI, WBTC, cbBTC, wstETH, …).
  For a sum of holdings, cap each position at the market cap: `least(usd, n.last_cap)`.

## 6. Incidents

Who gained and who lost, who else runs the same code, and where the money went: P19–P21 in
`database/sample_queries/incidents.md`, each tested on a real drain.
