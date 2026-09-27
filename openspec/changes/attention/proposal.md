# Attention watcher and monitor (#33, #34)

## Why

Roadmap step 1 (`docs/openrig/ROADMAP.md`, rows 2 and 1a). Today the operator
learns that a run needs a human only by reading panes: the 09-21 run waited
overnight on questions nobody saw. There is no single view of every agent and
ticket either.

## What changes

- New `tools/attention.py`, one rule set used by two commands:
  - `watch` sends a Herdr notification (and, with `--ntfy <url>`, a push) once
    per operator item: an open decision (from any run), a permission dialog
    (one per blocked episode), ready PRs (batched), a stalled run; run end is
    sent without a sound. A worker block the lead has not ruled on is the
    lead's and is never sent.
  - `monitor` prints every agent in the Herdr workspace (marking ones outside
    the run's tab), each issue's latest progress with its age, and a NEEDS YOU
    section. `scan` prints the items once (`--json` for tools).
- Stall rule (OpenRig's PARKED vs HELD): work in flight, nobody in the run's
  tab working, no agent there of unknown or blocked state, log quiet for 20
  min. An issue waiting on the operator is HELD: its decision alert stays, and
  it never raises a stall. DONE-UNSEEN (idle, unseen) is not attention.
- Dedup: each item's key is the log record's byte offset plus a hash of the
  line (a replaced log cannot suppress a new alert at a reused offset), or the
  pane and its Herdr `state_change_seq` for a blocked episode. Sent keys live in
  `<git common dir>/herd/attention-state.json`.
- Plan review round 1 (11 findings, all folded; three narrowed by lead
  ruling, recorded in the run log):
  - `tools/runlog.py`: a `wait` kind (`--issue`, `--reason
    resource|peer|environment|auth|rate-limit|scheduled|other`), ended by the
    issue's next progress event, so a deliberate wait is not a stall; and one
    open decision per issue, enforced at record time (`decision-needed` needs
    `--issue`; a second open one is refused).
  - Stall eligibility follows the issue's latest *work* event, so answering a
    decision makes unfinished work eligible again.
  - A failed `herdr agent list`, or an unknown run tab, claims nothing about
    who is working. The watcher records the run tab; `scan` and `monitor` use it.
  - One watcher per repository (a lock held for its lifetime). An item counts
    as sent only when Herdr reports it shown; a dropped one is retried; ntfy is
    best effort and never stops the watcher; state is written atomically.
  - The monitor adds pane, association, binding (`unknown` until #38), the
    observation time, the worktree as evidence, and a LEAD section.
- `skill/SKILL.md` Monitoring: the lead starts `attention.py watch` at
  run-start; `runlog.py add wait` for deliberate waits; the operator runs
  `attention.py monitor` in any pane.

## Grounded facts

- `herdr agent list` returns per agent: `agent`, `agent_status`
  (idle/working/blocked/done/unknown), `name`, `pane_id`, `tab_id`,
  `state_change_seq`, among others (read live, 2026-09-27).
- `herdr notification show <title> [--body TEXT] [--sound none|done|request]`
  (`herdr notification` help, 2026-09-27). It prints JSON and exits 0 even when
  it drops the notification: observed live 2026-09-27,
  `{"result":{"reason":"rate_limited","shown":false,...}}`. Success is
  `result.shown == true`.
- Herdr's own states: `blocked` = an approval or question UI; `done` = idle and
  unseen (herdr skill, "Understand layout, panes, and agents").
- `tools/runlog.py` at #32: `latest`, `PROGRESS`, `describe`, `log_path`; the
  `session` kind carries `agent` and `role`.
- OpenRig `docs/reference/agent-state-taxonomy.md` (mvschwarz/openrig f137f11):
  PARKED = idle or needs-input with open obligations; HELD = deliberate stop
  with a named owner; DONE-UNSEEN is not completion.

## Non-goals

- No agent-level obligation tracking beyond the run log: until tickets (#36)
  record owners, a stall is diagnosed per run, not per agent.
- No automatic wake-ups or keep-awake prompts (roadmap row 2).
- No notification dismissal: Herdr has no clear command; the monitor is the
  persistent view.
- No context % column (#41).

## Impact

New `tools/attention.py`, `tests/test_attention.py`; edits to
`tools/runlog.py`, `tests/test_runlog.py`, `skill/SKILL.md`,
`tests/test_skill_text.py`, `pyproject.toml` (isort first-party list). Depends on #32 (branch stacked on `feat/32-run-recovery`).
