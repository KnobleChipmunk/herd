# manual-reference-mutation-recovery

Status: applied https://github.com/KnobleChipmunk/herd/pull/83 2026-09-30

## Class

manual-reference-mutation-recovery (re-applying fence steps after a reference mutation is hand-scripted)

Event lines, quoted from the ledger:

- 2026-09-25 project-mera #460 (windows): After the lead folded a fix into tasks.md, the builder hand-wrote a scratch script to pick and re-apply specific steps (T15, I27-I36) against the new reference; a first-class reapply command would remove the guesswork.
- 2026-09-30 project-mera #380-4: The builder hand-rolled SCRATCH-apply.py (anchor count check + kind dispatch over the STEPS json) because the skill has no canonical step applier; every builder writes their own variant, and a shared tools/apply-steps.py would remove the reinvention.

## Proposed change

Ship a canonical step applier in `tools/`: `tools/apply-steps.py
<steps.json> <names...>` with the "anchor must occur exactly once" check
built in and kind dispatch over the STEPS json. Both events are the same
failure: each builder invents their own applier (or re-apply script) because
the skill has no first-class command, and a home-grown applier can mishandle
a `kind` or an anchor count without saying so. A tool change, not prose: the
check is mechanical.

## Prediction

No manual-reference-mutation-recovery events in the next run: the builder's
retro names `apply-steps.py` as the applier used, and no SCRATCH-apply*.py
file appears in the run's worktrees.

## Grading
- 2026-10-02: held
