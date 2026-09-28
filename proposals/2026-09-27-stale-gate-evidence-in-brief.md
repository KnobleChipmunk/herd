# Proposal: brief gate summary reports stale or pending results

Status: in-pr https://github.com/KnobleChipmunk/herd/pull/67

## Class

stale-gate-evidence-in-brief — brief gate summary reports stale or pending results

Events (friction ledger):
- 2026-09-25 project-mera #460: "Round 5 brief said the full suite was 'measuring now' while GREEN showed a final count, and the round-2/3 handoff still said FENCES OK (62 steps) after fences grew to 63, so the reviewer could not verify completion from the evidence."
- 2026-09-27 herd #40: "BUILD-BRIEFING-40.md said the full suite must be 487 passed while tasks.md and the spec commit said 489 (actual 489); the builder read the briefing first and had to notice the conflict itself."
- 2026-09-27 herd #40: "Lead: a briefing generated before the last fold carried stale gates (487 and M1-M14 instead of 489 and M1-M16); the builder noticed and followed tasks.md."
- 2026-09-27 herd #40: "pi_build: after the round-3 ruling the 'Required after the build' section of BUILD-BRIEFING-40.md went stale (487 to 495, 15 to 16 steps, M1-M16 to M1-M19); the lead updated it by hand because the skill has no step for re-issuing the briefing after a spec amendment."

## Proposed change

All four #40 events are the same drift: the briefing's gate literals (suite
count, mutation range, fence step count) were written by hand or before the
last fold, so they disagreed with tasks.md and the builder had to notice the
conflict itself.

1. `tools/mkbrief.py`: copy the gate literals (full-suite passed count,
   mutation range, fence step count) directly from the change's `tasks.md`
   instead of accepting them as generator inputs, so the two documents cannot
   drift. Generate the briefing after APPROVE, from the generator's own
   numbers, never by hand.
2. `skill/SKILL.md` lead loop: add a step — after any spec amendment,
   regenerate the briefing from `tasks.md` before dispatching the next round,
   so the builder never works to stale gate literals. This removes the lead's
   by-hand re-issuance (the last event above).

## Prediction

No `stale-gate-evidence-in-brief` events in the next run's friction lines;
the briefing's suite count, mutation range, and fence step count always match
tasks.md, and a spec amendment triggers a regenerated briefing before the next
dispatch.
