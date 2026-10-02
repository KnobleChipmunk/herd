# baseline-suite-contaminated-by-edits — measure the baseline in its own clean worktree

Status: accepted

## Class

`baseline-suite-contaminated-by-edits` (background baseline full suite reads static files at run time, so concurrent edits contaminate it)

Events (from the ledger):

- 2026-09-26 project-mera #459-4 (windows): The ~5 minute baseline full suite was started in the background before editing; because check.html is read at test-run time the run picked up mid-build edits and reported a contaminated 2 failed, 6798 passed, wasting the 5.5 minute run.
- 2026-09-30 project-mera #334: lead: the base full-suite run was started in the scratch worktree and that worktree was then edited while it ran, nearly contaminating the baseline; the baseline must be measured in its own clean worktree, never the pre-execution tree.

## Proposed change

A skill rule, because no tool can detect a concurrent edit mid-run: the lead section's baseline-measurement bullet becomes "measure the baseline full suite in its own clean worktree cut from the base commit; never in the pre-execution tree and never in a worktree you will edit". The #334 lead already added a `base-<id>` worktree by hand — this makes it the standing rule.

## Prediction

No `baseline-suite-contaminated-by-edits` events: every run's baseline tail comes from a `base-<id>` worktree that was never edited, and no baseline run is discarded for contamination.
