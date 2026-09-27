# OpenRig → herd: consensus v4 (Claude Opus 5.5 + Codex GPT-6 Astra), 2026-09-27

v4 adds portability across systems (rounds 9–10) and removes vendor names from
the role rows. v1–v3 are in rounds/. Confidence: 5 = would bet on it; ≤2 = do
not build yet. Both agents agreed every rating. Design consensus only — not
authorization to implement, probe accounts, or run trials.

## Build issues

Filed 2026-09-27 with the `openrig-roadmap` label, in build order. Each goes
through its own spec and review before any build.

| Issue | Step | Rows |
|---|---|---|
| #31 | 0a — team design decision + portability contracts | TD, U1, U5 |
| #32 | 0b — reconcile DEVLOOP vs herd + run recovery | 0 |
| #33 | 1 — attention watcher, Herdr notifications | 2 (+W) |
| #34 | 1 — text monitor pane | 1a |
| #35 | 2 — 60-minute OpenRig evaluation | P |
| #36 | 3 — agent ticket interface + ownership transitions | 6a, X |
| #37 | 3 — one Markdown page per ticket | 5 |
| #38 | 4 — bindings resolver, adapters, readiness, fallback | U1, U2, U3, U7, U9 |
| #39 | 5 — `herd setup` + recommendations file | U4, U6 |
| #40 | 6 — role cards, herd.yaml, recovery packet, gate checks | 3, 4, C, X |
| #41 | 7 — context % from statusLine | 1b |
| #42 | after #35 — seat-layer support envelope | U8 |
| #43 | trial, needs operator go — independent QA | T1 |
| #44 | trial, needs operator go — dogfood session | T2 |

Not filed (rated 2 or less): 6b, 7b, H-adopt, T2b, T3b, T4b, T5, T7.
The discussion record is in `rounds/`; the source report was the operator's
openrig.dev tour report, and OpenRig citations refer to mvschwarz/openrig at
commit f137f11 (v0.5.17).

## Infrastructure

| # | Implementation | Conf. |
|---|---|---|
| 0 | Reconcile DEVLOOP.md vs the herd skill (Gate A vs plan-review authorization; 3 vs 2+1 review cap; operator-only vs lead push) so generated cards never encode a contradiction. Run recovery (atomic start, unique run id, crash close, decisions visible across runs) + per-agent session outcome (resumed / fresh / failed / unknown); logical role kept separate from the pane occupying it; recovery carries the resolved binding | 5 |
| 2 | One watcher for attention + stalls, on OpenRig's state taxonomy. HELD suppresses only the stall alarm — a decision waiting on the operator still notifies and stays listed. Peer waits, resource waits, scheduled-off dogfood and idle specialist capacity are not stalls; missing environments and auth/rate-limit blockers are distinct recorded states. Unknown reasons stay unknown. Herdr notification + optional ntfy; record-offset dedup; no automatic wakeups | 4 |
| 1a | Monitor over every agent in the Herdr workspace; unassociated agents marked; activity, workflow step, attention, and binding provenance (no credentials) in separate columns; evidence links; text pane first | 5 |
| P | 60-minute evaluation: extend herd vs OpenRig-as-controller + Herdr-as-display, against the seven capabilities. Questions: Pi adapter runs `pi --mode rpc`; shared-seat lifecycle; independent QA; safe dogfood scheduling; single-harness resolution; conditional preflight; transport requirements; identity-safe fallback. Untested combinations labelled, not certified | 4 |
| 5 | One Markdown page per ticket at a stable address across runs; records selected/omitted checks, tested candidate, QA and dogfood evidence; an omitted or blocked check is never PASS | 5 |
| 6a | Agent-facing tickets: create, query, claim, hand off, block, close with a reason from a closed set (+ target when routed); GitHub issue as optional parent; questions go as messages, owned work as tickets | 5 |
| X | Ownership transitions as single durable records (with 6a); mechanical gate checks (with 3 + 4); tools enforce structure, reviewers/operator judge outcomes | 5 |
| C | Recovery packet (role contract + workflow position + decision anchors + resolved binding + next action) at dispatch and after compaction; a provider switch means a fresh session from durable artifacts, not cross-provider resume; a reused pane never inherits the previous role's authority | 4 |
| 1b | Context % where the harness supplies it (Claude Code statusLine JSON today), with sample age; others unknown | 3 |
| 6b | Message acknowledgment/retry subsystem | 2 |
| 7b | Delegate pre-execution — revisit after 1b measures lead context by phase | 2 |
| H | Keep herd lifecycle ownership now (4) / adopt OpenRig (2) — P informs later choice | 4 / 2 |

## Team design

**Roles are not seats.** The portable role catalog defines each role (purpose,
inputs, outputs, activation trigger, scope, evidence, authority, author/evaluator
exclusions) with no vendor names. Machine-local bindings resolve roles to
sessions and models. This machine's Claude + Codex + pi roster is an example
profile, not a requirement. Bindings grant no new permissions.

| # | Implementation | Conf. |
|---|---|---|
| TD | Team design decision: role catalog + bindings + independence policy (U5) + support envelope; runs alongside step 0, gates 3 + 4 | 5 |
| 3 | Role contracts: one card per role that runs in its own session (builder, plan reviewer, build reviewer, QA, dogfood, designer); ONE lead card with sections for orchestrator, architect, planner, product intake, release prep; librarian bound to an available harness or its work recorded as a pending obligation. Current-step packet carries role, candidate, required evidence, return route, independence requirement | 5 |
| 4 | Portable herd.yaml: roles, activation/skip conditions, exclusions, allowed operations, time/cost limits, capability requirements; resolved assignment (role + binding + session + candidate + scope + checks) stored at dispatch; advisory until a tool enforces (see U1) | 4 |
| 7a | The lead: single user-facing orchestrator; owns intake, role selection, architect/planner work, QA dispositions, dogfood triage; reports what was exercised and what remains unchecked | 5 |
| T1 | Independent Test QA: activated at planning by journey/risk (skip reason recorded); fresh non-author context in the specialist slot after build review is clean, before the lead's final review; a model different from the builder recommended; frozen candidate; isolated fixtures allowed, candidate repair not; promised vs observed + unchecked list; changed candidate renews review + QA evidence | 4 |
| T2 | Dogfood: operator-authorized, 20-minute session on any product with a usable surface + safe environment; findings as tickets; lead triage; new scope via the sweep | 4 |
| T2b | Standing continuous dogfood seat | 2 |
| T3 | Architect as a named lead-held role, distinct from Planner: cross-ticket decisions, interfaces, invariants, dogfood design implications, in design.md | 4 |
| T3b | Separate architect seat | 2 |
| T4 | Release prep as a lead-held responsibility; herd's branch-push authority unchanged; operator keeps merge/publish | 4 |
| T4b | Separate release-manager seat | 1 |
| T5 | Standing orchestrator peer (bounded coordination audit via the plan-review slot instead, when selected) | 2 |
| T6 | Product Designer, on demand in the specialist slot before the plan freezes | 3 |
| T7 | Separate PM rig | 2 |

## Portability across systems

Grounding: herd's preflight.py:18 hard-requires `pi`, `codex` and `claude`, so a
single-harness machine fails today; probe.py hardcodes three harnesses. OpenRig
detects only via `claude auth status` / `codex login status` and swaps a
precomputed variant (kernel-boot.ts:139-176) — no prompts, no diversity guidance.

| # | Implementation | Conf. |
|---|---|---|
| U1 | Portable vendor-neutral role policy (ships with herd / the repo) + user-local bindings in the platform config dir with full identity: harness, provider, endpoint, model, auth-profile reference, settings. Precedence: invocation flag → user-local bindings → portable defaults; local bindings can never relax the project's hard requirements. Version field, unknown keys rejected, migrations only when a real breaking change needs one. Sanitized resolved binding stored per run | 5 |
| U2 | Typed harness adapters (discover, status, probe, launch, observe) with vetted argument vectors — no shell templates in config. Preflight derived from the selected workflow + bindings: no unused harness required, needed tools (tests, browser, GitHub, transport) still checked | 4 |
| U3 | Readiness as independent observations on the exact dispatch tuple: installed, auth required/status, model access, role capabilities. Distinct states: needs-login, model-denied, rate-limited, unreachable, unsupported, unknown. A timeout is not "no access"; a reply is not proof of model identity. Cached with freshness; one result reused by roles sharing a tuple. Active probes gated by one saved consent answer covering setup and future preflights | 5 |
| U4 | `herd setup`: manual and assisted modes. Assisted discovers known binaries and configured/supplied endpoints only (no port scans, token-file reads, installs, logins, server starts); prompts per role from the usable pool (e.g. Claude-only: choose a model for lead, builder, reviewers/QA, preferring different suitable models); shows the diversity of each author/evaluator pair; previews and confirms before saving. Headless validate lists what is missing without prompting. Rediscovery never overrides saved choices | 5 |
| U5 | Independence policy, two dimensions: evaluator separation (non-author, fresh context) is HARD for designated independent evaluation, regardless of vendor; model diversity (same / different / unknown) is recommended, warned and recorded, never forced unless project policy requires it. Same-model fresh non-author evaluation is a valid, disclosed reduced-diversity setup. The lead's own final pass never counts as the independent evaluator. Replaces the "never Opus reviewing Opus" rule | 5 |
| U6 | Editable recommendations file: concrete model/provider profiles per role, each with reason, source type (official capability / user preference / observed role outcome) and date; stale and unknown entries flagged; no vendor stereotypes, no automatic tier spread; mixing recommended among suitable options, never over capability, privacy or budget | 4 |
| U7 | Fallback: only user-listed bindings in that role's ordered chain, each meeting project requirements; no auth-profile or provider switch unless that exact binding is listed; never switch global credentials under live sessions; no account rotation; transient limits distinguished from permanent denial | 5 |
| U8 | Seat-layer support envelope: inventory the full lifecycle herd needs; Herdr first; tmux or in-session modes decided after P; an unsupported transport is reported, not faked | 3 |
| U9 | Resolver/adapter fixture tests (Claude-only, Codex-only, mixed, one model, none usable, stale auth, rate-limited, bad endpoint) plus tests for consent, fallback, key validation and redaction; live smoke only for combinations the operator has, when authorized; everything else labelled untested | 4 |

## Order

TD + portability contracts (U1, U5) alongside 0 → 2 + 1a → P → 5 + 6a + X (ownership)
→ U1 resolver + U2 + U3 + U7 → U4 + U6 → 3 + 4 + C + X (gates) → 1b.
U8 after P. U9 grows with each U row. T1/T2 trials on today's files once separately authorized.

Key sources: openrig-src (commit f137f11, v0.5.17) kernel-boot.ts:139-176, specs/rigs/launch/factory-rsi/rig.yaml,
agents/development/qa/guidance/role.md, agents/factory-rsi/dogfood/guidance/role.md,
docs/reference/agent-state-taxonomy.md, docs/as-built/cli-reference.md:1281,1307-1308;
openrig.dev/tour/workflow; herd SKILL.md, tools/preflight.py:18, tools/probe.py.
