# fold-red-evidence-stale

Status: accepted

## Class

fold-red-evidence-stale (post-fold RED/gate evidence in the handoff is stale and not re-observed)

Event lines, quoted from the ledger:

- 2026-09-30 project-mera #380-4: The round-1 ruling regenerated the T1 test file and said re-run ALL gates, but the handoff's RED section kept the pre-fold tail and the regenerated RED was never re-observed; the builder kept the old RED and disclosed the gap in handoff section 8.
- 2026-09-30 project-mera #380-4: After the accepted I5 fold, tasks.md expected 11 failed/4 passed for the new T1 body but the handoff still carried the pre-fold 9 failed/4 passed tail and said the new RED was not re-observed; the fold checklist needs a re-observed RED tail to keep section-0 gate and handoff aligned.

## Proposed change

Two briefings lines in `tools/mkbrief.py`, both emitted when the run carries
a lead fold:

1. The builder's handoff section: "after a fold, carry the pre-fold RED with
   a disclosure; do not re-observe RED." The builder already did this
   correctly by instinct; the line removes the guess and the disclosure
   noise.
2. The lead's fold checklist: when a test fence changes, run that test file
   against the pinned base in scratch, record its new RED tail and the
   `gates.py match` line, then reapply the implementation.

Prose, not a tool change: the fold checklist is lead judgment, and the
re-observation the checklist demands is a scratch run the lead already runs.

## Prediction

The next run's handoff RED section is either a fresh post-fold tail or the
pre-fold tail with an explicit disclosure line, and the section-0 gate's
expected count matches the handoff's recorded RED on first read.
