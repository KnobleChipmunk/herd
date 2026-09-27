# OpenRig → herd: consensus v3 (Claude Opus 5.5 + Codex GPT-6 Astra), 2026-09-27

v3 adds team composition (rounds 7–8). v1 and v2 are in rounds/. Confidence:
5 = would bet on it; ≤2 = do not build yet. Both agents agreed every rating.
Design consensus only — not authorization to implement or run a role trial.

## Infrastructure

| # | Implementation | Conf. |
|---|---|---|
| 0 | Run recovery (atomic start, unique run id, crash close, decisions visible across runs) + per-agent session outcome (resumed / fresh / failed / unknown); logical role kept separate from the pane occupying it | 5 |
| 2 | One watcher for attention + stalls, on OpenRig's state taxonomy. HELD suppresses only the stall alarm — a decision waiting on Nate still notifies and stays listed. Peer waits, scheduled-off dogfood and idle specialist capacity are not stalls; missing environments are recorded blockers. Unknown reasons stay unknown. Herdr notification + optional ntfy; record-offset dedup; no automatic wakeups | 4 |
| 1a | Monitor over every agent in the Herdr workspace; unassociated agents marked; activity, workflow step, attention in separate columns; evidence links; text pane first | 5 |
| P | 60-minute evaluation: extend herd vs OpenRig-as-controller + Herdr-as-display, against the seven capabilities. Questions: OpenRig's Pi adapter runs `pi --mode rpc`; shared-seat lifecycle; independent QA; safe dogfood scheduling | 4 |
| 5 | One Markdown page per ticket at a stable address across runs; records selected/omitted checks, tested candidate, QA and dogfood evidence; an omitted or blocked check is never PASS | 5 |
| 6a | Agent-facing tickets: create, query, claim, hand off, block, close with a reason from a closed set (+ target when routed); GitHub issue as optional parent; questions go as messages, owned work as tickets | 5 |
| X | Ownership transitions as single durable records (with 6a); mechanical gate checks (with 3 + 4); tools enforce structure, reviewers/operator judge outcomes | 5 |
| C | Recovery packet (role contract + workflow position + decision anchors + next action) at dispatch and after compaction; a reused pane never silently inherits the previous role's authority | 4 |
| 1b | Context % for Claude-harness seats from statusLine JSON, with sample age; others unknown | 3 |
| 6b | Message acknowledgment/retry subsystem | 2 |
| 7b | Delegate pre-execution — revisit after 1b measures lead context by phase | 2 |
| H | Keep herd lifecycle ownership now (4) / adopt OpenRig (2) — P informs later choice | 4 / 2 |

## Team design

Principle: **roles are not seats.** `herd.yaml` defines each role (purpose,
inputs, outputs, activation trigger, scope, evidence, authority,
author/evaluator exclusions); bindings resolve roles to sessions and models.
A role can exist without its own pane. Bindings grant no new permissions.

| # | Implementation | Conf. |
|---|---|---|
| TD | Team design decision: role catalog + bindings; runs alongside step 0, gates 3 + 4 | 5 |
| 3 | Role contracts: one card per role that runs in its own session (builder, plan reviewer, build reviewer, QA, dogfood, designer); ONE lead card with sections for orchestrator, architect, planner, product intake, release prep; librarian keeps its existing guidance. Current-step packet carries role, candidate, required evidence, return route, independence requirement | 5 |
| 4 | herd.yaml: roles separate from bindings; activation/skip conditions, exclusions, allowed operations, time/cost limits; resolved assignment (role + session + candidate + scope + selected checks) stored at dispatch; advisory until a tool enforces | 4 |
| 7a | The lead: single user-facing orchestrator; owns intake, role selection, architect/planner work, QA dispositions, dogfood triage; reports what was exercised and what remains unchecked | 5 |
| T1 | Independent Test QA: activated at planning by journey/risk (skip reason recorded); fresh Codex context in slot 3 after build review is clean, before the lead's final review; frozen candidate; isolated fixtures allowed, candidate repair not; promised vs observed + unchecked list; changed candidate renews review + QA evidence; amend SKILL.md slot-3 rule | 4 |
| T2 | Dogfood: operator-authorized, 20-minute session on any product with a usable surface + safe environment (web app, CLI install/upgrade, library via public API, installed skill); findings as tickets; lead triage; new scope via the sweep | 4 |
| T2b | Standing continuous dogfood seat | 2 |
| T3 | Architect as a named lead-held role, distinct from Planner: cross-ticket decisions, interfaces, invariants, dogfood design implications, in design.md | 4 |
| T3b | Separate architect seat | 2 |
| T4 | Release prep as a lead-held responsibility; herd's branch-push authority unchanged; operator keeps merge/publish | 4 |
| T4b | Separate release-manager seat | 1 |
| T5 | Standing orchestrator peer (bounded coordination audit via the plan-review slot instead, when selected) | 2 |
| T6 | Product Designer, on demand in slot 3 before the plan freezes | 3 |
| T7 | Separate PM rig | 2 |

## Order

TD alongside 0 → 2 + 1a → P → 5 + 6a + X (ownership) → 3 + 4 + C + X (gates) → 1b.
T1/T2 trials can run on today's files and tickets once separately authorized.

Key sources: openrig-src (commit f137f11, v0.5.17) specs/rigs/launch/factory-rsi/rig.yaml,
specs/agents/development/qa/guidance/role.md, specs/agents/factory-rsi/dogfood/guidance/role.md,
docs/reference/agent-state-taxonomy.md, docs/as-built/cli-reference.md:1281,1307-1308;
openrig.dev/tour/workflow; herd SKILL.md:151,190-201,221-223.
