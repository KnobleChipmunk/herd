# provenance-citation-cap-mismatch

Status: accepted

## Class

provenance-citation-cap-mismatch (a changed metric cites a source cell whose value can exceed the metric's cap)

Event lines, quoted from the ledger:

- 2026-09-30 project-mera #380-4: Round-1 review found the I5 fence cites a capped uptime_pct for an uncapped raid-wide Debuffs (Enemies) tab cell that displayed 150%; spec-level, so the build stalled for a lead ruling and a regenerated fence, costing a second review round.
- 2026-09-30 project-mera #380-4: The pre-executed build was green (69 touched tests, full suite, 10 killed mutations) yet record_enemy_debuff_uptime_metric claimed a capped 100% input from a Debuffs (Enemies) cell displaying 150%; the plan review never checked whether the cited source can exceed the output cap.

## Proposed change

Add one plan-reviewer check to the plan-reviewer card in
`skill/herd.yaml`: for each changed direct citation or computed input, ask
whether its source tab can display a value outside the output metric's cap or
window, and require one negative-boundary case through that citation. A
90,000 ms raid-wide debuff in a 60,000 ms fight would have caught the I5
fence before dispatch and avoided the fold and second review round. This is a
card paragraph, not a tool change: no script can decide which citations are
semantic boundaries, so the check is prose the reviewer executes.

## Prediction

The next run's plan-review file cites at least one negative-boundary probe
for every changed citation, and the build's round-1 findings contain no
fence-owned cap/window contradictions (no fence-owned findings routed to a
lead ruling in the build).
