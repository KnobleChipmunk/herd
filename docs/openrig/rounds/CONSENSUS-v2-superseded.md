# OpenRig → herd: consensus v2 (Claude Opus 5.5 + Codex GPT-6 Astra), 2026-09-27

v2 folds in the openrig.dev report (Downloads/openrig_report.md) and the OpenRig
source at commit f137f11 (v0.5.17). v1 is in rounds/. Confidence: 5 = would bet
on it; ≤2 = do not build yet. Both agents agreed every rating.

| # | Implementation | Conf. |
|---|---|---|
| 0 | Run recovery (atomic start, unique run id, crash close, decisions visible across runs) + per-agent session outcome (resumed / fresh / failed / unknown); logical role kept separate from the pane occupying it | 5 |
| 2 | One watcher for attention + stalls, on OpenRig's state taxonomy. Intentional wait (HELD) is separate from a stall (PARKED); HELD suppresses only the stall alarm — a decision waiting on Nate still notifies and stays in the attention list. Waiting on a working peer is not a stall. Unknown reasons stay unknown. Herdr notification + optional ntfy; record-offset dedup; no automatic wakeups | 4 |
| 1a | Monitor over every agent in the Herdr workspace (not only the logged run); unassociated agents marked; activity, workflow step, and attention kept as separate columns; evidence links; text pane first | 5 |
| P | 60-minute evaluation: extend herd vs OpenRig-as-controller + Herdr-as-display, against the seven capabilities. Known question: OpenRig's Pi adapter runs `pi --mode rpc`, not interactive pi | 4 |
| 5 | One Markdown page per ticket at a stable address across runs (queued, parked and internal work too); run evidence linked beneath; status generated only from records | 5 |
| 6a | Agent-facing ticket interface: create, query, claim, hand off, block, close with a reason from a closed set (+ target when routed); GitHub issue as optional parent; questions go as messages, owned work goes as tickets | 5 |
| X | Ownership transitions as single durable records (with 6a); mechanical gate checks (with 3 + 4); tools enforce structure, reviewers/operator judge quality | 5 |
| 3 | Role cards + a current-step packet: role, step, inputs/outputs, next role, stop/escalation | 5 |
| 4 | herd.yaml: role identity, card ref, scope bindings, communication/escalation targets, model/fallback; resolved assignment stored at dispatch; advisory constraints labelled until a tool enforces them | 4 |
| C | Recovery packet (card + workflow position + decision anchors + next action) at dispatch and after compaction; delivery observed, not assumed | 4 |
| 7a | Keep the lead as the one orchestrator; define its behavior: record, route, give one consolidated answer, ask a specialist when records have gaps | 5 |
| 1b | Context % for Claude-harness seats from Claude Code statusLine JSON (`context_window.used_percentage`), with sample age; other harnesses unknown | 3 |
| 6b | Message acknowledgment/retry subsystem | 2 |
| 7b | Delegate pre-execution — revisit after 1b measures lead context by phase | 2 |
| H | Keep herd lifecycle ownership now (4) / adopt OpenRig (2) — P informs later choice | 4 / 2 |

Order: 0 → 2 + 1a → P → 5 + 6a + X (ownership) → 3 + 4 + C + X (gates) → 1b.

Key sources: openrig-src docs/reference/agent-state-taxonomy.md; docs/as-built/cli-reference.md:1281,1307-1308
(closure reasons, transactional handoff); openrig.dev/tour/workflow ("does not judge whether a step is complete");
openrig-src README.md:86,104 (statusLine collector); packages/daemon/src/adapters/pi-runtime-adapter.ts.
