# Reviewer Handoff Shapes (alert mode only)

Two small structures cross the orchestrator → Reviewer boundary, **passed inline** (no files):
the orchestrator pastes the **draft** into the Reviewer's dispatch prompt, and the Reviewer
**returns its verdict as its final message**. Keep these shapes — deviation breaks the handoff.

## Draft — pasted by the orchestrator into the Reviewer prompt

```markdown
# Query Draft: <Alert Name>

## SQL
```sql
-- what it detects + why; data source; scope (specific|all-forks); unique key
WITH lookup AS ( ... )            -- the windowed "incremental piece" (CTE), if any
SELECT ...                        -- final projection; every unique-key & template col present
FROM ...
WHERE ...                         -- indexed lead + block-range/duration; collision guard applied
```

## Alert Template
`<human-readable message with {{col}} placeholders, all present in SELECT>`

## Unique Key
`tx_hash, log_index`   <!-- or `tx_hash` for tx-based -->

## Materialization
`INCREMENTAL`          <!-- alert output is always INCREMENTAL; list any VIEW/TABLE lookup query
                            ids it reads via {{ref(<id>)}}, and whether each is CTE/VIEW/TABLE -->

## Network
`ethereum`             <!-- the chain the alert's run config applies to (enable-alerts --network) -->

## Frequency
`300`

## Rationale
Scope, index lead, why this won't full-scan, decode notes, macro vs raw choices.
```

## Verdict — the Reviewer's final message (its return value)

```markdown
# Review: <Alert Name>

## Verdict
APPROVED            <!-- or REJECTED -->

## Issues
(none)             <!-- or numbered, specific, each a blocker from review-criteria.md -->

## Suggestions
(none)             <!-- or numbered; non-blocking (style, preprocess-query checks) -->
```
