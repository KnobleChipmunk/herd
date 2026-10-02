# duplicate-mechanism-late-finding

Status: accepted

## Class

duplicate-mechanism-late-finding — duplicate mechanism found late, after plan review

Event lines, quoted from the ledger:

- 2026-10-02 project-mera #502 (linux): PR 2's third Node page runner (round 1) and PR 1's second atomic JSON writer (final review) both slipped past plan review, each producing a prerequisite PR (H, P0) and a rebuild of the stack.
- 2026-10-02 project-mera #502 (linux): the atomic-writer and node-runner duplicates surfaced late (final review and PR 2 plan review), each costing a prerequisite PR and a rebuild of everything stacked above.

## Proposed change

Add a mandatory One-copy grep to the lead's pre-execution brief and the plan-review card, run before dispatch (not at final review). For every helper the plan extracts or adds, the lead greps the repo for an existing implementation and records, in the brief, each match and the plan's disposition: reuse, hoist in a prerequisite PR, or exclude with a stated behavioral difference. The plan-review card's round-1 checklist should include "for each new helper in the plan, name the existing copy (if any) and the plan's disposition" as a required line. This is a skill change (plan-review card + pre-execution brief) plus a one-line checklist item; the grep itself is already in the lead's skill (One-copy invariant), the gap is that it runs at final review rather than before dispatch.

The 502 lead's retro item 1 names the exact fix: "a plan-time checklist item — 'for every helper the plan extracts or adds, grep the repo for an existing one' — would have caught both before pre-execution."

## Prediction

No `duplicate-mechanism-late-finding` events in the next run's friction lines: the pre-execution brief records each new helper's existing-copy disposition, so a duplicate is caught before the first build brief is sent and does not produce a mid-stack prerequisite PR.
