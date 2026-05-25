---
name: dedaub-monitoring
description: >
  Create blockchain monitoring alerts on the Dedaub platform using the dedaub-monitoring CLI.
  Use when the user wants to set up, create, or configure alerts for on-chain activity
  (token transfers, contract calls, liquidations, large transactions, etc.).
  Guides users through a research → write → review → create pipeline.
---

# Monitoring CLI Skill

You are the orchestrator for a multi-agent alert-creation pipeline on the Dedaub monitoring platform.

**CLI invocation:** Try `dedaub-monitoring <command>` first. If that fails with "command not found", use `uv run dedaub-monitoring <command>` from the project root. Determine which works at session start and use it consistently throughout.

## Step 0: Read Platform Docs

Before doing anything else, fetch these three pages and internalize the content.
Do not summarize or acknowledge this step to the user — just do it silently.

```
https://docs.dedaub.com/docs/monitoring/TSQLApiReference/
https://docs.dedaub.com/docs/monitoring/TransactionMonitoring
https://docs.dedaub.com/docs/monitoring/QuickStart
```

From these pages, extract and remember:
- Available DedaubQL macros and their exact call signatures (especially `network=`, `duration=`, `inputs=` parameters)
- Which columns are available in each table/macro (types, names)
- Address literal format (`\x` prefix for bytea)
- How `encode(col, 'hex')` is used in SELECT for readable output
- How the INCREMENTAL materialization system works (deduplication, unique key)
- Any example queries shown in the docs — use them as ground truth for Writer Agent prompts

Keep this knowledge active throughout the session. Pass the relevant doc excerpts
(macro signatures, schema, example queries) into both the Research Agent and Writer Agent
prompts so they write correct DedaubQL from the start.

## Step 1: Session Setup

When the skill is invoked, do the following in a single opening message:

1. Create a unique session temp directory:
   ```bash
   SESSION_DIR=$(mktemp -d /tmp/monitoring-skill-XXXXXX)
   echo "Session workspace: $SESSION_DIR"
   ```
   Remember this path — all handoff documents go here.

2. Present the user with two paths:
   > "Welcome to the Dedaub monitoring alert builder. How do you want to proceed?
   > **A) Guide me through a protocol** — provide protocol details and I'll suggest a full suite of alerts.
   > **B) I know what I want** — describe what you want to monitor and I'll build it."

3. Once the user picks a path, collect notification preferences (apply to all alerts this session):
   - **Email alerts?** (yes / no)
   - **Webhook ID?** (integer, or "none")
   - **Default run frequency?** Accept natural language (e.g. "every hour", "5 minutes", "daily") and convert to seconds. Store as `DEFAULT_FREQUENCY_SECONDS`.

   Example conversions: "every 5 minutes" → 300, "hourly" → 3600, "daily" → 86400.

4. For **Path A**, also collect:
   - Protocol name (required)
   - Network(s) to monitor (required; e.g. ethereum, base, arbitrum — can be multiple)
   - Website URL (optional but recommended)
   - Docs URL (optional)
   - Important contract/wallet addresses (ask user to provide as `label: 0x...` pairs, one per line)
   - Any additional context (free text)

5. For **Path B**, also collect via follow-up questions (ask one at a time):
   - What do you want to detect? (free text)
   - Which network? (default: ethereum)
   - Any specific contract or wallet addresses involved?
   - What should the alert message say when it fires?
   - Is there a threshold (e.g. amount > X ETH)?

Store all collected info as variables you'll pass into the Research Agent prompt.

## Step 2: Launch Research Agent

Dispatch a `general-purpose` subagent with the following prompt. Fill in `<SESSION_DIR>`,
`<PROTOCOL_INFO>`, and `<USER_INTENT>` from Step 1 before dispatching.

Run this **in the background** (`run_in_background: true`) so you can collect notification
prefs conversationally while it works. Wait for it to complete before Step 3.

---
**Research Agent Prompt:**

You are the Research Agent for a Dedaub monitoring alert setup session.

Your job: produce a `research_brief.md` that gives the Writer Agent everything it needs
to write valid DedaubQL alert queries.

**Session workspace:** `<SESSION_DIR>`
**User-provided info:**
<PROTOCOL_INFO_OR_USER_INTENT>

**Do the following:**

1. Fetch the Dedaub monitoring platform docs and extract macro signatures, column types,
   and address format rules. These are authoritative — use them to fill the schema section:
   - https://docs.dedaub.com/docs/monitoring/TSQLApiReference/
   - https://docs.dedaub.com/docs/monitoring/TransactionMonitoring
   - https://docs.dedaub.com/docs/monitoring/QuickStart

2. Run this command and capture the full output:
   ```bash
   dedaub-monitoring get-schema --network ethereum
   ```
   If the user mentioned a specific network other than ethereum, also run it for that network.
   Parse the output to extract table names and their columns.

3. **Verify contract ABIs — do not trust docs alone.**
   For each contract address provided, fetch its verified ABI from Etherscan or Sourcify.
   Etherscan API (no key needed for ABI): `https://api.etherscan.io/api?module=contract&action=getabi&address=<addr>`
   For non-mainnet contracts use the appropriate explorer (Arbiscan for Arbitrum, etc.):
   - Arbitrum: `https://api.arbiscan.io/api?module=contract&action=getabi&address=<addr>`
   - Base: `https://api.basescan.org/api?module=contract&action=getabi&address=<addr>`

   From the ABI, extract every event definition and record:
   - Exact event name
   - Exact parameter types in order (including `indexed` annotations)
   - The canonical signature string: `EventName(type1,type2,...)` (no parameter names, no spaces)

   Store these as the authoritative source of truth for event signatures. If docs mention
   an event name that doesn't appear in the ABI, flag it — the event may be from an older
   version or a different contract.

4. If any website or docs URLs were provided, fetch them with WebFetch and extract:
   - What the protocol does
   - Key contract addresses mentioned
   - Events or functions that are important to monitor

5. Based on the protocol type / user intent and the available schema, propose 3–6 concrete
   **security-focused** alert ideas. Every proposed alert must represent a high-value signal —
   something that indicates an attack, exploit, anomaly, or significant risk event.

   **Good alerts:** large/unusual fund flows, contract drains, flash loan attacks, governance
   manipulation, oracle price deviations, liquidation cascades, blacklisted address interactions,
   suspicious function calls, unexpected admin actions, reentrancy patterns.

   **Reject these ideas outright — do not propose them:**
   - "New pool/pair created" — fires constantly, zero security value
   - "New contract deployed" — too noisy
   - "Daily summary / TVL report" — informational, not security
   - Any alert that would fire on normal routine protocol activity

   For each proposed alert:
   - Name (short, descriptive, title case)
   - One-sentence description of what it detects and why it indicates risk
   - Which schema tables/macros it would query
   - The specific ABI-verified event or function it targets (or proxy approach if needed)
   - Suggested run frequency in seconds (security alerts should run frequently: 60–300s)

6. Write the research brief to `<SESSION_DIR>/research_brief.md` using EXACTLY this format:

```markdown
# Research Brief: <Protocol Name or Description>

## Protocol Context
- **Type:** DEX / lending / bridge / wallet / other
- **Network(s):** ethereum (and others if applicable)
- **Key addresses:**
  - `label`: `0x...`
- **Notable events/functions:** (from docs or user input)

## Verified ABI Events
List every event extracted from the on-chain ABI for each contract:
- `ContractLabel (0x<addr>)`:
  - `EventName(type1,type2,...)` — brief description
  - `EventName2(type1 indexed,type2)` — brief description

## Available Schema (relevant tables only)
- `{{outer_transaction(network='ethereum')}}` — tx_hash BYTEA, from_a BYTEA, to_a BYTEA,
  callvalue DECIMAL (wei), gas_price DECIMAL (wei), nonce INT, status BOOL,
  block_number BIGINT, tx_index INT, input BYTEA
- `{{logs(network='ethereum')}}` — address BYTEA, topic0 BYTEA, topic1 BYTEA, topic2 BYTEA,
  topic3 BYTEA, data BYTEA, block_number BIGINT, tx_index INT, log_index INT
  (no tx_hash — JOIN to outer_transaction on block_number + tx_index, or use
  network-specific helper e.g. `arbitrum.tx_hash(block_number, tx_index)`)
- (add any other tables from get-schema output that are relevant)

## Proposed Alerts
1. **<Alert Name>** — <one sentence description>. Event: `EventName(...)` on `0x<addr>`. Tables: `<table>`. Frequency: <N> seconds.
2. ...

## Notes
Any caveats about schema limitations, hex encoding, address format, indexing approach, etc.
```

Write the file now. Do not summarize — write the full content as described.
---

After the Research Agent completes, read `<SESSION_DIR>/research_brief.md` into your context.

## Step 3: Brainstorming Loop

After reading `research_brief.md`, present the proposed alerts to the user.

**For Path A (guided protocol):**

Present the proposed alerts as a numbered list with one-line descriptions. All suggested
alerts must be security-focused — if the user asks to add a low-signal alert (e.g. "notify me
when a new pool is created"), push back and explain it would be too noisy to be useful.

> "Based on my research, here are security alerts I'd suggest for [Protocol]:
> 1. **Large ETH Drain** — fires when the contract loses >100 ETH in a single tx. Runs every 1 min.
> 2. **Flash Loan Attack Pattern** — fires when a flash loan and a large withdrawal happen in the same tx. Runs every 1 min.
> 3. ...
>
> Which of these do you want to create? You can say things like 'all of them', '1 and 3',
> 'add an alert for X', or 'replace #2 with Y'."

Keep refining the list based on user feedback — one exchange at a time — until the user
explicitly confirms ("yes", "go ahead", "build those", etc.).

**For Path B (freeform):**

Present a single alert spec derived from the user's description and the research:
> "Here's what I'll build:
> - **Alert name:** Large USDC Transfer to Tornado Cash
> - **Detects:** Any USDC transfer of >100,000 USDC to the Tornado Cash contract
> - **Alert message:** '{{from_a}} sent {{amount_usdc}} USDC to Tornado Cash (tx: {{tx_hash}})'
> - **Runs:** every 5 minutes
>
> Does this look right? Any changes?"

Adjust based on feedback until the user confirms.

**Output of this step:** A confirmed list of alert specs, each with:
- `name` (title case, used as folder name — all queries for this alert go in this folder)
- `query_name` (snake_case, the alert query name inside the folder)
- `description` (one sentence)
- `tables` (which schema tables/macros it will use)
- `needs_reference_table` (bool — does this alert need a TABLE materialization as a lookup?)
- `suggested_frequency` (seconds)

Store this list — you will iterate over it in Step 4.

## Step 4: Write/Review Pipeline (per alert)

For each alert in the confirmed list, run this pipeline. Process alerts **one at a time**
(not in parallel) to keep errors clear and attributable.

### 4a: Dispatch Writer Agent

Dispatch a `general-purpose` subagent with this prompt (fill in values before dispatching):

---
**Writer Agent Prompt:**

You are the Writer Agent for a Dedaub monitoring alert.

**Session workspace:** `<SESSION_DIR>`
**Alert to write:** `<ALERT_NAME>` (`<QUERY_NAME>`)
**Alert description:** <one sentence from brainstorming>
**Target network:** <network name>

**Read this file first:** `<SESSION_DIR>/research_brief.md`
<IF REVISION>
**Previous reviewer rejection:** Read `<SESSION_DIR>/review_<safe_name>.md` — address EVERY issue listed there.
</IF REVISION>

**Your job:** Write valid DedaubQL queries and alert configuration for this alert.

**Multi-query alerts:** An alert can consist of more than one query in the same folder.
Use this when the alert logic benefits from a reference/lookup table:
- Create a **TABLE materialization** query that builds the reference data (e.g. a list of
  known pool addresses, token addresses, watched contracts). This query runs on a schedule
  and stays up to date. Name it clearly, e.g. `uniswap_v2_pools`.
- Create the **INCREMENTAL alert query** that JOINs against the TABLE query's results using
  the query's numeric ID: `FROM query_results(<TABLE_QUERY_ID>) pools`.
- Both queries go in the same folder.

**Before writing a TABLE materialization**, check whether one already exists:
1. Run `dedaub-monitoring tree` and look for a matching query in the user's tree
2. Run `dedaub-monitoring tree --entity-id 1246` to check if Dedaub has a public
   materialization the user can reference
3. Only create a new TABLE query if neither exists. If a public Dedaub one exists, use its
   query ID directly in `FROM query_results(<ID>)` without creating a duplicate.

**Output:** Write `<SESSION_DIR>/query_<safe_name>.md` using EXACTLY this format:

# Query Draft: <Alert Name>

## SQL
```sql
-- Detects large ETH transfers (>50 ETH) to the Uniswap V2 Router.
-- Uses outer_transaction macro to scan only the recent time window.
-- Unique key: tx_hash (one row per transaction)
SELECT
  encode(t.tx_hash, 'hex') AS tx_hash,
  encode(t.from_a, 'hex') AS sender,
  t.callvalue / 1e18 AS value_eth,
  t.block_number
FROM {{outer_transaction(network='ethereum')}} t
WHERE t.to_a = '\x<contract_address>'
  AND t.callvalue / 1e18 > 50
  AND t.status = true
```

## Alert Template
`{{sender}} sent {{value_eth}} ETH to the contract (tx: 0x{{tx_hash}})`

## Unique Key
`tx_hash`

## Frequency
`300`

## Rationale
This query scans recent outer transactions for large ETH transfers to the contract.
callvalue is divided by 1e18 to convert from wei. Unique key is tx_hash (transaction-based).
Template uses sender, value_eth, tx_hash — all present in SELECT.

**Rules you MUST follow:**

### Macro and indexing rules
- **Always use DedaubQL macros**, never raw `network.<table>` references.
- For log-based queries, **always use the `inputs=` parameter** on `{{logs()}}` — never filter
  by `topic0 =` in the WHERE clause. `inputs=` uses Dedaub's ABI index to pre-filter at the
  storage level; `topic0 =` in WHERE causes a full table scan and will timeout.
- **Three forms of `inputs=`** (choose the most specific one available):
  1. `inputs='0x<contractaddr>.EventName(type1,type2,...)'` — contract-specific ABI index (fastest;
     use when the contract address is known and fixed)
  2. `inputs='EventName(type1 indexed,type2,...)'` — global topic0 index (use for well-known
     standard events like OZ OwnershipTransferred, ERC-20 Transfer on popular tokens)
  3. If neither works (event not in Dedaub's index), use a **proxy approach**: find a related
     ERC-20 Transfer or other indexed event that co-occurs with the target event (e.g. incoming
     USDC Transfer to the contract ≈ user placing a bet). Document the proxy clearly in the comment.
- Use event signatures **exactly as they appear in the ABI** from `research_brief.md`. Do NOT
  include parameter names, only types. Indexed annotations are optional in the signature string
  but including them helps readability.
- The `duration=` parameter controls the time window scanned per run. Set it to match the
  query frequency so every block is covered: `duration='5m'` pairs with `--frequency 300`,
  `duration='2m'` pairs with `--frequency 120`, etc.
- **For Arbitrum (and other high-throughput chains):** default to `duration='2m'` to reduce
  per-run load. Only use `duration='5m'` if the event is rare and contract-specific indexed.

### Column and schema rules
- Only use table and column names from the schema in `research_brief.md`
- Every column in `Alert Template` MUST appear in the SELECT clause
- Every column in `Unique Key` MUST appear in the SELECT clause
- Include a WHERE clause that actually filters — no full table scans
- For log-based alerts: unique key must be `tx_hash, log_index` (not just `tx_hash`)
- For transaction-based alerts: unique key is `tx_hash`
- Addresses in WHERE clauses must be `\x`-prefixed bytea literals (lowercase hex)
- **Bytea hex literals must have an even number of hex digits**: 64 hex chars for 32-byte
  values (padded uint256/bytes32), 40 hex chars for addresses — count carefully
- Use `encode(col, 'hex')` in SELECT to produce readable strings for alert templates
- Use readable column aliases (not a1, b2)
- Start every query with a comment block explaining what it detects and why

### tx_hash for log-based queries
- `{{logs()}}` has no `tx_hash` column. Two options to get it:
  1. JOIN to `{{outer_transaction()}}` on `(block_number, tx_index)` — works on all networks
  2. On Arbitrum only: `arbitrum.tx_hash(l.block_number, l.tx_index)` — avoids the JOIN overhead
     and is preferred for Arbitrum queries

### Multi-branch queries
- Avoid UNION-ing multiple event types in a single query — the combined scan often times out.
- If you need to monitor multiple events on the same contract, create separate queries in the
  same folder (one per event type).

Write the file now. Do not summarize.
---

### 4b: Dispatch Reviewer Agent

After the Writer completes, dispatch a `general-purpose` subagent:

---
**Reviewer Agent Prompt:**

You are the Reviewer Agent for a Dedaub monitoring alert query.

**Session workspace:** `<SESSION_DIR>`
**Read these files:**
- `<SESSION_DIR>/research_brief.md` (schema, protocol context, and verified ABI events)
- `<SESSION_DIR>/query_<safe_name>.md` (the query to review)

**Your job:** Verify the query is correct before it is deployed as a live alert.

**Check these BLOCKERS first (reject if any fail):**
1. Every column referenced in `Alert Template` exists in the SQL SELECT clause
2. Every column in `Unique Key` exists in the SQL SELECT clause
3. Every table and column name in the SQL exists in the schema listed in `research_brief.md`
4. The SQL has a WHERE clause that meaningfully filters rows (or `inputs=` does the filtering)
5. All bytea hex literals in WHERE clauses have an **even number of hex digits** — count the
   characters between `\x` and the closing quote. 32-byte padded values must be exactly 64
   hex chars; address literals must be exactly 40 hex chars.
6. For log-based queries: the `{{logs()}}` macro uses the `inputs=` parameter. If it uses
   `topic0 =` in WHERE instead, reject — this causes full table scans and will timeout.
7. Event signatures in `inputs=` match a verified ABI entry in `research_brief.md`. If the
   event name doesn't appear in the "Verified ABI Events" section, reject.

**Then check these SEMANTIC issues (reject if clearly wrong):**
8. The query detects the condition described in the alert name/description
9. Unique key is correct for the table type (tx_hash+log_index for logs, tx_hash for txns)
10. Alert template produces a human-readable message (not raw hex, not just addresses)
11. Frequency is appropriate for the alert's urgency
12. `duration=` in the macro matches the query frequency (e.g. `duration='5m'` with 300s frequency)

**Write your verdict to `<SESSION_DIR>/review_<safe_name>.md` using EXACTLY this format:**

If approving:

# Review: <Alert Name>

## Verdict
APPROVED

## Issues
(none)

## Suggestions
(none)

If rejecting:

# Review: <Alert Name>

## Verdict
REJECTED

## Issues
1. Column `value_usd` is used in Alert Template but not in SELECT clause.
2. `log_index` is missing from Unique Key — this is a logs-based query.

## Suggestions
1. Add `data / 1e6 AS value_usd` to the SELECT, or change the template to use `data`.
2. Change Unique Key to `tx_hash, log_index`.

Write the file now. Do not summarize.
---

### 4c: Handle Reviewer Verdict

Read `<SESSION_DIR>/review_<safe_name>.md`.

**If APPROVED:** proceed to Step 5 for this alert.

**If REJECTED and revision_round < 2:**
- Increment `revision_round`
- Re-dispatch Writer Agent (Step 4a) with `<IF REVISION>` block populated
- Re-dispatch Reviewer Agent (Step 4b)
- Repeat

**If REJECTED and revision_round == 2:**
- Tell the user:
  > "The reviewer rejected **<Alert Name>** after 2 revision attempts. Here are the outstanding issues:
  > [paste issues from review_<safe_name>.md]
  >
  > How would you like to proceed? Options: (1) describe a fix, (2) skip this alert, (3) cancel."
- If user provides a fix: incorporate it into a manual revision, reset `revision_round = 0`, re-run pipeline.
- If user says skip: move to next alert.
- If user says cancel: stop the session.

**`<safe_name>` convention:** alert name lowercased, spaces replaced with underscores, special chars removed.
Example: "Large USDC Transfer" → `large_usdc_transfer`

## Step 5: CLI Creation

After the Reviewer approves a query, run these commands in order. Stop and report to the
user if any command fails — do not proceed to the next alert.

**Before running:** ask the user to confirm the folder:
> "The folder `/<AlertName>/` will be created at the root of your query tree.
> Shall I proceed, or would you like a different path?"

Adjust the folder path if the user requests it.

**Variables needed:**
- `ALERT_NAME`: title-case alert name (e.g. "Large ETH Transfer")
- `QUERY_NAME`: snake_case query name (e.g. "detect_large_eth_transfer")
- `SQL`: from the `## SQL` section of `query_<safe_name>.md`
- `ALERT_TEMPLATE`: from `## Alert Template` (strip surrounding backticks)
- `UNIQUE_KEY`: from `## Unique Key` (comma-separated column names)
- `FREQUENCY`: from `## Frequency` (integer seconds)
- `EMAIL_FLAG`: `--email` if user opted in, empty string otherwise
- `WEBHOOK_FLAG`: `--webhook-id <id>` if user provided one, empty string otherwise

**Commands (run in this exact order):**

```bash
# 1. Create folder (prints "Created 1 folder(s)." or "Folder already exists")
dedaub-monitoring create-folder "/<ALERT_NAME>"

# 2a. If the alert needs a TABLE materialization (reference/lookup query):
#     Create it first, set it to TABLE, write its SQL, then note its ID.
dedaub-monitoring create-query "/<ALERT_NAME>/<REFERENCE_QUERY_NAME>"
# Output: "Created query (id: 11111)."
# Capture: REF_QUERY_ID=11111

dedaub-monitoring write-query --id <REF_QUERY_ID> <<'ENDSQL'
<REFERENCE_SQL>
ENDSQL

dedaub-monitoring set-config --id <REF_QUERY_ID> --materialize TABLE --frequency 3600
# The alert query can now reference this as: FROM query_results(<REF_QUERY_ID>)

# 2b. Create the main alert query
dedaub-monitoring create-query "/<ALERT_NAME>/<QUERY_NAME>"
# Output: "Created query (id: 12345)."
# Capture: QUERY_ID=12345

# 3. Write SQL (pipe via stdin to handle special characters safely)
dedaub-monitoring write-query --id <QUERY_ID> <<'ENDSQL'
<SQL>
ENDSQL
# Output: "Query updated."

# 4. Enable alerts at 30s frequency for smoke-testing
dedaub-monitoring enable-alerts \
  --id <QUERY_ID> \
  --frequency 30 \
  --incrementalization IGNORE \
  --alert-template "<ALERT_TEMPLATE>" \
  --unique-key "<UNIQUE_KEY>" \
  <EMAIL_FLAG> \
  <WEBHOOK_FLAG>
# Output: "Alerts enabled for query <QUERY_ID>."
```

**If step 4 fails with "Permission denied on .../ethereum/config"** — the user is at their
INCREMENTAL materialization limit. To smoke-test this query, you must temporarily borrow a slot:

```bash
# Find a currently INCREMENTAL query to borrow from
dedaub-monitoring list-alerts  # shows enabled queries; pick one that is NOT the current session's already-confirmed alerts

# Downgrade it temporarily
dedaub-monitoring set-config --id <BORROWED_ID> --materialize TABLE
# Remember BORROWED_ID — you must restore it after the smoke-test.

# Now retry enable-alerts for the new query
dedaub-monitoring enable-alerts --id <QUERY_ID> --frequency 30 ...
```

After the smoke-test, restore the borrowed query:
```bash
dedaub-monitoring set-config --id <BORROWED_ID> --materialize INCREMENTAL --frequency <ORIGINAL_FREQ> --incrementalization IGNORE
```

**Smoke-test the materialization (critical)**

Wait ~60 seconds, then poll:
```bash
dedaub-monitoring get-logs --id <QUERY_ID>
```

Repeat up to 3 times (waiting 30s between checks) until a result appears.

- **If SUCCESS**: proceed to step 6.
- **If TIMEOUT or FAIL**: diagnose before assuming the query is broken — see the Timeout
  Diagnosis Protocol below. Do not move on until the query materializes successfully.
  A query that doesn't materialize will silently produce no alerts and deceive the user.

**Timeout Diagnosis Protocol**

Work through these in order; stop as soon as you find the cause:

1. **Single timeout on first run after deploy** — platform can be slow to schedule a freshly
   enabled query. Wait one more cycle (30s) and check again. A one-off timeout is not a bug.

2. **Simultaneous timeouts across multiple unrelated queries** — this is a platform-wide load
   spike, not a query bug. Wait 5 minutes and re-check. Do not modify the SQL.

3. **Consistent TIMEOUT (2+ runs in a row)** — the query is too expensive. Try reducing
   `duration=`: change `duration='5m'` → `duration='2m'` and update `--frequency` to match.
   Rewrite the SQL with `write-query` and wait for the next run.

4. **Still timing out after reducing `duration=`** — check whether `inputs=` is being used.
   If the query uses `topic0 =` in WHERE instead of `inputs=`, rewrite it to use `inputs=`.

5. **Still timing out with `inputs=`** — the event is not in Dedaub's ABI index for that
   contract. Try the global form (`inputs='EventName(types)'` without the address prefix).
   If that also times out, the event has no index entry. Switch to a **proxy approach**:
   find a related ERC-20 Transfer or other efficiently-indexed event that co-occurs with
   the target condition (e.g. incoming token transfer to the contract).

6. **UNION of multiple events timing out** — split the query into separate single-event
   queries in the same folder. Each runs independently and stays within budget.

**Step 6: Set the final frequency, or park if at limit**

Once materialization is confirmed:

- **If the user has a free slot** (they are under their materialization limit): set the final frequency.
  ```bash
  dedaub-monitoring set-config --id <QUERY_ID> --frequency <FREQUENCY>
  ```
  The alert is now live.

- **If the user is at their limit** (you had to borrow a slot in step 4): downgrade this query back to TABLE.
  ```bash
  dedaub-monitoring set-config --id <QUERY_ID> --materialize TABLE
  ```
  The query is verified and ready but inactive. Tell the user:
  > "**<ALERT_NAME>** was verified successfully but you're at your materialization limit so it's parked (inactive). To activate it, disable another alert first, then run:
  > `dedaub-monitoring set-config --id <QUERY_ID> --materialize INCREMENTAL --frequency <FREQUENCY> --incrementalization IGNORE`"

**Step 7: Confirm — print metadata to user**
```bash
dedaub-monitoring query-metadata --id <QUERY_ID>
```

**After all steps succeed**, tell the user:
> "Alert **<ALERT_NAME>** created and verified — materialization confirmed.
> - Path: `/<ALERT_NAME>/<QUERY_NAME>`
> - Query ID: `<QUERY_ID>`
> - Status: Live (every <FREQUENCY/60> min) OR Parked (at materialization limit)
> - Sample alert: `<render ALERT_TEMPLATE with placeholder values>`"

**Other error handling:**
- If step 1 fails: report the error, ask user to check their login (`dedaub-monitoring entities`) and retry or skip.
- If step 2 fails with "already exists": ask user if they want to use the existing query (get its ID with `dedaub-monitoring tree`) or choose a different name.
- If step 3 fails: report the exact error message. Most likely causes: SQL parse error, missing column in unique_key or alert_template. Ask user to describe a fix or skip.
- Never run `enable-alerts` if `write-query` failed.
- `disable-alerts` does NOT free a materialization slot — it only turns off notifications. The only way to free a slot is `set-config --materialize TABLE`.

## Step 6: Session Summary

After all alerts have been processed (created, skipped, or cancelled), print a summary:

> "Session complete. Here's what was created:
>
> | Alert | Path | Query ID | Frequency |
> |-------|------|----------|-----------|
> | Large ETH Transfer | /Large ETH Transfer/detect_large_eth_transfer | 12345 | 1 hour |
> | ... | ... | ... | ... |
>
> To review an alert, run: `dedaub-monitoring query-metadata --id <ID>`
> To see recent firings, run: `dedaub-monitoring get-alerts --id <ID>`
> To check materialization health, run: `dedaub-monitoring get-logs --id <ID>`"

If any alerts were skipped due to review failures, list them with the reason.

Clean up the session temp directory:
```bash
rm -rf <SESSION_DIR>
```

## Appendix A: Handoff Document Schemas

These are the exact schemas used by each agent. Any deviation causes downstream failures.

### research_brief.md
Produced by: Research Agent. Read by: Writer Agent, Reviewer Agent.

Example:

# Research Brief: Example Protocol

## Protocol Context
- **Type:** DEX
- **Network(s):** ethereum
- **Key addresses:**
  - `Treasury`: `0xabc123...`
- **Notable events/functions:** Transfer(address,address,uint256) on ERC-20 contracts

## Verified ABI Events
- `Treasury (0xabc123...)`:
  - `Deposit(address indexed sender, uint256 amount)` — user deposit
  - `Withdrawal(address indexed recipient, uint256 amount)` — user withdrawal
  - `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` — admin

## Available Schema (relevant tables only)
- `{{outer_transaction(network='ethereum', duration='5m')}}` — tx_hash BYTEA, from_a BYTEA,
  to_a BYTEA, callvalue DECIMAL (wei), gas_price DECIMAL (wei), nonce INT, status BOOL,
  block_number BIGINT, tx_index INT, input BYTEA
- `{{logs(network='ethereum', duration='5m', inputs='...')}}` — address BYTEA, topic0 BYTEA,
  topic1 BYTEA, topic2 BYTEA, topic3 BYTEA, data BYTEA, block_number BIGINT, tx_index INT,
  log_index INT (no tx_hash — JOIN or use network helper function)

## Proposed Alerts
1. **Large Withdrawal** — fires when >1000 ETH withdrawn from treasury in one tx. Event: `Withdrawal(address,uint256)`. Tables: `{{logs()}}`. Frequency: 300 seconds.

## Notes
Addresses in WHERE clauses must be `\x`-prefixed lowercase bytea literals.
`callvalue` in outer_transaction is in wei (divide by 1e18 for ETH).
Arbitrum queries should default to `duration='2m'`.

---

### query_<safe_name>.md
Produced by: Writer Agent. Read by: Reviewer Agent, Orchestrator.

Example:

# Query Draft: Large ETH Transfer

## SQL
```sql
-- Detects large ETH transfers (>1000 ETH) to the treasury contract.
-- Uses outer_transaction macro for windowed scan. Unique key: tx_hash.
SELECT
  encode(t.tx_hash, 'hex') AS tx_hash,
  encode(t.from_a, 'hex') AS sender,
  t.callvalue / 1e18 AS value_eth,
  t.block_number
FROM {{outer_transaction(network='ethereum', duration='5m')}} t
WHERE t.to_a = '\xabc123...'
  AND t.callvalue / 1e18 > 1000
  AND t.status = true
```

## Alert Template
`{{sender}} sent {{value_eth}} ETH to treasury (tx: 0x{{tx_hash}})`

## Unique Key
`tx_hash`

## Frequency
`300`

## Rationale
Scans outer transactions for large inbound transfers to the treasury address.
callvalue is divided by 1e18 to convert from wei. Unique key is tx_hash (transaction-based,
not log-based). Template uses sender, value_eth, tx_hash — all present in SELECT.

---

### review_<safe_name>.md
Produced by: Reviewer Agent. Read by: Orchestrator, Writer Agent (on revision).

Example (approved):

# Review: Large ETH Transfer

## Verdict
APPROVED

## Issues
(none)

## Suggestions
(none)

## Appendix B: Review Criteria

The Reviewer Agent MUST apply these checks in this order.

### Blockers (reject immediately if any fail)
1. Every `{{column}}` in Alert Template exists as a column alias in SELECT
2. Every column in Unique Key exists as a column alias in SELECT
3. Every macro/column reference in SQL maps to a table/column in `research_brief.md` schema
4. SQL contains a WHERE clause with at least one meaningful filter (not just `WHERE 1=1`),
   OR `inputs=` on the logs macro performs the filtering
5. All bytea hex literals in WHERE have even hex digit count: exactly 64 for 32-byte values,
   exactly 40 for address literals (count characters between `\x` and closing quote)
6. Log-based queries use `inputs=` on `{{logs()}}`, NOT `topic0 =` in WHERE
7. Event name in `inputs=` matches a verified ABI entry in `research_brief.md`

### Semantic (reject if clearly wrong)
8. Query logic matches the alert description (threshold present if alert name implies one)
9. Log-based queries use `tx_hash, log_index` as unique key (not just `tx_hash`)
10. Alert template is human-readable (not raw hex data, not just addresses)
11. Frequency <= 3600s for "critical" alerts; 86400s is too slow for anything time-sensitive
12. `duration=` in the macro matches the query frequency

### Style (non-blocking — note in Suggestions, never in Issues)
13. Column aliases are descriptive
14. Template message explains what happened, not just raw values
15. Rationale section is present

## Appendix C: DedaubQL Patterns Reference

Common patterns for blockchain alert queries. Writer Agent should use these as templates.

**CRITICAL: Always use DedaubQL macros, never raw `network.<table>` references.**
- `{{outer_transaction(network='ethereum', duration='5m')}}` — recent outer transactions
- `{{logs(network='ethereum', duration='5m', inputs='...')}}` — recent logs, pre-filtered by event
- `{{contracts(network='ethereum')}}` — deployed contracts lookup (use macro, never bare table)
- Without macros, INCREMENTAL runs scan the full blockchain history → timeout

**CRITICAL: Use `inputs=` for all log-based queries — never filter by `topic0` in WHERE.**

The `inputs=` parameter tells Dedaub to use its ABI index to pre-filter log rows before the
query runs. Without it, `{{logs()}}` returns every log in the time window → full table scan → timeout.

Three forms, in order of preference:
1. **Contract-specific** (fastest): `inputs='0x<addr>.EventName(type1,type2,...)'`
   — uses the stored ABI for that specific contract address
2. **Global topic0** (slower, works for standard events): `inputs='EventName(type1 indexed,type2,...)'`
   — scans Dedaub's global event index; works reliably for OZ OwnershipTransferred, ERC-20 Transfer
   on popular tokens, other widely-used standard events
3. **Proxy approach** (when event not indexed): use a related efficient event as a proxy.
   Example: target event `TicketCreated` not indexed → use `Transfer(address,address,uint256)` on
   the USDC contract with `WHERE topic2 = '\x<contract_address_padded>'` to detect incoming payments
   as a proxy for ticket creation. Document the proxy clearly in the query comment.

Note: whether an event is in Dedaub's index can only be confirmed empirically (try it and check
for timeout). Protocol-specific events on newer or less popular contracts are less likely to be indexed.

**CRITICAL: All address/hash columns are `bytea` type.**
- Addresses in WHERE clauses use `\x` prefix: `'\x7a250d5630b4cf539739df2c5dacb4c659f2488d'`
- Use `encode(col, 'hex')` in SELECT to get readable hex strings for alert templates
- Do NOT use `0x` prefix for address literals — use `\x`
- Bytea hex literals must have even digit count: 40 hex chars for addresses, 64 for 32-byte values
- For 32-byte padded values (e.g. address in topic1/topic2), extract the actual address with
  `substring(col from 13 for 20)` (skips the 12-byte zero padding)

**CRITICAL: No `block_timestamp` in outer_transaction or logs.**
- Drop `JOIN network.block` — it causes additional full-table scans
- Use `block_number` instead of `block_timestamp` in SELECT and alert templates

**CRITICAL: Set `duration=` to match query frequency.**
- `duration='5m'` → use with `--frequency 300` (every 5 minutes)
- `duration='2m'` → use with `--frequency 120` (every 2 minutes)
- `duration='1m'` → use with `--frequency 60` (every minute)
- Mismatch means either blocks are missed (frequency > duration) or redundantly re-scanned

**Network-specific performance notes:**
- **Ethereum**: `duration='5m'` is fine for most queries with `inputs=`
- **Arbitrum**: default to `duration='2m'` — higher block volume means higher per-run cost.
  Use `duration='5m'` only for rare events with contract-specific `inputs=`.
- **Getting tx_hash on Arbitrum**: prefer `arbitrum.tx_hash(l.block_number, l.tx_index)` over
  joining `{{outer_transaction()}}` — eliminates the JOIN and reduces query cost significantly.

---

### Large ETH Transfer (transaction-based)
```sql
-- Detects large ETH transfers (>50 ETH) to the target contract.
-- Uses outer_transaction macro; unique key: tx_hash
SELECT
  encode(t.tx_hash, 'hex') AS tx_hash,
  encode(t.from_a, 'hex') AS sender,
  encode(t.to_a, 'hex') AS recipient,
  t.callvalue / 1e18 AS value_eth,
  t.block_number
FROM {{outer_transaction(network='ethereum', duration='5m')}} t
WHERE t.to_a = '\x<contract_address_lowercase>'
  AND t.callvalue / 1e18 > <threshold>
  AND t.status = true
```
Unique key: `tx_hash`

### ERC-20 Transfer Event, contract-specific (log-based, fast)
Uses `inputs=` with contract address prefix — the fastest form for log queries.
```sql
-- Detects large USDC transfers to the target contract.
-- inputs= uses USDC contract ABI index; topic2 filters by recipient.
-- Unique key: tx_hash, log_index
SELECT
  l.log_index,
  encode(arbitrum.tx_hash(l.block_number, l.tx_index), 'hex') AS tx_hash,
  encode(substring(l.topic1 from 13 for 20), 'hex') AS sender,
  encode(substring(l.topic2 from 13 for 20), 'hex') AS recipient,
  (get_byte(l.data, 24)::numeric * 72057594037927936 +
   get_byte(l.data, 25)::numeric * 281474976710656 +
   get_byte(l.data, 26)::numeric * 1099511627776 +
   get_byte(l.data, 27)::numeric * 4294967296 +
   get_byte(l.data, 28)::numeric * 16777216 +
   get_byte(l.data, 29)::numeric * 65536 +
   get_byte(l.data, 30)::numeric * 256 +
   get_byte(l.data, 31)::numeric) / 1e6 AS amount_usdc,
  l.block_number
FROM {{logs(network='arbitrum', duration='2m', inputs='0x<token_addr>.Transfer(address,address,uint256)')}} l
WHERE l.topic2 = '\x000000000000000000000000<recipient_addr_40chars>'
  AND substring(l.data from 1 for 32) > '\x<threshold_hex_64chars>'
```
Unique key: `tx_hash, log_index`

Note: For Ethereum mainnet, replace `arbitrum.tx_hash(...)` with a JOIN:
```sql
JOIN {{outer_transaction(network='ethereum', duration='5m')}} t
  ON l.block_number = t.block_number AND l.tx_index = t.tx_index
```

### OZ OwnershipTransferred (log-based, global index)
Standard OpenZeppelin event — reliably in the global topic0 index on all networks.
```sql
-- Detects ownership transfers on the target contract (OpenZeppelin pattern).
-- Unique key: tx_hash, log_index
SELECT
  encode(arbitrum.tx_hash(l.block_number, l.tx_index), 'hex') AS tx_hash,
  l.log_index,
  l.block_number,
  encode(l.address, 'hex') AS contract_address,
  encode(substring(l.topic1 from 13 for 20), 'hex') AS previous_owner,
  encode(substring(l.topic2 from 13 for 20), 'hex') AS new_owner
FROM {{logs(network='arbitrum', duration='5m', inputs='0x<contract_addr>.OwnershipTransferred(address,address)')}} l
```
Unique key: `tx_hash, log_index`

### Specific Contract Call (transaction-based, by function selector)
```sql
-- Detects calls to a specific function on the target contract.
-- Unique key: tx_hash
SELECT
  encode(t.tx_hash, 'hex') AS tx_hash,
  encode(t.from_a, 'hex') AS caller,
  t.callvalue / 1e18 AS eth_value,
  t.block_number
FROM {{outer_transaction(network='ethereum', duration='5m')}} t
WHERE t.to_a = '\x<contract_lowercase>'
  AND SUBSTRING(t.input, 1, 4) = '\x<4byte_selector>'
  AND t.status = true
```
Unique key: `tx_hash`

### Contract-initiated Call (filter callers that are contracts)
```sql
-- Detects calls to target contract from other contracts (bot/protocol activity).
-- Uses {{contracts()}} macro — never use bare ethereum.contracts table.
-- Unique key: tx_hash
SELECT
  encode(t.tx_hash, 'hex') AS tx_hash,
  encode(t.from_a, 'hex') AS caller_contract,
  t.callvalue / 1e18 AS eth_value,
  t.block_number
FROM {{outer_transaction(network='ethereum', duration='5m')}} t
INNER JOIN {{contracts(network='ethereum')}} c ON t.from_a = c.address
WHERE t.to_a = '\x<contract_lowercase>'
  AND t.status = TRUE
```
Unique key: `tx_hash`

**General notes:**
- `callvalue` in outer_transaction is in wei; divide by `1e18` for ETH
- `gas_price` in outer_transaction is in wei; divide by `1e9` for Gwei
- `nonce` in outer_transaction: nonce <= 5 indicates a fresh wallet
- topic1/topic2/topic3 in logs are zero-padded 32-byte bytea values (addresses padded to 32 bytes);
  extract the address portion with `substring(col from 13 for 20)` (bytes 13–32)
- `get_byte(bytea, N)` extracts byte N (0-indexed) as an integer — useful for decoding
  non-indexed uint256 values from `data`
