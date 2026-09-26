# Proposal: skill gives conflicting plan-reviewer execution rules

Status: applied https://github.com/KnobleChipmunk/herd/pull/25 2026-09-26

## Class

skill-contradicts-itself — skill gives conflicting plan-reviewer execution rules

Events (friction ledger):
- 2026-09-25: "The tier table says the plan reviewer never re-executes, while 'the full suite runs once per build' lists it among roles that run touched tests; the #460 review had to infer the boundary itself."
- 2026-09-26: "The tier table and reviewer brief say the plan reviewer never re-executes, while the 'full suite runs once per build' paragraph lists it among roles that run touched tests; the reviewer had to infer the boundary."
- 2026-09-26: "The same execution-boundary contradiction recurred in the tail plan review: the tier table forbids re-execution while the full-suite paragraph instructs the plan reviewer to run touched tests; the reviewer again had to infer the boundary and set aside a general reviewer skill that did not fit."

## Proposed change

Three events in two runs, so this is a skill fix that must actually land:
remove the plan reviewer from the "The full suite runs once per build"
paragraph in the herd skill's `SKILL.md`, and add one sentence to the
plan-reviewer brief explicitly permitting read-only source/git-blob queries,
independent arithmetic, AST inspection, and in-memory projection of fences —
and excluding importing/applying the plan or running its tests and
mutations. Both #459 retros (PR 1 and tail, by the same role) name this as
their first action, so it is the operator's to apply; no tool in
`~/projects/herd/tools` owns this text.

## Prediction

No `skill-contradicts-itself` events in the next run's friction lines; plan
reviewers cite a single, unambiguous execution boundary and no retro again
proposes removing the plan reviewer from the full-suite paragraph.
