# Proposal: byte-exact gate rejects case-variant defect fix until fences are folded

Status: accepted

## Class

case-variant-byte-exact — byte-exact gate rejects case-variant defect fix until
fences are folded

Events (friction ledger):
- 2026-10-02: "round 1 found a case-variant account owner defect in byte-exact I17; the builder cannot fix it until the lead folds regenerated fences, adding one review round."
- 2026-10-02: "the lead's fold of round 2 introduced a normative 'every job ends as failed' sentence contradicting the CheckRefused handling; round 3 existed only to align prose, costing a full review round."

## Proposed change

Prefer a tool over a new skill paragraph: extend `tools/fencecheck.py` (or the
fence-regeneration tool it wraps) with a `--rebase` mode that, when a byte-exact
gate fails on a case-variant or prose-level difference between the defect fix
and the pinned fences, regenerates the fences from the current tree and writes
them to the lead's coordination area with a one-line diff summary — so the lead
folds the regenerated fences in the same round the builder reports the finding,
instead of the builder being blocked on a fence fold it cannot make. The skill's
byte-exact section then gets one sentence: on a case-variant/prose fence
mismatch, run fencecheck --rebase and attach its output to the round report;
the builder does not hand-edit fences.

## Prediction

No `case-variant-byte-exact` events in the next run's friction lines; fence
mismatches are reported with regenerated fences attached, and no review round
exists solely to align prose or fold case-variant fences.
