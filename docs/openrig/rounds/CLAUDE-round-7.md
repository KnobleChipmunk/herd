# Claude — round 7 (team composition)

Verified from the clone: no shipped rig has an Architect seat; "architect"
appears only in skills. factory-rsi = orch lead, planner, implementer, qa,
reviewer, dogfood tester, release manager; qa/review/dogfood run on Codex
"for cross-runtime diversity against the builder". QA role: "exercise the
public journey… record what was not checked… the evaluator must not be the
author". Dogfood: out-of-band on the SHIPPED product, "not a smoke test…
NOT a second QA"; findings feed the next plan, UNGATED.

| # | Seat | Herd today | Gap | Shape | Conf. |
|---|---|---|---|---|---|
| T1 | Test QA | lead writes tests + pre-executes + final-reviews; builder runs them; reviewer runs touched tests; mutation drives | Every check traces to one author's model of the contract; a wrong fixture passes pre-execution, build, review, and mutations (herd SKILL.md plan-reviewer brief already names this: "a wrong expected value that the implementation reproduces passes tests AND mutations"). DEVLOOP stage 3 requires "one end-to-end smoke"; herd has none | Independent QA in the slot-3 pane (Codex), after build-review clean and before the lead's final review; exercises the built branch against real inputs (real data, running app/CLI); read-only; reports promised vs observed + what was not checked; findings route to the builder like review findings | 4 |
| T2 | Dogfood | none — the librarian dogfoods the PROCESS (friction → proposals), not the product | Nobody uses what shipped | Out-of-band seat for projects with a running product (MERA web app; not skill/library repos); uses the deployed product; files GitHub issues with evidence; GATED — issues enter herd via the operator's sweep, never auto-planned | 3 |
| T3 | Architect | lead (pick, tier, design.md) + plan reviewer challenges | none material | No separate seat; duplicates the lead's shaping and adds a hand-off | 2 |
| T4 | Release manager | merge_stack.py + openspec archive; operator holds merge | none — the operator gate is deliberate | No seat | 1 |
| T5 | Orchestrator peer (Codex) | plan reviewer is a per-issue peer on the spec only | cross-model check on routing/rulings is absent | Not now; revisit if lead rulings prove wrong in the run log (`ruling` events) | 2 |

Knock-on for v2 rows: row 4 (herd.yaml) must define seats beyond the
current four (QA, dogfood) and allow a seat to be per-project optional;
row 3 needs QA and dogfood cards; T1 slots into the loop between
build-review clean and the lead's final review.
