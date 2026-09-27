# Proposal: full suite re-run after every fold

Status: applied https://github.com/KnobleChipmunk/herd/pull/54 2026-09-27

## Class

full-suite-rerun-after-fold — full suite re-run after every fold instead of once

Events (friction ledger):
- 2026-09-25: "Lead restarted the replay's full suite three times because a fold landed while it ran, wasting about 45 minutes; it should run once after the last fold before plan review."
- 2026-09-25: "The lead's ruling forced a second 13-14 minute full-suite run (6663 to 6666) against the handoff's 'run exactly once' rule; the gate legitimately re-opens per build-state."

## Proposed change

Code change in `~/projects/herd/tools` plus one handoff sentence: the build
loop should not start a full-suite run while a fold is pending — sequence folds
first, then a single suite run after the last fold before plan review (enforce
or warn in the loop tooling that tracks gate runs). The handoff's "run the full
suite exactly once" should be scoped as *per build-state*: a reference
mutation from a ruling legitimately re-opens the suite gate for one additional
run. Neither event in this class was a rule the agents lacked; the loop tooling
gives no signal that a fold invalidated an in-flight run.

## Prediction

The next run's ledger shows at most one full-suite run per build-state; no
`full-suite-rerun-after-fold` events, and no 13+ minute suite run started
during a pending fold.
2026-09-26: held
