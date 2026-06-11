# Review Criteria (semantic — what the Reviewer checks)

The orchestrator already ran the **empirical gate** (SKILL Step 5: `preprocess-query` + `run-query`),
which proved the SQL executes, every SELECT/unique-key/template column exists, literals parse, and
latency shows an indexed lead. **The Reviewer does NOT re-check those mechanics** — reject only on the
semantic faults below.

1. **Detects the right thing.** Query logic matches the alert name/description; threshold present and
   correct if implied; direction (inflow/outflow, >/<) right.
2. **Scope + collision family.** Specific deployment → pinned to emitter `address` (or `to_a`+selector).
   All-forks → topic0 alone only where appropriate. topic0 matches the intended event/family per the
   ref's `## Detection invariants & gotchas` (no silent cross-family collision).
3. **Unique-key semantics.** `tx_hash, log_index` for logs; `tx_hash` for txns. Won't over/under-dedup
   under `--incrementalization IGNORE|UPSERT`.
4. **Reverts** excluded (`status = true` / `committed AND error IS NULL`) unless reverts are intended.
5. **Template** human-readable (decoded values/labels, not raw hex) and every `{{col}}` is in SELECT.
6. **Materialization fit.** History-spanning lookup is TABLE+ref, not a windowed CTE; reusable lookup
   is VIEW+ref; final alert is INCREMENTAL.
7. **Frequency / window** suit urgency and match (`duration=` vs frequency).
8. **Scope discipline (directional — §9).** No silently-added precision filter that narrows recall below
   the literal ask (e.g. pinning callback callers to factory-deployed pairs) — such tightenings must be a
   commented-out option or a user question. Broadening a vague ask (standard admin surface, all forks) is
   fine **only if declared** in the header comment + summary.
9. **Production hygiene.** A deployed alert / materialized query carries **no `ORDER BY`/`LIMIT`**
   (top-N-by-design excepted). Signal identity readable: signature-form macros, or every raw `\x`
   topic0/selector literal annotated with its `-- EventName(types)` / `-- fnName(types)`. Call monitoring
   on `transaction_detail` filters `call_opcode = 'CALL'`, or the header comment says why the
   delegatecall surface is in scope (absence/P13 checks legitimately omit it).

**Style — Suggestions only, never block:** descriptive aliases; rationale present; a suspected
mechanical issue the gate missed → suggest re-running `preprocess-query`/`run-query`, don't block.
