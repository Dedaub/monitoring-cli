# Alert Deploy Playbook (alert mode, after Reviewer APPROVES)

**Precondition (from Step 5):** the real target query `/<AlertName>/<QueryName>` is already
**created, written, and passed the empirical gate** (`preprocess-query` + `run-query`). Any VIEW/TABLE
lookup it reads via `{{ref(<id>)}}` is already created and `set-config`'d. So this playbook is mostly
`enable-alerts` + smoke-test + finalize. Run in order; stop and report on any failure.

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
# the alert references it as: FROM {{ref(<LOOKUP_ID>)}}
```

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

## Smoke-test (critical — a non-materializing query silently never alerts)

Wait ~60s then poll, up to 3× (30s apart):
```bash
dedaub-monitoring get-logs --id <QUERY_ID>
```
- **SUCCESS** → set final frequency (below).
- **TIMEOUT/FAIL** → Timeout Diagnosis; do not move on.

### Timeout Diagnosis (stop at first cause)
1. **Single timeout, first run** — scheduler warm-up. Wait one cycle, recheck.
2. **Simultaneous timeouts across unrelated queries** — platform load spike. Wait 5 min, don't edit SQL.
3. **Consistent (2+ in a row)** — too expensive. The empirical gate should have caught this; re-check
   `run-query` latency, reduce `duration=`/block-range, `write-query`, recheck.
4. **Still slow** — confirm the indexed lead is used (`preprocess-query` to see the expansion; predict
   against §1.1). `topic0` is indexed on all chains, so the culprit is usually a **missing
   `block_number`/`duration=` bound** (the topic0 lookup still scans all history) or `SELECT *` — not topic0 itself.
5. **Still slow with a tight window** — add `address = '\x…'` to pin the emitter (turns an all-forks
   scan into a single-contract one), or split a multi-event `UNION` into one query per event.
6. **UNION of events** — split into one query per event in the same folder.
7. **State stuck** — `reset-materialization --id <QUERY_ID>` forces a full recompute.

## Finalize
- **Free slot:** `dedaub-monitoring set-config --id <QUERY_ID> --network <NETWORK> --frequency <FREQUENCY>` → live.
- **At limit (borrowed):** `set-config --id <QUERY_ID> --network <NETWORK> --materialize TABLE` → parked
  (verified but inactive). Tell the user how to activate later (disable another, then re-`enable-alerts`).
- Confirm: `dedaub-monitoring query-metadata --id <QUERY_ID>`.

**Notes:** `disable-alerts` does NOT free a slot (only `set-config --materialize TABLE` does). Fix a
wrong query **in place** via `write-query` — never spawn siblings (no `delete-query`; see macros.md CLI
notes). Non-`ethereum` alerts: confirm via `get-logs` that runs actually fire on `<NETWORK>` on the
first deploy to a new chain.
