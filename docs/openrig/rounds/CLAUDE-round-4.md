# Claude — round 4 (written independently, before reading CODEX-round-4.md)

Sources checked beyond the report: openrig.dev/tour/workflow, /tour/queue,
/tour/context, /docs/tui (fetched); /docs/architecture returned 404, so I
shallow-cloned github.com/mvschwarz/openrig into
`../openrig-src/` and read the as-built docs. Paths below are in that clone.

## Adjustments to existing rows

**X — tool-enforced transitions. Rating 5, scope sharpened.**
Verified: `update --state done` REQUIRES `--closure-reason` from
`handed_off_to | blocked_on | denied | canceled | no-follow-on | escalation`;
the three routed ones also require `--closure-target`
(docs/as-built/cli-reference.md:1307-1308). `handoff` is "transactional
close-as-handed-off + create-new" (:1281). Workflows: `rig workflow project`
takes packet, exit, evidence; "OpenRig does not judge whether a step is
complete" (tour/workflow). So X should mean: every terminal event carries a
reason from a closed set (+ target when routed), a handoff is one append
that closes and opens, a transition names its evidence path — and the tool
never judges quality. That matches our "narrow tool enforcement".

**1a + 2 + W — adopt OpenRig's state taxonomy. W 4 → 5, and fold W into
the row-2 watcher (one process, one rule set).**
docs/reference/agent-state-taxonomy.md defines three orthogonal axes
(session / activity / resumability), needs-input as `{count, reason}` with
reasons like "permission prompt", "usage limit", and derived diagnoses:
- PARKED = (idle-at-prompt OR needs-input) × open obligations — "a dropped
  baton or an unanswered block". This IS herd's stall rule ("a builder that
  settles without DONE or BLOCKED has stalled", herd SKILL.md:531-534).
- HELD = deliberate stop with a named owner and an armed wake — maps to a
  parked issue with `decision-needed`; must NOT alarm as PARKED.
- DONE-UNSEEN = idle ∧ unseen, credited to herdr's own derivation.
The doc reconciles itself against herdr's states line by line
(`src/detect/mod.rs:11`). We can copy the vocabulary almost verbatim: herdr
state × run-log open obligations → PARKED / HELD / DONE-UNSEEN / needs-input.
That gives the watcher and the monitor one shared, tested rule. Also:
"usage limit" as a needs-input reason covers the 09-21 stops and probe.py
fallbacks.

**1b — context % column. 2 → 3 for Claude-harness seats only.**
OpenRig does not scrape: its Claude collector is a Claude Code `statusLine`
command plus activity hooks that write context/token usage
(openrig-src/README.md:86,104). Claude Code passes context-window data to
the statusLine command as JSON, so a statusLine command that also writes
`{session, context_used, ts}` to a file is a supported source. Codex and pi
seats stay "unknown". Side effect: it measures the LEAD's context, which is
the evidence row 7b said it lacked.

**7b — delegate pre-execution. Stays 2**, but becomes re-decidable once
1b records lead context across a few runs.

**6b — delivery queue. Stays 2.** If ever built, copy OpenRig's claim
step: notification, then the receiver claims the id, pending → in-progress
(tour/queue). The claim IS the acknowledgment we said was the unproven gap.

**H — stays 4 / 2.** One unverified gap from round 1 closes: OpenRig ships
a Pi runtime adapter (`runtime: pi`, CHANGELOG.md:925), so the pi builder
is not a blocker. The single-controller conflict still decides it.

## New rows

| # | Implementation | Proposed | Order |
|---|---|---|---|
| N1 | Message vs owned-work rule in the shared contract/role cards: `herdr agent prompt` for questions (no owner); anything that must be done becomes a run-log/manifest item with an owner (tour/send, tour/queue draw this exact line) | 4 | with 3 |
| N2 | Lead restore packet after compaction: generated from `runlog.py status` + the ticket PROGRESS.md files, loaded by a compaction/SessionStart hook. OpenRig ships a "seat-scoped post-compaction restore packet" for Claude seats (CHANGELOG.md:1167); herd already says "recover from runlog status" but relies on the lead remembering to | 4 | after 5 |
| N3 | Addressable decisions: lead rulings written under stable anchors in design.md (`design.md#ruling-<slug>`), reviewer prompts cite the anchor instead of pasting prose (tour/context `rig context get file#section`) | 2 | defer — herd's "Lead ruling: X OUT OF SCOPE, do not re-raise" already works |

## Contradictions with rounds 1–3 / the video

- Video: workflows are "deterministic rails the daemon enforces". Site:
  the daemon records transitions and does not judge them. Our X already
  assumed the narrower version; no change needed.
- Video: the watchdog "can keep agents awake for weeks". Repo: shipped
  policies are `periodic-reminder`, `artifact-pool-ready`,
  `edge-artifact-required`; `workflow-keepalive` is "rejected with
  policy_deferred_to_phase_d" (cli-reference.md:1407). Supports our
  "no keep-awake prompts" in W.
- Report cites openrig.dev/docs/architecture — that URL 404s today.

## Proposed order

0 → 2(+W, taxonomy) + 1a → 5 + 6a → N2 → 3 + N1 + 4 → X → 1b.
Deferred: 6b, 7b (revisit with 1b data), N3.
