# Run recovery and loop scope (#32)

## Why

Step 0b of the OpenRig roadmap (`docs/openrig/ROADMAP.md`, row 0). Two defects
would leak into everything built later:

1. The run log cannot tell runs apart safely. Any `run-start` opens a new run
   even while another is open, so overlapping runs merge or split their events.
   Run ids are seconds-truncated timestamps. An open decision disappears from
   `status` the moment a new run starts.
2. `~/.claude/DEVLOOP.md` and the herd skill give contradictory rules, and
   neither says which one governs. Role cards generated later would encode the
   contradiction.

## What changes

- `run-start` is refused while the latest run has no `run-end`. The refusal
  names the open run and the exact command that closes it.
- New `runlog.py close --reason "<why>"` ends the open run after a crash with
  `run-end` text `closed: <why>`. Resuming a crashed run needs no command: the
  lead keeps appending to it.
- Every append holds an exclusive lock from reading the log to writing its
  line, so two concurrent starts cannot both succeed and an append that read
  the log before a `close` cannot land inside the next run.
- Run ids are unique: `run-start` timestamps carry microseconds, and a clash
  with an existing id gets a numeric suffix. `run` still equals the
  `run-start` event's `ts`.
- `status` keeps listing a `decision-needed` from an earlier run until a
  `decision-made` for the same issue appears, marked with the run it came from.
- New `session` kind records one agent's session outcome at start or recovery:
  `--agent` (pane agent name), `--role` (logical role), `--outcome`
  (`resumed | fresh | failed | unknown`).
- Scope lines: the herd skill says it governs `/herd` runs and wins where it
  differs from DEVLOOP. DEVLOOP says it governs delegated builds outside
  `/herd`. Operator ruling on #32, 2026-09-27.

## Grounded facts

- `tools/runlog.py:65`: `now = ...isoformat(timespec="seconds")`; `:67`:
  a `run-start` event's run id is `now`, so two starts in one second collide.
- `tools/runlog.py:66-72`: `append` accepts `run-start` at any time and binds
  every other event to the latest `run-start`. Nothing checks for an open run.
- `tools/runlog.py:49-52`: `latest` slices from the last `run-start`. `status`,
  `created` and `friction` read only that slice (`main`, `latest_run`).
- `tools/runlog.py:104-110`: open blocks and decisions are found only inside
  the events passed in, which is the latest run.
- `tools/merge_stack.py:189`: after the run's PRs merge, merge_stack appends a
  `note` to the log. That happens after the lead's `run-end`, so an event
  after `run-end` must still be accepted and belong to the ended run.
- At baseline `b07145e`, `tests/test_runlog.py:59-61` was the only test that
  started two runs in one repo, with no `run-end` between them. This change
  inserts `run-end` at line 61 (the second start moves to line 62) and adds
  the recovery cases.
- `/home/tusk/projects/project-mera/.git/herd/run-log.jsonl` (the only real
  log): 4 `run-start`, 4 `run-end`, last marker `run-end`, no duplicate run
  ids, so the new refusal does not block it.
- `~/.claude/DEVLOOP.md:41-44` (Gate A: operator approval authorizes the build)
  vs `skill/SKILL.md:301-310` (plan-review APPROVE is the authorization);
  `DEVLOOP.md:59` (cap 3 rounds) vs `SKILL.md:378` (cap 2, +1 on a ruling);
  `DEVLOOP.md:73-77` (the operator alone commits and pushes) vs
  `SKILL.md:319-337` (the lead pushes and opens the PR).
- `DEVLOOP.md` is not under version control, and `SKILL.md` never mentions
  DEVLOOP (`grep -n DEVLOOP skill/SKILL.md`: no match).

## Non-goals

- No change to how `latest` slices runs, or to `created` and `friction`:
  merge_stack and the librarian keep reading the latest run.
- Open `blocked` events are not carried across runs. A block belongs to a
  live agent, and that agent is gone once its run ends.
- `status` does not render `session` events. The monitor (#34) consumes them.
- No schema version on log lines, and no migration of existing logs.
- Roadmap row 0 also says "recovery carries the resolved binding". That part
  is deferred: persisting the resolved binding belongs to #38 (U1 resolver),
  and carrying it in recovery packets belongs to #40 (row C). This change
  records only each session's agent, role, and outcome, so it completes
  row 0 except for that clause.
- DEVLOOP's other content (roles, stages, handoff payload) is unchanged.

## Impact

`tools/runlog.py`, `tests/test_runlog.py`, `tests/test_skill_text.py`,
`skill/SKILL.md` (scope line + Run log section), and `~/.claude/DEVLOOP.md`
(one scope line, outside the repo).
