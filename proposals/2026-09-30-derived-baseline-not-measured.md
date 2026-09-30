# Proposal: full-suite baseline derived by subtraction from the after count instead of run

Status: applied https://github.com/KnobleChipmunk/herd/pull/75 2026-09-30

## Class

derived-baseline-not-measured — full-suite baseline derived by subtraction from the after count instead of run

Events (friction ledger):
- 2026-09-29 project-mera #482 (windows): "Plan reviewer: the full-suite base count 6827 was derived by subtracting three new tests from the measured GREEN 6830, and the skill's wording left the measured-vs-derived distinction to the reviewer's interpretation."
- 2026-09-29 project-mera #482 (windows): "Lead: the full-suite baseline at HEAD was derived, not run (after count minus 3 new tests); the plan reviewer flagged it and the fix is to run the baseline suite in the background during pre-execution."

## Proposed change

Both events are the same gap: the full-suite baseline at HEAD was never run,
it was derived (after count minus the new tests), and the skill's wording
about measured baselines left it to the reviewer to notice and flag. The
baseline is cheap — it costs nothing on the critical path if it runs in the
background during pre-execution while the plan is being reviewed.

Change `tools/mkbrief.py` (and the pre-execution step it
drives) so the lead's pre-execution sequence starts the full-suite baseline
run in the background at HEAD, before the build begins, and writes its tail
into the briefing as a `measured` value. The briefing's gate-evidence block
should then carry a provenance field per gate (`measured` vs `derived`) so a
derived baseline is labeled as such and can never be read as a run.

## Prediction

No `derived-baseline-not-measured` events in the next run's friction lines;
the briefing's full-suite baseline carries a `measured` provenance and a real
tail from a run at HEAD, and the plan reviewer no longer has to flag a
subtracted base count.
