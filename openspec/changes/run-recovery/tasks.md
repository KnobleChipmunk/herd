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
  worker's result or exception from daemon threads and checks 8 results, 7 refusals naming the
  winning run; a lock regression (round 2 replaced the timing-based race test
  with `test_every_append_holds_the_lock_from_its_read_to_its_write`; round 3
  added `test_an_append_waits_out_brief_contention` and
  `test_an_append_gives_up_at_the_lock_deadline_not_before` on a controlled
  clock, a 60 s per-test alarm fixture, and daemon threads for the
  eight-thread test);
  three-run fixed-clock ids `base`, `base+2`, `base+3`; sessions accepted for
  all four outcomes and refused for each missing field; an earlier or
  other-issue `decision-made` does not resolve a decision; `status` does not
  render sessions.
- [x] 1.6 Pre-executed by the lead in a scratch worktree after plan-review APPROVE: GREEN
  `248 passed in 7.07s`; `ruff check tools tests` → `All checks passed!`; M1-M9 all
  KILLED by their named tests (section 5).
- [x] 1.5 RED after the round-3 fold: `python3 -m pytest -q tests/test_runlog.py
  tests/test_skill_text.py` → `23 failed, 32 passed`. Round 2 also corrected
  the cross-run test's #427 assertion to the latest progress event
  (`#427 decision-made another issue's answer`). Four new tests pass
  already, on purpose, as guards: `test_an_event_after_run_end_still_belongs_to_the_ended_run`,
  `test_a_block_is_not_carried_into_the_next_run`,
  `test_a_decision_made_before_the_question_does_not_resolve_it` (current
  behavior that must survive), and `test_a_decision_made_in_a_later_run_resolves_the_earlier_one`
  (it only gains force once cross-run carry exists). The split depends on the
  clock: `test_a_run_start_after_run_end_opens_a_new_run` can pass on the old
  code if its two starts straddle a second, which gives `22 failed, 33 passed`
  instead.

## 2. Implementation (byte-exact; generated from the lead's pre-executed tree)

Apply I1-I4 exactly. `tools/fencecheck.py` must print `FENCES OK (4 steps)`.

- [ ] **I1** `tools/runlog.py` — run recovery: bounded lock on every append, one open run, close, unique ids, cross-run decisions, session

REPLACE THE WHOLE FILE. Delete everything in it and write exactly this body (byte-exact, ends with one newline):

```python
"""The herd's run log: one JSON line per checkpoint, shared by every worktree of a repo.

usage: runlog.py add <kind> [--issue N] [--pr N] [--branch B] [--worktree W]
                 [--agent A] [--model M] [--round N] [--verdict V] [--text T]
                 [--role R] [--outcome resumed|fresh|failed|unknown] [--repo PATH]
       runlog.py close --reason WHY [--repo PATH]
       runlog.py status | created | friction | path [--repo PATH]

The log is <git common dir>/herd/run-log.jsonl: every worktree of the repo
resolves to the same file, `git clean` never touches it, and it can never be
committed. Lines are only appended. `run-start` opens a run; every later
event carries that run's id, including events after its `run-end` (merge_stack
appends its librarian note then). A second `run-start` is refused while the
latest run has no `run-end`; after a crash, keep appending to resume, or end
the run with `close --reason`. Every append holds `run-log.lock` from reading
the log to writing its line, and gives up after LOCK_TIMEOUT seconds. status,
created and friction read the latest run; status also lists decisions left
open by earlier runs. `session` records one agent's session outcome.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import fcntl
import json
import os
import pathlib
import sys
import time

from herdtool import git_common_dir

KINDS = ("run-start", "run-end", "spec-approved", "worktree-created", "branch-created", "scratch-created",
         "plan-review", "dispatched", "review-round", "ruling", "gate-miss", "lead-finding", "done", "blocked",
         "pr-opened", "fallback", "friction", "decision-needed", "decision-made", "note", "session")
REQUIRED = {"worktree-created": ("worktree",), "scratch-created": ("worktree",), "branch-created": ("branch",),
            "pr-opened": ("pr", "branch"), "friction": ("agent", "text"), "decision-needed": ("text",),
            "blocked": ("text",), "fallback": ("agent", "model"), "spec-approved": ("tier",),
            "plan-review": ("round", "verdict"), "review-round": ("round", "verdict"), "ruling": ("text",),
            "gate-miss": ("text",), "lead-finding": ("text",), "session": ("agent", "role", "outcome")}
# Events that move an issue forward; friction, fallbacks and notes are side channels.
PROGRESS = ("spec-approved", "plan-review", "worktree-created", "dispatched", "review-round", "done", "blocked",
            "pr-opened", "decision-needed", "decision-made")
FIELDS = ("issue", "pr", "branch", "worktree", "agent", "model", "tier", "round", "verdict", "text", "role",
          "outcome")
OUTCOMES = ("resumed", "fresh", "failed", "unknown")
LOCK_TIMEOUT = 30
LOCK_POLL = 0.01
_monotonic = time.monotonic
_sleep = time.sleep


def now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def log_path(repo: pathlib.Path) -> pathlib.Path:
    return git_common_dir(repo) / "herd" / "run-log.jsonl"


def read_file(path: pathlib.Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln] if path.exists() else []


def read(repo: pathlib.Path) -> list[dict]:
    return read_file(log_path(repo))


def latest(events: list[dict]) -> list[dict]:
    """The events of the last run: from its run-start to the end."""
    starts = [i for i, e in enumerate(events) if e["kind"] == "run-start"]
    return events[starts[-1]:] if starts else []


def latest_run(repo: pathlib.Path) -> list[dict]:
    return latest(read(repo))


def open_run(events: list[dict]) -> dict | None:
    """The latest run's `run-start` when no `run-end` follows it, else None."""
    run = latest(events)
    return run[0] if run and not any(e["kind"] == "run-end" for e in run) else None


@contextlib.contextmanager
def locked(path: pathlib.Path):
    """Hold run-log.lock next to `path`; raise TimeoutError after LOCK_TIMEOUT seconds of contention."""
    lock = path.with_name("run-log.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "a") as fh:
        deadline = _monotonic() + LOCK_TIMEOUT
        while True:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if _monotonic() >= deadline:
                    raise TimeoutError(f"run log is locked: {lock}") from None
                _sleep(LOCK_POLL)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _write(path: pathlib.Path, event: dict) -> None:
    """Append one line; the caller holds the lock."""
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, (json.dumps(event) + "\n").encode())
    finally:
        os.close(fd)


def unique_run_id(base: str, events: list[dict]) -> str:
    taken = {e.get("run") for e in events if e["kind"] == "run-start"}
    run, n = base, 1
    while run in taken:
        n += 1
        run = f"{base}+{n}"
    return run


def append(repo: pathlib.Path, kind: str, fields: dict, path: pathlib.Path | None = None) -> str | None:
    """Append one event to the repo's log (or to `path`); return why it was refused, or None."""
    path = path or log_path(repo)
    missing = [f for f in REQUIRED.get(kind, ()) if not fields.get(f)]
    if missing:
        return f"{kind} needs --{missing[0]}"
    try:
        with locked(path):
            events = read_file(path)
            stamp = now()
            if kind == "run-start":
                current = open_run(events)
                if current:
                    return (f"run {current['run']} is still open (no run-end); "
                            f'close it with: runlog.py close --reason "<why>"')
                ts = run = unique_run_id(stamp.isoformat(timespec="microseconds"), events)
            else:
                run_events = latest(events)
                if not run_events:
                    return "no run-start in the log; start a run first"
                ts = stamp.isoformat(timespec="seconds")
                run = run_events[0].get("run", ts)
            _write(path, {"ts": ts, "run": run, "kind": kind, **{k: v for k, v in fields.items() if v}})
    except TimeoutError:
        return f"run log is locked: {path.with_name('run-log.lock')}"
    return None


def close(repo: pathlib.Path, reason: str, path: pathlib.Path | None = None) -> str | None:
    """End the open run after a crash; return why it was refused, or None."""
    path = path or log_path(repo)
    try:
        with locked(path):
            current = open_run(read_file(path))
            if not current:
                return "no open run"
            _write(path, {"ts": now().isoformat(timespec="seconds"), "run": current["run"], "kind": "run-end",
                          "text": f"closed: {reason}"})
    except TimeoutError:
        return f"run log is locked: {path.with_name('run-log.lock')}"
    return None


def describe(e: dict) -> str:
    parts = [e["kind"]]
    if e.get("pr"):
        parts.append(f"PR #{e['pr']}")
    parts += [e[k] for k in ("branch", "agent", "model", "verdict", "text") if e.get(k)]
    return " ".join(parts)


def status(events: list[dict], all_events: list[dict] | None = None) -> list[str]:
    """Each issue's latest progress event (with its PR once opened), then what is still open.
    Blocks come from `events` (the latest run); decisions from `all_events` when given, so a
    decision an earlier run left open stays listed, marked with its run."""
    latest: dict[str, dict] = {}
    prs: dict[str, str] = {}
    for e in events:
        if e.get("issue") and e["kind"] in PROGRESS:
            latest[e["issue"]] = e
        if e["kind"] == "pr-opened":
            prs[e["issue"]] = e["pr"]
    lines = []
    for issue, e in latest.items():
        pr = f" [PR #{prs[issue]}]" if issue in prs and e["kind"] != "pr-opened" else ""
        lines.append(f"#{issue} {describe(e)}{pr} ({e['ts']})")
    current = events[0]["run"] if events else None
    for kind, closers, label, source in (("blocked", ("done", "pr-opened"), "blocked", events),
                                         ("decision-needed", ("decision-made",), "decision",
                                          events if all_events is None else all_events)):
        for i, e in enumerate(source):
            later = source[i + 1:]
            if e["kind"] == kind and not any(x["kind"] in closers and x.get("issue") == e.get("issue")
                                             for x in later):
                origin = f" (from run {e.get('run')})" if e.get("run") != current else ""
                lines.append(f"OPEN {label} #{e.get('issue', '?')}: {e['text']}{origin}")
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add")
    add.add_argument("kind", choices=KINDS)
    for f in FIELDS:
        add.add_argument(f"--{f}", **({"choices": OUTCOMES} if f == "outcome" else {}))
    sub.add_parser("close").add_argument("--reason", required=True)
    for name in ("status", "created", "friction", "path"):
        sub.add_parser(name)
    for p in sub.choices.values():
        p.add_argument("--repo", default=".")
    a = ap.parse_args(argv)
    repo = pathlib.Path(a.repo)
    if a.cmd == "add":
        why = append(repo, a.kind, {f: getattr(a, f) for f in FIELDS})
        if why:
            print(why)
            return 2
        return 0
    if a.cmd == "close":
        why = close(repo, a.reason)
        if why:
            print(why)
            return 2
        return 0
    if a.cmd == "path":
        print(log_path(repo))
        return 0
    events = latest_run(repo)
    if a.cmd == "status":
        out = status(events, read(repo))
    elif a.cmd == "created":
        out = [f"{e['kind']} #{e.get('issue', '?')} {e['worktree']} {e.get('branch', '')}".rstrip()
               for e in events if e["kind"] in ("worktree-created", "scratch-created")]
        out += [f"branch-created #{e.get('issue', '?')} {e['branch']}" for e in events if e["kind"] == "branch-created"]
    else:
        out = [f"#{e.get('issue', '?')} {e['agent']}: {e['text']}" for e in events if e["kind"] == "friction"]
    for ln in out:
        print(ln)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **I2** `skill/SKILL.md` — scope paragraph under the title

Find this exact text (it occurs exactly once):

```python
# Herd — the lead orchestrates, pi builds, Codex reviews

One session — **the lead, this one**
```

Replace it with exactly:

```python
# Herd — the lead orchestrates, pi builds, Codex reviews

This skill governs `/herd` runs. `~/.claude/DEVLOOP.md` governs delegated
builds outside `/herd`; where the two differ (who authorizes the spec, the
review-round cap, who pushes), this skill wins inside a `/herd` run
(operator ruling, #32).

One session — **the lead, this one**
```

- [ ] **I3** `skill/SKILL.md` — crash close and open-run rules in the Run log section

Find this exact text (it occurs exactly once):

```python
lead recovers from `runlog.py status` and live git/gh, not from memory.
```

Replace it with exactly:

```python
lead recovers from `runlog.py status` and live git/gh, not from memory.
A crashed run stays open: resume it by appending as usual, or end it with
`runlog.py close --reason "<why>"`. A second `run-start` is refused while
a run is open, and `status` keeps listing decisions an earlier run left
open, marked with that run's id (#32).
```

- [ ] **I4** `skill/SKILL.md` — session in the checkpoint list

Find this exact text (it occurs exactly once):

```python
`decision-made`, and `run-end`. These are the herd ledger's columns: a
```

Replace it with exactly:

```python
`decision-made`, `session` (with `--agent`, `--role` and `--outcome`
resumed | fresh | failed | unknown, whenever the lead starts, reuses or
recovers an agent), and `run-end`. These are the herd ledger's columns: a
```

## 3. Outside the repo (the lead, at PR time)

- [ ] 3.1 `~/.claude/DEVLOOP.md` (outside the repo, not versioned), a new
  paragraph after the intro:
  > Scope: this loop governs delegated builds outside `/herd`. A `/herd` run
  > follows `~/.claude/skills/herd/SKILL.md`, which wins where the two differ
  > (who authorizes the spec, the review-round cap, who pushes).
  Verified by reading the file back. No test covers it.

## 4. Gates

- [ ] 4.1 `python3 -m pytest -q` → all pass. Baseline on `main` at the spec
  commit: `221 passed`. Expected after the build: `221 + 27 new = 248 passed`
  (20 test functions in the new block expanding to 26 cases: `close` with no
  open run ×2, session outcomes ×4, missing session fields ×3, the rest ×1
  each; `lock_is_held` and the `bounded` fixture are not tests; plus 1
  skill-text test; the edited two-run and cross-run tests are not new). `--co`
  at the round-3 fold: `248 tests collected`. Wall time about 8 s.
- [ ] 4.2 `ruff check tools tests` → `All checks passed!` (the baseline).
- [ ] 4.3 mypy: not installed on this machine and not configured in
  `pyproject.toml`. Skipped, and the handoff says so.
- [ ] 4.4 `openspec validate run-recovery` passes.

## 5. Mutations

Drive with `python3 tools/mutate.py openspec/changes/run-recovery/tasks.md <tree>`.
Every one must be KILLED. M1 is killed by the 60 s alarm; M5 by the 30 s lock timeout.

- [ ] **M1** in `tools/runlog.py`: replace

```python
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
```

with

```python
                fcntl.flock(fh, fcntl.LOCK_EX)
```

Killer: `tests/test_runlog.py::test_an_append_waits_out_brief_contention`

- [ ] **M2** in `tools/runlog.py`: replace

```python
        with locked(path):
            events = read_file(path)
```

with

```python
        with (locked(path) if kind == "run-start" else contextlib.nullcontext()):
            events = read_file(path)
```

Killer: `tests/test_runlog.py::test_every_append_holds_the_lock_from_its_read_to_its_write`

- [ ] **M3** in `tools/runlog.py`: replace

```python
            except BlockingIOError:
                if _monotonic() >= deadline:
```

with

```python
            except BlockingIOError:
                if True:
```

Killer: `tests/test_runlog.py::test_an_append_waits_out_brief_contention`

- [ ] **M4** in `tools/runlog.py`: replace

```python
        deadline = _monotonic() + LOCK_TIMEOUT
        while True:
            try:
```

with

```python
        while True:
            deadline = _monotonic() + LOCK_TIMEOUT
            try:
```

Killer: `tests/test_runlog.py::test_an_append_gives_up_at_the_lock_deadline_not_before`

- [ ] **M5** in `tools/runlog.py`: replace

```python
            _write(path, {"ts": now().isoformat(timespec="seconds"), "run": current["run"], "kind": "run-end",
                          "text": f"closed: {reason}"})
```

with

```python
            why = append(repo, "run-end", {"text": f"closed: {reason}"}, path=path)
            if why:
                return why
```

Killer: `tests/test_runlog.py::test_every_append_holds_the_lock_from_its_read_to_its_write`

- [ ] **M6** in `tools/runlog.py`: replace

```python
    while run in taken:
        n += 1
        run = f"{base}+{n}"
```

with

```python
    if run in taken:
        run = f"{base}+2"
```

Killer: `tests/test_runlog.py::test_run_ids_are_unique_even_when_the_clock_repeats`

- [ ] **M7** in `tools/runlog.py`: replace

```python
            later = source[i + 1:]
```

with

```python
            later = source
```

Killer: `tests/test_runlog.py::test_a_decision_made_before_the_question_does_not_resolve_it`

- [ ] **M8** in `tools/runlog.py`: replace

```python
PROGRESS = ("spec-approved",
```

with

```python
PROGRESS = ("session", "spec-approved",
```

Killer: `tests/test_runlog.py::test_status_does_not_render_session_events`

- [ ] **M9** in `tools/runlog.py`: replace

```python
                current = open_run(events)
                if current:
```

with

```python
                current = None
                if current:
```

Killer: `tests/test_runlog.py::test_a_second_run_start_is_refused_while_a_run_is_open`
