# Proposal: contract extraction drops authorization qualifiers from role rules

Status: accepted

## Class

dropped-authorization-qualifier — contract extraction drops authorization qualifiers from role rules

Events (friction ledger):
- 2026-09-27 herd #40: "Expanding the lead card to eight fields changed protected pushes from 'need the operator' to 'never', although the source skill and team design retain an explicit authorization exception; the plan reviewer found it in round 2 and the round-3 fold restored it."
- 2026-09-27 herd #40: "Lead: the release-prep card rewrite dropped the 'without the operator' qualification; a pre-execution checklist should verify every rewritten rule keeps its operator qualification."

## Proposed change

Both events are the same failure: when a role rule is extracted or
reformatted into a card/contract, the authorization condition attached to the
rule was silently dropped (tightened from "needs the operator" to an absolute
prohibition). Add to the plan-reviewer checklist a focused check for
authority rules: when a rule is extracted, reformatted, or rewritten, compare
actor, action, scope, and the authorization condition against the source
skill, and add a test asserting the surviving condition. The check must cover
tightened prohibitions as well as relaxed permissions.

## Prediction

No `dropped-authorization-qualifier` events in the next run's friction lines;
extracted or rewritten authority rules keep their operator-authorization
qualifier, caught by the checklist (and a focused assertion) before the fence
is frozen rather than in a review round.
