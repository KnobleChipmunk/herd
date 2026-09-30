# Proposal: RULING-* files outside the coordination exemption list

Status: applied https://github.com/KnobleChipmunk/herd/pull/26 2026-09-26

## Class

ruling-file-outside-allowed — RULING-* files not in the coordination exemption list

Events (friction ledger):
- 2026-09-25: "Lead named its ruling file RULING-460-1.md; gates.py COORDINATION does not exempt RULING-*, so build review round 2 was spent entirely on it."
- 2026-09-25: "RULING-460-1.md produced OUTSIDE ALLOWED in build review round 2; the lead had to rename it SCRATCH-RULING-460-1.md and burn the round."

## Proposed change

Code change in `tools/gates.py`: add `RULING-*` to the
`COORDINATION` exemption tuple alongside BUILD-BRIEFING/HANDOFF/REVIEW/CODEX/
ALLOWED/RED/GREEN/FULLSUITE/MUTATION-LOG/SCRATCH, with a manifest test that
asserts a `RULING-<id>-<n>.md` file in the worktree does not produce
`OUTSIDE ALLOWED`. This loosens nothing on the source-file allowlist: ruling
files were never build output, and the allowed-file list is unchanged.

## Prediction

No `ruling-file-outside-allowed` events in the next run's friction lines; a
lead ruling left in the worktree produces no spurious `OUTSIDE ALLOWED` finding
and no review round is spent on it.
2026-09-26: held

## Grading
- 2026-09-27: held
- 2026-09-29: held
- 2026-09-30: held
