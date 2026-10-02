# boundary-tests-miss-downstream-contract — trace changed discriminators into branching callers at plan review

Status: accepted

## Class

`boundary-tests-miss-downstream-contract` (boundary test passes while the downstream consumer contract rejects the new output)

Events (from the ledger):

- 2026-09-30 project-mera #380-4 (windows): Round 1 asserted only that zero time alive produced an estimated recorder entry, which passed while Brewmaster and Guardian's production contracts rejected it as a derivation downgrade; round 2 had to add the affected-contract cases, costing a second plan-review round.
- 2026-09-30 project-mera #334: plan reviewer: the new season keys flip a prior boss from found=False to found=True, which makes runner.py skip fetch/refill and bypasses the guide-error gate, a consumer effect that reader tests alone could not establish.

## Proposed change

Prefer a tool: add a check to the plan-reviewer card's consumer-sweep step — for every changed output discriminator (a field whose value set changed), the plan reviewer names the branching callers (grep the field) and records the resulting branch for each. The card text has already failed once (the #334 effect was only found by the reviewer after the fact, not by any checklist), so the check is mechanical: a table row per changed discriminator with `caller file:line → branch taken → intended?`. A plan that cannot fill the table for a changed discriminator is REVISE.

## Prediction

Next run's plan-review files contain the discriminator table for every changed output field, and no second plan-review round is spent on a downstream-consumer effect (no `boundary-tests-miss-downstream-contract` events).
