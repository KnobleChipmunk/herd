# Proposal: fold declares done without checking implementation constraints

Status: applied https://github.com/KnobleChipmunk/herd/pull/85 2026-09-30

## Class

fold-coherence-gap — fold declares done without checking implementation
constraints

Events (friction ledger):
- 2026-09-25 project-mera #460 (windows): Round 3 caught a new Node runner duplicating machinery the spec required reusing, and folds shipped stale descriptions and unvalidated timer-coverage promises; folds need a coherence check before returning to review.
- 2026-09-29 project-mera #333 (windows): Plan reviewer: the stacking-model fold changed no-aura handoffs from zero/early to None/unknown, M6's insertion, and M7's default early threshold; the round-2 disposition enumerated these changes, and a 'never returns 0' helper claim needed bounding to the observed encoding.

## Proposed change

Both events are the same shape: a fold (lead-applied spec change) returned to
review without a checklist of which outcomes it changed. In #333 the
model-changing fold silently altered missing-data behavior, a mutation's
insertion, and a threshold default — the round-2 disposition had to enumerate
them, and a helper claim ("never returns 0") was too broad until bounded to
the observed encoding.

Add a model-changing-fold checklist to the skill's fold step (prose, tagged
with the two events): before a fold returns to review, enumerate (1) normal
boundary, (2) late boundary, (3) absent-state behavior, and (4) affected
mutation/killer pairs. Require claims about helper functions to follow every
relevant branch, and bound documentation to the observed encoding without
expanding the change into defensive parser work.

## Prediction

No `fold-coherence-gap` events in the next run's friction lines; each fold
disposition in the round file carries the four-row outcome checklist, and
helper-function claims in the spec name the branch they hold on.

## Grading
- 2026-10-02: held
