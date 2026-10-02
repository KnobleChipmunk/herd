# Proposal: gates.py manifest flags openspec/changes/ as OUTSIDE ALLOWED despite the brief's exemption

Status: applied https://github.com/KnobleChipmunk/herd/pull/26 2026-09-26

## Class

gates-manifest-openspec-unaware — gates.py manifest flags openspec/changes/ as OUTSIDE ALLOWED despite the brief's exemption

Events (friction ledger):
- 2026-09-26: "gates.py manifest printed four OUTSIDE ALLOWED lines and exited 1 for openspec/changes/pull-row-helper/ while the review brief explicitly exempted that directory, forcing manual reconciliation."
- 2026-09-26: "gates.py manifest's coordination exclusions omit ALLOWED-* and SCRATCH-* patterns: git status showed them outside the allowed paths and the reviewer had to manually confirm the manifest correctly excluded them."

## Proposed change

Code change in `tools/gates.py`: (a) add an exempt-prefix
option (or a separate manifest class) so spec paths under
`openspec/changes/` are excluded from `OUTSIDE ALLOWED` the same way the
review brief already exempts them; (b) make the reviewer-prompt exclusion
sentence generated from the manifest tool's own exclusion list, including
`ALLOWED-*` and `SCRATCH-*`, so the prompt and the tool have one source of
truth. Add a manifest test asserting a file under `openspec/changes/` and an
`ALLOWED-<id>.txt` produce no `OUTSIDE ALLOWED` line.

## Prediction

No `gates-manifest-openspec-unaware` events in the next run's friction
lines; a build with an OpenSpec change directory produces a clean manifest
and the reviewer prompt's exclusion sentence matches the tool's exclusions.

## Grading
- 2026-09-27: held
- 2026-09-29: missed — #333: the manifest showed two code files and four spec files while git status showed many more untracked coordination files, and the builder had to trust the manifest's invisible SCRATCH-* ignore across two tools
- 2026-09-30: held
- 2026-10-02: held
