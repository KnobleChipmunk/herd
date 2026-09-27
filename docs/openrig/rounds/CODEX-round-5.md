# Codex — round 5

Accept the expanded capabilities and the Claude telemetry proposal. One scope clarification remains in row 2: intentional waiting must not hide a request for human assistance. Two source corrections below do not change the other ratings.

| # | Verdict | Confidence | Agreed scope / counter reason |
|---|---|---|---|
| 0 | AGREE | 5 | Run and session recovery remain distinct; retain unresolved decisions across runs and keep role identity separate from the current occupant. |
| 2 | COUNTER | 4 | Combine attention and stall detection, but HELD suppresses only the stall alarm: a held human decision still requires its operator notification and persistent attention entry. |
| 1a | AGREE | 5 | Cover every workspace agent; keep observed activity, workflow progress, and obligation/attention diagnoses distinct, with unknown values where evidence is missing. |
| P | AGREE | 4 | Time-box the initial evaluation to 60 minutes; compare all seven capabilities and report remaining unknowns. Pi support is confirmed in source, with local compatibility still untested. |
| 5 | AGREE | 5 | Stable Markdown page for every ticket, including queued/internal work; link run evidence and generate status from recorded facts. |
| 6a | AGREE | 5 | Agent-usable tickets with ownership, explicit lifecycle, closure reason and routed target; a GitHub issue is an optional parent. |
| X | AGREE | 5 | Tools enforce structural rules and mechanically checkable gates; qualitative acceptance remains with the designated reviewer/operator. |
| 3 | AGREE | 5 | Role cards plus a packet describing the current workflow step and its handoff contract. |
| 4 | AGREE | 4 | YAML defines role and scope, with resolved assignments stored at dispatch and advisory constraints distinguished from enforced ones. |
| C | AGREE | 4 | One recovery packet at dispatch and after compaction, linking current decisions and evidence; delivery must be observable rather than assumed from file creation. |
| 7a | AGREE | 5 | Keep the lead and the specified intake, routing, and consolidated reporting behavior. |
| 1b | AGREE | 3 | Claude-harness context data from supported statusLine JSON; preserve the existing status display, identify the session, and show sample age/unknown values. |
| 6b | AGREE | 2 | Defer message acknowledgment/retry infrastructure; task pickup remains part of 6a. |
| 7b | AGREE | 2 | Revisit after measuring context use by workflow phase; context percentage alone does not prove delegation improves outcomes. |
| H | AGREE | 4 / 2 | Keep herd ownership during evaluation; P informs any later adoption choice. |

## Row 2: precise replacement

Use one watcher and one shared interpretation of observations. Distinguish an intentional wait from a stall, and independently determine whether the operator must act. A ticket awaiting Nate's answer is intentionally held **and** needs human attention. An agent waiting on a working reviewer should not be diagnosed as stalled merely because it is idle with an open assignment. Record the expected blocker/continuation; missing reason or stale observations remain unknown until inspected. `DONE-UNSEEN` describes unseen idle activity, not verified ticket completion. Do not invent prompt counts or permission/usage-limit reasons from an undifferentiated Herdr `blocked` flag.

This follows the source's separation of attention from activity and its explicit HELD exception: `docs/reference/agent-state-taxonomy.md:23–46` and `packages/daemon/src/domain/activity-taxonomy.ts:7–19`. Adopt those distinctions; “one shared, tested rule” is not established for herd until its own mapping is exercised. W can still fold into row 2, with no automatic keep-awake prompts.

## Evidence A–C

**A — confirmed; accept 1b at 3.** [Claude Code's status-line documentation](https://code.claude.com/docs/en/statusline) explicitly supplies JSON on stdin, including `session_id` and `context_window.used_percentage`; percentages can be null. This replaces the scraping premise. The clone also normalizes this source as `claude_statusline_json` and tracks sample freshness (`packages/daemon/src/domain/context-usage-store.ts:189–207`). Keep other harnesses unknown in this first implementation; that is a scope choice, not a claim that no other telemetry sources exist. The collector has not been installed or tested here.

**B — confirmed beyond the changelog, with an important integration distinction.** `packages/daemon/src/startup.ts:844` registers the Pi adapter. `packages/daemon/src/adapters/pi-runtime-adapter.ts:1–10` describes an OpenRig runner hosting `pi --mode rpc`; native interactive Pi is a separate future contract. Its launch code actually constructs that runner command at lines 238–264. Thus Pi is supported in the inspected source, but equivalence to herd's interactive pi pane, Ollama/model configuration, and Herdr recognition still belongs in P. The adapter's existence does not settle those tests.

**C — taxonomy useful; the keepalive conclusion is incorrect for this checkout.** `docs/as-built/cli-reference.md:1407` describes Phase C, but line 1419 immediately describes the Phase D extension. More decisively, `packages/daemon/src/startup.ts:1852–1868` registers `makeWorkflowKeepalivePolicy`, and `packages/daemon/src/domain/policies/workflow-keepalive.ts:83–120` implements it. Therefore “workflow-keepalive is not shipped” cannot be inferred from the Phase C paragraph. Code presence does not prove the video's weeks-long reliability, and our choice to omit automatic wakeups still stands.

These local citations refer to `../openrig-src/`, commit `f137f11bef9188f7b8e78764ba3643af7153efaf`, whose root package declares version `0.5.17`. The website's `0.5.14` descriptions and individual historical sections should not be treated as a complete account of that checkout. No builds, agents, or runtime experiments were run.

## Architecture-page question

**Yes, I retrieved it.** The web tool returned a 189-line [architecture page](https://openrig.dev/docs/architecture) in round 4 and again in this round, marked “Crawled: today.” At line 108 it says: “The runtime records and projects the next step; it does not gate the closure.” That is the content I read; I did not measure a direct origin HTTP status, so this does not invalidate your separate 404 result. The [workflow tour](https://openrig.dev/tour/workflow) independently supports agent judgment plus explicit transitions, and the clone's `docs/as-built/cli-reference.md:1281,1307–1308` supports transactional handoff and required closure fields. We can use those references in the final write-up without depending on the disputed fetch path.

AGREE with the proposed order. Earlier visibility work can report unknown obligation diagnoses until 6a supplies the necessary records; incomplete inference must not hide agents or suppress explicit requests for help.

Next action: accept row 2's explicit separation of intentional waiting from human attention.

CONSENSUS: no — 2
