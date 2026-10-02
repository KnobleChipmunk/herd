# plan-negative-boundary-missing — enumerate every validation/filter condition and test both sides of it

Status: in-pr https://github.com/KnobleChipmunk/herd/pull/96

## Class

`plan-negative-boundary-missing` (plan freezes a fence without pre-executing negative boundary cases)

Events (from the ledger):

- 2026-09-27 herd ##40 (windows): Round 1's catalog and packet tests passed and all planned mutations were killed, but they missed binding: null, card: null, an existing non-card path, and assignment with no bindings file; those became findings F1, F2 and F4 and the lead had to add tests and amend I10 in round 3.
- 2026-09-27 herd #proposal-audit (windows): Pre-execution exercised universal output requirements only on success paths; round 1 found project() omitted anchors=n/a on file-operation failures while every gate and mutation stayed green.
- 2026-09-30 project-mera #334: build reviewer: the plan froze prior_seasons checking the patch cutoff before validating a catalog season name, so an unsafe name at the current patch produced no required warning; the accepted fold added exactly that case and mutation M14.
- 2026-09-30 project-mera #334: claude_build friction line: the I8 fence orders SeasonRef validation after the major_patch cutoff, so an unsafe catalog season name at or above the cutoff is skipped with no warning (the proposal requires the warning unconditionally); the round-1 reviewer caught it and BLOCKED for a reference fold.

## Proposed change

A card rule for the plan reviewer, since the defect is ordering between conditions and no tool sees the plan's condition list: when the spec says "every X warns/behaves", the plan reviewer enumerates each validation and filtering condition in the planned code, and the plan must test an invalid entry on both sides of every filter — an entry that passes the filter and an entry that is skipped by it. A mutation only pins the order the author thought to reverse; the two-sided test pins what the spec requires.

## Prediction

No `plan-negative-boundary-missing` events: every planned filter ships with a test for the skipped branch, and no build-review round is spent on a missing warning in a filter-skipped path.
