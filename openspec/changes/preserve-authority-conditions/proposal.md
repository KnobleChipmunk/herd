# Preserve authorization conditions during plan review

## Why
The accepted proposal `proposals/2026-09-27-dropped-authorization-qualifier.md` records a role-card rewrite that changed a protected push from requiring operator authorization to an unconditional prohibition.

## Grounded facts
At base 4dfa966, `skill/cards/plan-reviewer.md:21` lists arithmetic, anchors and gate checks but no authority comparison. `skill/SKILL.md:239` gives the plan-review brief. `tests/test_team.py:172` already asserts that protected pushes retain their operator exception.

## What Changes
Add the source actor/action/scope/authorization comparison to the plan-reviewer card, covering extracted, reformatted and rewritten rules in both directions: tighter prohibitions and relaxed permissions. Require a focused assertion of the surviving condition, allowing existing coverage. Point to the check from the skill's plan-review brief and verify the delivered card contract.

## Non-goals
No changes to current permissions, role catalog, release-prep rules, model choice, or new authorization engine. Do not duplicate the existing protected-push assertion.

## Impact
Two instruction files and a focused contract test. Small tier; no new mechanism or design decision.
