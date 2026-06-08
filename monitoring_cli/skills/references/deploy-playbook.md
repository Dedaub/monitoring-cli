# Alert Deploy Playbook (alert mode, after Reviewer APPROVES)

**Precondition (from Step 5):** the real target query `/<AlertName>/<QueryName>` is already
**created, written, and passed the empirical gate** (`validate-query` first, then `run-query`). Any
VIEW/TABLE lookup it reads via `{{ref(<id>)}}` is already created and `set-config`'d. So this playbook is
mostly `enable-alerts` + smoke-test + finalize. Run in order; stop and report on any failure.

**Variables:** `QUERY_ID`, `NETWORK` (the chain the query's macros read), `ALERT_TEMPLATE`
(no backticks), `UNIQUE_KEY` (comma-separated), `FREQUENCY` (seconds), `EMAIL_FLAG`
(`--email`/empty), `WEBHOOK_FLAG` (`--webhook-id <id>`/empty).

## (Optional) lookup layer — only if the alert reads a VIEW/TABLE via ref

Must already exist before the alert SQL was validated, since the alert `{{ref()}}`s it:
```bash
dedaub-monitoring create-query "/<AlertName>/<LOOKUP_NAME>"     # -> capture LOOKUP_ID
dedaub-monitoring write-query --id <LOOKUP_ID> <<'SQL'
<lookup SQL>
SQL
# VIEW = re-evaluated each run (reusable, not materialized); TABLE = refreshed snapshot (history)
dedaub-monitoring set-config --id <LOOKUP_ID> --network <NETWORK> --materialize VIEW
# the alert references it as: FROM {{ref(query_id=<LOOKUP_ID>)}}
```
For a **TABLE** lookup (history-spanning), force the first population so the alert's `{{ref()}}` resolves
to real rows immediately instead of on the next scheduled cycle:
```bash
dedaub-monitoring materialize --id <LOOKUP_ID>          # kicks off a materialization run; prints the task id
dedaub-monitoring query-status --id <LOOKUP_ID>         # confirm is_materialized=true before relying on the ref
```

## Prove the alert columns exist (before enable-alerts)

```bash
dedaub-monitoring query-columns --id <QUERY_ID>   # output columns (name+type); also re-validates the SQL
```
Confirm every column in `<UNIQUE_KEY>` and every `{{var}}` in `<ALERT_TEMPLATE>` appears. A unique-key or
template column the SELECT doesn't project is the most common deploy failure — catch it here, not after
it materializes.

## Enable alerts (smoke frequency first)

```bash
dedaub-monitoring enable-alerts --id <QUERY_ID> --network <NETWORK> --frequency 30 \
  --incrementalization IGNORE \
  --alert-template "<ALERT_TEMPLATE>" --unique-key "<UNIQUE_KEY>" \
  <EMAIL_FLAG> <WEBHOOK_FLAG>
```

**If it fails "Permission denied on .../config"** — at the INCREMENTAL materialization limit. Borrow a slot:
```bash
dedaub-monitoring list-alerts --network <NETWORK>            # pick a borrowable query (not this session's)
dedaub-monitoring set-config --id <BORROWED_ID> --network <NETWORK> --materialize TABLE  # remember its freq
# retry enable-alerts; restore afterwards:
dedaub-monitoring set-config --id <BORROWED_ID> --network <NETWORK> --materialize INCREMENTAL \
  --frequency <ORIG> --incrementalization IGNORE
```

## Verify the config landed (read it back — the UI modal can lie)

`enable-alerts` writes **per-`(query, network)`** config (`set_run_config` + `set_notify_config`). Two
gotchas this creates:
- The CLI's default `--network` is **`ethereum`** — if the query's macros read another chain and you
  forgot `--network <NET>`, the alert config landed on the **wrong network slot** and the query will
  never alert on its real chain. **`<NETWORK>` here MUST equal the chain the query's macros read.**
- The platform's **Query Configuration Settings** modal is **scoped to the UI's selected Default
  Network** — it shows None/off for any network other than the one selected, so it is *not* proof the
  alert exists. Don't trust it; read the config back from the API instead:

```bash
dedaub-monitoring get-config --id <QUERY_ID> --network <NETWORK>   # expect materialize=INCREMENTAL, frequency=<FREQUENCY>
```
If `get-config` on the alert's network shows `INCREMENTAL` + your frequency, the config is live
regardless of what the UI modal renders for its currently-selected network.

### Execution slot — explicit-`network=` / cross-chain queries deploy on `ethereum` (chain_id=1)

`--network` = data chain holds **only for network-agnostic macros** (no `network=`; the slot injects the
chain). When the SQL **hard-codes `network=`** (the skill's norm), and for any **cross-chain `UNION`**, the
data chain is fixed in the SQL, so the slot is just an execution identity — and the materializer/scheduler
**defaults it to `chain_id=1`**. Deploy on any other slot and `materialize`/`query-status` fail with
`Unable to locate query … chain_id=1` and **no run ever fires**. **Fix: `enable-alerts --network ethereum`**
(macros still read their own chains). Confirm:
```bash
dedaub-monitoring materialize  --id <QUERY_ID>     # force a run
dedaub-monitoring query-status --id <QUERY_ID>     # expect is_materialized=true + recent last_time_run
dedaub-monitoring get-logs     --id <QUERY_ID>     # expect a SUCCESS row
```
Park any stray data-chain slot so it stops FAIL-ing: `set-config --id <QUERY_ID> --network <data-chain>
--materialize TABLE`. (`materialize` takes no `--network` — always chain_id=1; `reset-materialization` is
broken — POSTs no body → 422.) Same for a TABLE+`{{ref()}}` lookup (won't materialize off-slot, `ref`
fails) — so prefer resolving history-spanning data **in-tx** when possible (e.g. a Morpho liquidation's
seized collateral from `token_ledger` — the singleton's `value_delta = +seizedAssets` row — over a
backfilled `CreateMarket` registry).

## Smoke-test (critical — a non-materializing query silently never alerts)

Wait ~60s then poll, up to 3× (30s apart):
```bash
dedaub-monitoring get-logs --id <QUERY_ID>     # proves it RAN; get-alerts --id <QUERY_ID> proves it FIRED
dedaub-monitoring query-status --id <QUERY_ID> # direct materialization health: is_materialized, last_time_run, message
```
- **SUCCESS** → set final frequency (below).
- **TIMEOUT/FAIL** → Timeout Diagnosis; do not move on.
- `query-status` is the most direct check that the query actually materialized — `is_materialized=true`
  with a recent `last_time_run` confirms it; a `message` field surfaces the materialization error if not.

### Timeout Diagnosis (stop at first cause)
1. **Single timeout, first run** — scheduler warm-up. Wait one cycle, recheck.
2. **Simultaneous timeouts across unrelated queries** — platform load spike. Wait 5 min, don't edit SQL.
3. **Consistent (2+ in a row)** — too expensive. The empirical gate should have caught this; re-check
   `run-query` latency, reduce `duration=`/block-range, `write-query`, recheck.
4. **Still slow** — confirm the indexed lead is used (`preprocess-query` to see the expansion; predict
   against §1.1). `topic0` is indexed on most chains (**not Base** — there, lead with `address`), so where indexed the culprit is usually a **missing
   `block_number`/`duration=` bound** (the topic0 lookup still scans all history) or `SELECT *` — not topic0 itself.
5. **Still slow with a tight window** — add `address = '\x…'` to pin the emitter (turns an all-forks
   scan into a single-contract one), or split a multi-event `UNION` into one query per event.
6. **UNION of events** — split into one query per event in the same folder.
7. **State stuck** — `reset-materialization --id <QUERY_ID>` forces a full recompute.

## Finalize
- **Free slot:** `dedaub-monitoring set-config --id <QUERY_ID> --network <NETWORK> --materialize INCREMENTAL --frequency <FREQUENCY> --incrementalization IGNORE` → live.
  **Always re-pass `--materialize INCREMENTAL` (+ `--incrementalization IGNORE`) here.** A bare
  `set-config --frequency <N>` **resets `materialize` to the default `TABLE` and clears
  `incrementalization`** (verified live: it silently parks the alert). Confirm with `get-config` that
  `materialize` is still `INCREMENTAL` after this call — if it flipped to `TABLE`, re-run with the
  explicit flags.
- **At limit (borrowed):** `set-config --id <QUERY_ID> --network <NETWORK> --materialize TABLE` → parked
  (verified but inactive). Tell the user how to activate later (disable another, then re-`enable-alerts`).
- Confirm: `dedaub-monitoring query-metadata --id <QUERY_ID>`.

**Notes:** `disable-alerts` does NOT free a slot (only `set-config --materialize TABLE` does). Fix a
wrong query **in place** via `write-query` — never spawn siblings (no `delete-query`; see macros.md CLI
notes). Non-`ethereum` alerts: confirm via `get-logs` that runs actually fire on `<NETWORK>` on the
first deploy to a new chain.
