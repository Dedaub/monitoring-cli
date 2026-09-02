# Decode Verification (Step 5 gate — run it after the tuning loop)

The empirical gate proves the SQL **executes** and returns rows. It does not prove the **values**
in those rows are correct. This gate checks the values. Run it after the tuning loop and before
you show results (query mode) or dispatch the Reviewer (alert mode). It runs in **both modes**.

The gate **reports**; it does not rewrite. Fix a rejected query in place with `write-query` on the
same id, then run the gate again.

Report in the **Decode Verdict** shape (`handoff-schemas.md`).

---

## Why this gate exists

A generated Morpho Blue liquidation query returned rows that looked like data and were not:

| Rendered cell | Fault |
|---|---|
| `repaid_shares 6.520726627089377e+26` in a column typed `int8` | `int8` stops at `9223372036854775807` (9.22e18). A column cannot hold 6.5e26. |
| the **same** `6.520726627089377e+26` on 6 rows with different `tx_hash` | Independent liquidations do not produce a byte-identical `uint256`. |
| `repaid_assets 120000007`, `loan_token_symbol USDC` | Raw, unscaled. The value is **120.000007 USDC** (6 decimals). |

Root cause of the first two: the value crossed the wire as a **JSON float**. `float64` holds
integers exactly only to **2^53 = 9007199254740992**, and `str(float)` switches to `e+` notation at
**1e16**. The two thresholds nearly coincide, so **an `e+` in an amount cell is a near-exact proxy
for lost precision**. `str()` of an `int` never yields `e+`, so an `e+` cell **proves** the value
was floated. The loss happens before the CLI renders the row, so no CLI change recovers it. The fix
belongs in the SQL projection.

Float spacing at 6.5e26 is `1.374e11`: two distinct amounts closer than that render identically.
That is a real collapse mechanism, so Check 3 stays independent of Check 1.

---

## Tier 1 — read what you already have (no new run)

Inputs: the `run-query` output the tuning loop produced, and
`dedaub-monitoring query-columns --id <ID>` (free — it does not execute the query).

Checks are numbered 1–6 and the numbers are stable. Tier 1 holds Checks 1, 2, 3 and 6 because they
need no new run. Checks 4 and 5 need a probe run, so they sit in Tier 2.

### Check 1 — Float transport (blocker)

Scan every **amount** cell of the `run-query` output for **`e+`**.

An amount in scientific notation proves the value crossed the wire as a float. Every digit past the
17th is reconstructed, not read.

**Fix:** project the raw amount as `::text`, and add a scaled companion (Check 6).

**`e-` is not a fault, and it never blocks.** `str()` renders any float below `1e-4` in scientific
notation, so `e-` marks a **small** float, which `float64` holds exactly. Two columns in this skill
produce `e-` in healthy output: `nti.last_price` is a `double` and a low-priced token prices near
`1.23e-05`; an oracle-deviation query reads `abs(price - 1.0)`, which is near zero on a healthy peg.
Check 1 covers integer amount columns only. It does not cover a price, a ratio or a percentage.

### Check 2 — Declared type cannot hold the value (blocker)

Pair each `column_type` from `query-columns` with the rendered values.

A column declared `int8` or `int4` whose value exceeds `9223372036854775807` is a contradiction.
The observed 6.52e26 exceeds the `int8` maximum by a factor of 7.07e7.

### Check 3 — One amount on several distinct events (blocker unless declared)

Group the rendered rows by each amount column. **Ignore `0` and NULL.** Flag any remaining value
that appears on **2 or more rows with a different `tx_hash`**.

**The zero exclusion is load-bearing.** A correct decode repeats `0` by design. Morpho Blue's
`Liquidate(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)` ends in `badDebtAssets`
and `badDebtShares` (`protocols/morpho/v1.md`), and both are `0` on every liquidation that leaves no
bad debt — the large majority. Without the exclusion, a fully correct per-word decode rejects on its
own `0` column. The same holds for `fee`, `protocolFee`, and `amount1` on a single-sided event.

Separate the two causes and say which one applies:

- Check 1 also fires → float collapse.
- Check 1 is clean → a JOIN fan-out or an aliasing fault. Probe A separates the two: `n_rows`
  above `n_events` is a fan-out.

**Escape hatch:** a genuinely fixed non-zero amount passes **only if the header comment says so**.

### Check 6 — Raw amount without its unit (blocker)

Every projected token amount ships with `decimals` **and** `symbol`, or with a scaled companion
column. A reader cannot tell a large number from a large value without the decimals.

Source both from `latest_token_info` (`database/decode_primitives.md`) — PK `token_address`, 1:1, no
fan-out.

```sql
    repaid_assets::text                                      AS repaid_assets_raw,
    round(repaid_assets / pow(10::numeric, lti.decimals), 6) AS repaid_assets_scaled,
    lti.symbol
```

**The `::numeric` base is load-bearing.** `pow(10, decimals)` resolves to `pow(double precision,
double precision)` and returns `double precision`, which floats the amount again. Verified:
`pg_typeof(pow(10, 6::smallint))` is `double precision`; `pg_typeof(pow(10::numeric, 6::smallint))`
is `numeric`.

Verified output: `120000007` → `120.000007` USDC; `958080000000000000` → `0.958080` USUAL.

**This recipe renames the column.** `repaid_assets` becomes `repaid_assets_raw` plus
`repaid_assets_scaled`. In alert mode the old name may sit in a `--unique-key` or an
`--alert-template {{var}}`. **After any fix that renames a projected column, run
`query-columns --id <ID>` again and update the flags** before the Reviewer or the deploy. The
alert-column proof in `SKILL.md` Step 5 runs *before* this gate, so it does not cover a rename this
gate causes. Keeping the original name on the scaled column avoids the problem altogether.

---

## Tier 2 — one probe query id, four statements

Run Tier 2 when Tier 1 flags, **or** when the SQL decodes `log.data` by hand.

Create the probe with `create-query "/<slug>/Probe"` — a short role name in the query's own folder,
like `Query`, `Alert`, `Detail` and `Summary`. Reuse its id for all four statements: `write-query`
one statement, `run-query`, then overwrite with the next. Never delete it and never spawn siblings.

**Every statement below opens with the same prelude. Paste it at the head of each one:**

```sql
WITH probe AS (
    <the generated final SELECT, with ORDER BY and LIMIT removed, and with
     block_number, tx_index, log_index and the raw bytea token address added>
)
```

**The four added columns are not optional.** The house style projects a **readable** `tx_hash`
(`concat('0x', encode(<chain>.tx_hash(block_number, tx_index), 'hex'))`) and a **symbol**, so the
event key and the raw token address are normally absent from the final projection. Probe A groups on
the event key. Checks 4 and 5 join on the raw address and on the block coordinates. Add the columns
to the probe CTE only. Never add them to the query the user gets.

Substitute the real amount column for `repaid_shares` and `repaid_assets` below.

### Probe A — counters (Checks 1, 2 and 3 in one row)

Runs in exact `numeric`. It never touches a float.

```sql
WITH probe AS ( <see the prelude above> )
SELECT
    count(*)                                                                                AS n_rows,
    count(DISTINCT (block_number, tx_index, log_index))                                     AS n_events,
    count(DISTINCT repaid_shares) FILTER (WHERE repaid_shares <> 0)                          AS n_distinct_repaid_shares,
    count(*) FILTER (WHERE repaid_shares IS DISTINCT FROM (repaid_shares::float8)::numeric)  AS n_precision_lost,
    count(*) FILTER (WHERE abs(repaid_shares) > 9007199254740992::numeric)                   AS n_over_float_exact,
    max(length(trim(leading '-' from repaid_shares::text)))                                  AS max_digits
FROM probe
```

**Read every counter. Each one maps to a verdict:**

| Counter | Reading |
|---|---|
| `n_rows = 0` | The probe returned nothing. The gate proved nothing. Fix the probe and run it again. |
| `n_rows > n_events` | A JOIN fan-out. One event became several rows. **REJECT** (Check 3). This is the only mechanical fan-out detector in the gate. |
| `n_distinct_repaid_shares` far below `n_events` | Amounts repeat. Run Probe B to name them. **REJECT** (Check 3) unless the header comment declares the amount fixed. |
| `n_precision_lost > 0` | The value does not survive a float round trip. **REJECT** (Check 1). |
| `n_over_float_exact > 0` | The value is above `2^53`, so it renders as `e+`. **REJECT** (Check 1). |
| `max_digits > 40` | Not an amount. **REJECT** (Check 4). Verified bounds: a real 18-decimal amount at 1e12 whole tokens is **31** digits; one `uint256` word holds at most **78**; a 5-word body decoded whole holds up to **386**. The one legitimate exception is an allowance column holding the `2^256 - 1` approval sentinel. |

`max_digits` is the fallback bound when Check 4 reports `n_unbounded > 0`. It needs no token
metadata.

**Keep both float counters.** They are independent. Verified: `seized_assets =
20542000000000000000000` scores `n_precision_lost = 0` — it carries only 5 significant digits, so
the shortest float representation round-trips — but `n_over_float_exact = 1`, and it still renders
as `2.0542e+22`. `n_precision_lost` alone misses it.

### Probe B — name the repeated values (Check 3)

```sql
WITH probe AS ( <see the prelude above> )
SELECT repaid_shares::text     AS value,
       count(*)                AS rows,
       count(DISTINCT tx_hash) AS distinct_txs
FROM probe
WHERE repaid_shares IS NOT NULL
  AND repaid_shares <> 0
GROUP BY repaid_shares
HAVING count(DISTINCT tx_hash) > 1
ORDER BY rows DESC
LIMIT 5
```

The `WHERE` clause carries Check 3's zero exclusion. Verified on a 6-row fixture: without it, a
correct `bad_debt_assets` column reports `value 0, rows 5, distinct_txs 5` and blocks a correct
query. With it, that column returns 0 rows, and a genuinely repeated `repaid_shares` still reports
`rows 6, distinct_txs 6`.

### Check 4 — Amount above the token's own total supply (blocker)

A single event amount cannot exceed the token's total supply. The bound is exact, not a guess.
Read `total_supply` from `latest_token_info` (`database/decode_primitives.md`).

```sql
WITH probe AS ( <see the prelude above> )
SELECT count(*)                                                   AS n_rows,
       count(*) FILTER (WHERE p.repaid_assets > lti.total_supply)  AS n_impossible,
       count(*) FILTER (WHERE lti.total_supply IS NULL)            AS n_unbounded
FROM probe p
LEFT JOIN <chain>.latest_token_info lti ON lti.token_address = p.loan_token
```

**`LEFT JOIN`, and read all three numbers.** An inner `JOIN` drops a token that has no
`latest_token_info` row before the FILTER sees it. `x > NULL` is also NULL, so a row whose
`total_supply` is NULL is never counted. Both paths report zero on rows the check never examined,
and without `n_rows` the caller cannot tell "0 of 6" from "0 of 1". Verified on a 6-row fixture
holding two 38-digit whole-blob amounts: the inner-join form prints `impossible_rows = 0`; this form
prints `n_rows 6, n_impossible 0, n_unbounded 2`. `SKILL.md` Step 5 already carries the same rule —
LEFT JOIN so rows survive missing metadata.

**Read the result:**

- `n_impossible > 0` → **REJECT**.
- `n_unbounded > 0` → the bound did not apply to those rows, and Check 4 proves nothing about them.
  Fall back to `max_digits` (Probe A) and to Check 5. State in the verdict how many rows the bound
  covered.
- `n_impossible = n_rows` → suspect the unit, not the data. This check reads `total_supply` as raw
  base units. Confirm that before you reject, because a scaled `total_supply` makes every row look
  impossible.

This check catches a whole-blob or straddled decode. A 5-word event body is 160 bytes; decoded
whole it is a several-hundred-digit number. An off-by-one `substring(data FROM 32 FOR 32)` straddles
two words and decodes to 76 digits. Both dwarf any real supply.

### Check 5 — The decoded amount matches a real token movement (blocker, conditional)

The strongest decode-correctness check. It uses the in-tx `token_ledger` recipe from
`database/decode_primitives.md`: for Morpho `Liquidate`, seized collateral is the `value_delta =
+seizedAssets` row and the repaid loan is the `-repaidAssets` row. The `LIMIT 1` inside the LATERAL
guarantees no fan-out.

```sql
WITH probe AS ( <see the prelude above> )
SELECT count(*)                                        AS n_rows,
       count(*) FILTER (WHERE m.token_address IS NULL) AS n_unmatched_decodes
FROM probe p
LEFT JOIN LATERAL (
    SELECT tl.token_address
      FROM {{token_ledger(network='<chain>', duration='<w>')}} tl
     WHERE tl.block_number = p.block_number
       AND tl.tx_index     = p.tx_index
       AND tl.address      = '\x<protocol_contract>'::bytea
       AND tl.value_delta  = -p.repaid_assets
     LIMIT 1
) m ON true
```

`n_unmatched_decodes > 0` means the decoded number matches no token movement in its own
transaction. The decode is wrong.

**Applicability.** This check works **only if the underlying token moves**. Skip it for cToken,
eVault-share and aToken-share seizes (Compound V2 `seizeTokens`, Euler V2 `yieldBalance`, Aave V4
`liquidatedShares`), which move a wrapper token. Record the skip as a Suggestion that names the
wrapper reason. Never report a pass you did not run.

---

## Fix recipes

### Decode one word of `log.data`, not the whole blob

`database/decode_primitives.md` gives the whole-blob form, which is correct only for a
**single-word** body. For a multi-word body, take one 32-byte word. PostgreSQL `substring` is
1-indexed, so word **N** (0-based) starts at **32N + 1**:

```sql
common.hex_to_numeric('0x' || encode(substring(l.data FROM 33 FOR 32), 'hex'))  AS repaid_shares
```

Verified on a 160-byte body: the words start at `FROM 1`, `33`, `65`, `97` and `129`. `FROM 32`
straddles two words and returns garbage.

**Prefer the signature-form macro** (`database/macros.md`), which returns decoded named columns and
removes the offset arithmetic altogether.

### Prefer `value_delta` over decoding `logs.data`

`SKILL.md` Step 5 already carries the hard rule **"Value math via `token_ledger.value_delta`
(signed), not decoding `logs.data`"**. A query that hand-decodes `log.data` for an amount broke an
existing rule. Say so in the verdict, and offer the `value_delta` source as the fix.

### After a fix that renames a column

Run `query-columns --id <ID>` again. In alert mode, confirm every `--unique-key` and every
`--alert-template {{var}}` still appears in the output, and update the flags if not.

---

## Verdict and what the caller does

| Result | Caller action |
|---|---|
| **APPROVED** | Continue. Query mode → show results. Alert mode → the Reviewer. |
| **REJECTED** | Fix **in place** with `write-query` on the **same id** — never a sibling. Then `validate-query` → `run-query` → `query-columns` → this gate again. **Bound at 2 rounds**, like the Reviewer's revise loop. |
| **Still rejected after 2 rounds** | **STOP and ask the user**, offering: (a) project the raw amount as `::text` and drop the decode, (b) switch the amount source to `token_ledger.value_delta`, (c) accept and deploy with the limitation written into the header comment. |
| **Check 5 not applicable** | Record it as a Suggestion that names the wrapper-token reason. |

`query-columns` stays inside the loop for two reasons. Check 2 reads its output on every round, and
a fix that renames a column invalidates the alert-column proof taken before the gate.

**Blockers:** Checks 1, 2, 3, 4, 5 and 6.
**Suggestions (never block):** a skipped Check 5, a repeat the header comment already declares, and
column naming.

---

## Out of scope (deliberate)

| Dropped | Why |
|---|---|
| Re-decoding the ABI inside SQL | No keccak primitive exists in the documented schema. A placeholder check is worse than none. |
| Cross-checking against an RPC | `eth_call` reads **current** state at tip and costs one RPC per row. It cannot re-read a historical amount. |
| A USD plausibility threshold | Any figure is arbitrary, and `to_usd_value` **silently returns 0** for unpriced tokens, notably stablecoins. Check 4 gives an exact bound instead. |
| Detecting wrong `indexed` flags | Wrong flags give **silent 0 rows** (`database/macros.md`), and the tuning loop already requires ≥1 row. The empirical gate covers it. |
| Changing the CLI or the wire format | The precision loss happens **before** the CLI. The value arrives already floated. |
| A new CLI subcommand | Every check runs on `query-columns` output, `run-query` output, or the probe query. |
| Rewriting the query automatically | This is a verification step, not a rewrite step. The gate reports; the orchestrator fixes. |
| Checking a price or a ratio for float transport | A price is a `double` by design (`nti.last_price`). Check 1 covers integer amount columns only. |
