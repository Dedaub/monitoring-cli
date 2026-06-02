# Handoff Document Schemas (alert mode only)

Two small docs cross the inline-Writer → Reviewer boundary. Exact shapes — deviation breaks the
handoff. The bulky `research_brief.md` is gone: the orchestrator greps constants inline and the
patterns doc replaces the schema dump.

## query_<safe_name>.md — written inline by the orchestrator, read by the Reviewer

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

## review_<safe_name>.md — written by the Reviewer subagent

```markdown
# Review: <Alert Name>

## Verdict
APPROVED            <!-- or REJECTED -->

## Issues
(none)             <!-- or numbered, specific, each a blocker from review-criteria.md -->

## Suggestions
(none)             <!-- or numbered; non-blocking (style, preprocess-query checks) -->
```

`<safe_name>` = alert name lowercased, spaces→underscores, special chars removed.
