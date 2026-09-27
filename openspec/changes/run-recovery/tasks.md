# Tasks — run recovery and loop scope (#32)

Tier: **full**. There is a new mechanism (the lock and `close`) and a design
choice worth recording. Gates are measured on this branch at the spec commit.

## 1. Tests first (written; RED observed)

- [x] 1.1 `tests/test_runlog.py`: the two-run status test gets a `run-end`
  between its runs (setup only; its three assertions are unchanged).
- [x] 1.2 `tests/test_runlog.py`: new block `# --- #32: run recovery` —
  refused second start, start after end, `close` with reason, `close` with no
  open run (2 cases), `close` requires `--reason`, event after `run-end`, ids
  unique under a repeated clock, microsecond ids, 8-thread concurrent start,
  cross-run open decision, decision resolved in a later run, block not
  carried, `session` records, `session` needs `--role`, `--outcome` choices.
- [x] 1.3 `tests/test_skill_text.py`: the skill states it governs `/herd` runs
  over DEVLOOP.md, between its title and its intro paragraph.
- [x] 1.4 Plan review round 1 folds: the concurrent-start test collects every
  worker's result through futures and checks 8 results, 7 refusals naming the
  winning run; a new race regression (`test_an_append_that_read_the_log_before_a_close_cannot_land_in_the_next_run`);
  three-run fixed-clock ids `base`, `base+2`, `base+3`; sessions accepted for
  all four outcomes and refused for each missing field; an earlier or
  other-issue `decision-made` does not resolve a decision; `status` does not
  render sessions.
- [x] 1.5 RED after the fold: `python3 -m pytest -q tests/test_runlog.py
  tests/test_skill_text.py` → `21 failed, 32 passed`. Four new tests pass
  already, on purpose, as guards: `test_an_event_after_run_end_still_belongs_to_the_ended_run`,
  `test_a_block_is_not_carried_into_the_next_run`,
  `test_a_decision_made_before_the_question_does_not_resolve_it` (current
  behavior that must survive), and `test_a_decision_made_in_a_later_run_resolves_the_earlier_one`
  (it only gains force once cross-run carry exists). The split depends on the
  clock: `test_a_run_start_after_run_end_opens_a_new_run` can pass on the old
  code if its two starts straddle a second, which gives `20 failed, 33 passed`
  instead. The race test's helper thread warns until `close` exists.

## 2. Implementation — `tools/runlog.py`

- [ ] 2.1 Add `def now() -> datetime.datetime` (UTC) and use it in `append`.
  Ordinary events keep `timespec="seconds"`. `run-start` uses
  `timespec="microseconds"`.
- [ ] 2.2 Add `"session"` to KINDS; add `"role"` and `"outcome"` to FIELDS;
  `REQUIRED["session"] = ("agent", "role", "outcome")`; `--outcome` gets
  `choices=("resumed", "fresh", "failed", "unknown")`. Not a PROGRESS kind.
- [ ] 2.3 Add `open_run(events) -> dict | None`: the latest `run-start` if no
  `run-end` follows it, else None.
- [ ] 2.4 Add a context manager `locked(path)`: `fcntl.flock(LOCK_EX)` on
  `path.with_name("run-log.lock")`, creating the directory if missing. Never
  unlink the lock file. Split today's write into an internal `_write(path,
  event)` that assumes the lock is held.
- [ ] 2.5 Every `append` runs under `locked`, from reading the log (through
  `runlog.read_file`, the race test's seam) to `_write`. For `run-start`:
  If `open_run` is set, return `run <id> is still open (no run-end); close it
  with: runlog.py close --reason "<why>"`. Otherwise build the id from `now()`;
  while it is already a run id in the log, try `<id>+2`, `<id>+3`, … ; set
  both `ts` and `run` to the result, then append.
- [ ] 2.6 Add `def close(repo, reason, path=None) -> str | None`: under
  `locked`, read through `read_file`, refuse with `no open run` when
  `open_run` is None, else `_write` a `run-end` with `text = f"closed:
  {reason}"` for that run. It never calls the public `append` (a nested
  `flock` from a second `open()` would deadlock).
- [ ] 2.7 CLI: new subparser `close` with required `--reason`; exit 2 and print
  the refusal like `add` does.
- [ ] 2.8 `status(events, all_events=None)`: progress and blocks from `events`
  (the latest run), as today. Open decisions come from `all_events` when
  given: a `decision-needed` with no later `decision-made` for the same issue.
  One from an earlier run gets ` (from run <id>)`. `main` passes `read(repo)`
  as `all_events`. The librarian's call is unchanged.
- [ ] 2.9 Update the module docstring: one open run, `close`, events after
  `run-end`, `session`.

## 3. Skill and DEVLOOP text

- [ ] 3.1 `skill/SKILL.md`, a new paragraph between the H1 and "One session —
  **the lead, this one**":
  > This skill governs `/herd` runs. `~/.claude/DEVLOOP.md` governs delegated
  > builds outside `/herd`; where the two differ (who authorizes the spec, the
  > review-round cap, who pushes), this skill wins inside a `/herd` run
  > (operator ruling, #32).
- [ ] 3.2 `skill/SKILL.md` "Run log" section: add `session` to the checkpoint
  list; one sentence each on "a second `run-start` is refused while a run is
  open", "after a crash, resume by appending; end it with `runlog.py close
  --reason`", and "status keeps earlier runs' open decisions".
- [ ] 3.3 `~/.claude/DEVLOOP.md` (outside the repo, not versioned), a new
  paragraph after the intro:
  > Scope: this loop governs delegated builds outside `/herd`. A `/herd` run
  > follows `~/.claude/skills/herd/SKILL.md`, which wins where the two differ
  > (who authorizes the spec, the review-round cap, who pushes).
  Verified by reading the file back. No test covers it.

## 4. Gates

- [ ] 4.1 `python3 -m pytest -q` → all pass. Baseline on `main` at the spec
  commit: `221 passed`. Expected after the build: `221 + 25 new = 246 passed`
  (18 functions in the new block expanding to 24 cases: `close` with no open
  run ×2, session outcomes ×4, missing session fields ×3, the rest ×1 each;
  plus 1 skill-text test; the edited two-run and cross-run tests are not new).
  `--co` at the fold commit: `246 tests collected`. Wall time about 8 s.
- [ ] 4.2 `ruff check tools tests` → `All checks passed!` (the baseline).
- [ ] 4.3 mypy: not installed on this machine and not configured in
  `pyproject.toml`. Skipped, and the handoff says so.
- [ ] 4.4 `openspec validate run-recovery` passes.
