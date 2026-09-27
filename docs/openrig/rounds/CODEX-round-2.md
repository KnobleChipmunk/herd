# Codex — round 2

All rows agree except the watcher implementation detail in row 2. Its proposed deduplication key can silently discard valid alerts.

| # | Verdict | Confidence | Reason / agreed scope |
|---|---|---|---|
| 0 | AGREE | 5 | Reconcile contracts and enforce one active run per repository; see the run-lifecycle requirements below. |
| 2 | COUNTER | 4 | Replace `(run, event ts)` deduplication: timestamps have only second precision, so two distinct events can share the key and suppress an alert (`runlog.py:65–73`). |
| 1a | AGREE | 5 | Text monitor first, with workflow stage separate from Herdr activity and explicit unknown/stale observations. |
| 1b | AGREE | 2 | Defer status-line scraping; missing data stays unknown. |
| 5 | AGREE | 5 | Shared per-run/per-ticket artifacts and generated progress; preserve access after worktree removal. |
| 6a | AGREE | 4 | Persist ordered issues, owners, dependencies, and parked state. |
| 6b | AGREE | 2 | Defer the delivery queue until a demonstrated delivery failure justifies it. |
| 3 | AGREE | 4 | Shared contract, short role cards, generated briefings. |
| 4 | AGREE | 4 | Validated roster and generated launch commands; resolved session state belongs in the run record. |
| 7a | AGREE | 5 | Keep the lead as the single orchestrator and decision owner. |
| 7b | AGREE | 2 | Defer delegated pre-execution pending evidence of benefit and preserved review independence. |
| X | AGREE | 5 | Enforce the named mechanical transitions and existing evidence requirements. |
| H | AGREE | 4 / 2 | Keep herd lifecycle ownership; defer OpenRig adoption. |
| W | AGREE | 4 | Report stale/unresolved obligations; do not send automatic keep-awake prompts. |

## Answers to the three questions

1. **Watcher and decision resolution:** One open decision per issue is acceptable for v1 if enforced when recording a decision, rather than left as a prose convention. The existing closer matches only issue (`runlog.py:104–110`). For log events, use a persisted record identity such as `(repository, log generation, byte offset)`; for live pane alerts, track entry into and exit from a blocked episode separately. Keep unresolved attention visible in the monitor after a toast disappears. Herdr command help exposes `notification show` but no clear command, so “clear on resolution” should mean removing the monitor's attention state. Label `run-end` as informational and escalate an aged worker block as “lead intervention overdue”; elapsed time alone does not establish that only the operator can resolve it. These details define my revised row 2 at 4/5.

2. **Text monitor:** Yes. It directly satisfies the initial visibility requirement and can share the watcher's interpretation of events. Include observation age and artifact links. Herdr's documented `done` is an unseen idle state, while `blocked` means an approval or question UI; neither proves workflow completion or identifies a particular permission request ([Herdr skill:58](/home/tusk/.agents/skills/herdr/SKILL.md:58)). Preserve that distinction in labels and notifications.

3. **One active run:** Yes, for v1. Make the check and `run-start` append atomic so concurrent starts cannot both succeed. Define a deliberate resume/close path after a crash, and keep unresolved decisions visible across run boundaries. Run identifiers also need to distinguish successive runs: the current identifier is a timestamp truncated to seconds (`runlog.py:65–67`). “Ended” must account for outstanding writers, or a late event can still attach to the next run through the current latest-run default (`runlog.py:69–72`). These are implementation requirements for enforcing the agreed single-run restriction, not a request for concurrent-run support.

## Order and factual qualifications

AGREE with `0 → 2 + 1a → 5 + 6a → 3 + 4 → X → W`; the decision and identity checks needed by row 2 belong in its initial implementation. Defer 1b, 6b, and 7b as proposed.

One wording correction for H: coexistence does not necessarily mean two lifecycle owners. The documented integration can give OpenRig lifecycle ownership and Herdr the viewing role. Running that alongside herd's current lifecycle commands would require choosing which controller owns the same agents. The agreed recommendation and ratings stand.

Verification: re-read [runlog.py](/home/tusk/projects/herd/tools/runlog.py:59) and used the [Herdr skill](/home/tusk/.agents/skills/herdr/SKILL.md) to check installed CLI help. The notification syntax is confirmed; delivery and dismissal behavior were not exercised. Live `agent get` was denied by the sandbox's socket permissions, so the claimed absence of context fields remains **UNVERIFIED** independently here. Even if absent from that command, it would not establish that scraping is the only possible telemetry source. No builds, agents, notifications, or edits outside the discussion folder were made.

Next action: accept or counter row 2's record-based deduplication and revised 4/5 rating.

CONSENSUS: no — 2
