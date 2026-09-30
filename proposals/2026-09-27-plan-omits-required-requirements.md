# Proposal: plan review passes while the plan omits governing requirements

Status: applied https://github.com/KnobleChipmunk/herd/pull/69 2026-09-28

## Class

plan-omits-required-requirements — plan review passes while the plan omits governing requirements

Events (friction ledger):
- 2026-09-27 herd #40: "Plan review round 1 arrived with 476 passing tests and seven killed mutations, yet the catalog lacked required policy fields, the lead card lacked complete eight-field contracts, and librarian portability was omitted; the tests reproduced the plan's omissions, so the missing requirements only surfaced at the first independent review."
- 2026-09-27 herd #40: "Lead: #40 round 2 found a new command (team.py assign) that nothing in the skill calls; a pre-execution checklist should verify every new command has a caller in the skill or a card."

## Proposed change

A green pre-execution run is not a completeness check: it reproduced the
plan's omissions. The fix is a small requirement table in the planning
template, checked against the issue and design before fences are generated.

Add to the plan template (and the plan-reviewer checklist) a requirement
table with one row per governing requirement: source section, implementing
step, acceptance evidence, or a linked deferral. The pre-execution check
verifies three things before the first independent review:
- every governing requirement maps to an implementing step or an explicit
  deferral,
- every new command the plan adds has a caller in the skill or a card
  (catches "a new command nothing calls"),
- the table is checked against the issue and the design, not just the tests.

## Prediction

No `plan-omits-required-requirements` events in the next run's friction lines;
missing requirements and caller-less commands surface in the plan table before
the first independent review round, not in round 1 findings.

## Grading
- 2026-09-29: held
- 2026-09-30: held
