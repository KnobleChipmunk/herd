# Proposal: mutation engine false verdicts

Status: applied https://github.com/KnobleChipmunk/herd/pull/15 2026-09-25

## Class

mutation-engine-false-verdict — mutation engine reports wrong survivor/killer verdicts

Events (friction ledger):
- 2026-09-25: "Skipped node killer read SURVIVED and unresolvable killer id read KILLED, so mutation kills were misreported until herd PR #15 fixed the tool."
- 2026-09-25: "An interrupted drive left a mutation applied in the reference, corrupting the byte-exact baseline the builder restores from."

## Proposed change

The verdict bug is already fixed in code (herd PR #15, merged), so the proposal is
a code change to keep it fixed: add a regression test suite under
`tools` that exercises (a) a killer whose node is skipped in the
task tree and (b) an unresolvable killer id, asserting both read as neither
SURVIVED nor KILLED, and (c) a simulated interrupted drive asserting the
reference tree is restored to the base before the next step. Prefer extending
the existing test layout in `tools/` to a new `test_mutation_engine.py`; do not
change the skill wording.

## Prediction

No `mutation-engine-false-verdict` events in the next run's friction lines; the
regression suite passes on a fresh clone before the run starts.
2026-09-26: held

## Grading
- 2026-09-27: held
- 2026-09-29: held
- 2026-09-30: held
