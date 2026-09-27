# Tickets agents can use, and a page per ticket (#36, #37)

## Why

Roadmap step 3 (rows 6a, X-ownership, 5). Owned work between agents travels as
`herdr agent prompt` text; nobody can list who owns what, whether it was picked
up, or why it closed. The #35 evaluation decided to build this in herd and copy
three contracts from OpenRig's `rig queue` (docs/openrig-evaluation.md).

## What changes

- New `tools/tickets.py`, an append-only store at `<git common dir>/herd/tickets.jsonl`
  (shared by every worktree and run): `create`, `claim`, `block`, `close`,
  `handoff`, `check`, `list`, `show`, `page`, `pages`.
- Contracts from `rig queue` (openrig `docs/as-built/cli-reference.md:1272-1312`):
  a ticket stays pending until its owner claims it; it closes only with a reason
  from a closed set (`no-follow-on | denied | canceled | superseded | escalation`, plus
  `handed_off_to` from `handoff`; `block` records `blocked_on` and keeps it open);
  a routed reason names its target; `handoff` closes one ticket and opens its
  successor in one write.
- Only the owner may claim, block, close or hand off; anyone may record a check.
  Owners, actors and targets must not be blank (plan review round 1).
- A handoff is ONE record that closes the ticket and opens its successor; a
  line counts only with its newline, an interrupted last line is ignored and
  dropped (atomic rewrite) before the next write, and appends are fsynced.
- A check can name its candidate (commit or tree); a pass must. The verdict is
  `PASS on <candidate>` only when every check passed on one candidate.
- Every write holds #32's run-log lock from reading the store to writing.
- `page <id>` writes `<git common dir>/herd/tickets/<id>.md` from the records:
  owner, state, parent, verdict, checks, history, and the parent issue's run-log
  events. The verdict is PASS only when every recorded check passed; an omitted,
  blocked, failed or unchecked one makes it NOT PASS.
- `skill/SKILL.md`: a Tickets section with the rule "a question goes as a
  message; owned work goes as a ticket".

## Grounded facts

- `runlog.locked(path)` locks `path.with_name("run-log.lock")` and times out
  after `LOCK_TIMEOUT` (#32, `tools/runlog.py`); the tickets store sits beside
  the run log, so both share one lock.
- `runlog.read`, `runlog.describe` and `runlog.log_path` exist at #32.
- OpenRig closure reasons: `handed_off_to, blocked_on, denied, canceled,
  no-follow-on, escalation`; routed ones require a target
  (openrig `cli-reference.md:1307-1308`); `handoff` is transactional (`:1281`).

## Non-goals

- No automatic ticket creation from the run log, and no change to how the lead
  dispatches today: the loop adopts tickets when #40's role cards use them.
- No delivery acknowledgment or retries beyond `claim` (row 6b, 2/5).
- No per-agent stall diagnosis in `attention.py` yet (it can read tickets later).

## Impact

New `tools/tickets.py`, `tests/test_tickets.py`; edits to `skill/SKILL.md`,
`tests/test_skill_text.py`, `pyproject.toml`. Stacked on `feat/33-attention`.
