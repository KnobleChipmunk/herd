"""The herd's run log: one JSON line per checkpoint, shared by every worktree of a repo.

usage: runlog.py add <kind> [--issue N] [--pr N] [--branch B] [--worktree W]
                 [--agent A] [--model M] [--round N] [--verdict V] [--text T]
                 [--role R] [--outcome resumed|fresh|failed|unknown]
                 [--reason resource|peer|environment|auth|rate-limit|scheduled|other] [--tab TAB] [--repo PATH]
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
         "pr-opened", "fallback", "friction", "decision-needed", "decision-made", "note", "session", "wait")
REQUIRED = {"worktree-created": ("worktree",), "scratch-created": ("worktree",), "branch-created": ("branch",),
            "pr-opened": ("pr", "branch"), "friction": ("agent", "text"), "decision-needed": ("issue", "text"),
            "blocked": ("text",), "fallback": ("agent", "model"), "spec-approved": ("tier",),
            "plan-review": ("round", "verdict"), "review-round": ("round", "verdict"), "ruling": ("text",),
            "gate-miss": ("text",), "lead-finding": ("text",), "session": ("agent", "role", "outcome"),
            "wait": ("issue", "reason")}
# Events that move an issue forward; friction, fallbacks and notes are side channels.
PROGRESS = ("spec-approved", "plan-review", "worktree-created", "dispatched", "review-round", "done", "blocked",
            "pr-opened", "decision-needed", "decision-made", "wait")
FIELDS = ("issue", "pr", "branch", "worktree", "agent", "model", "tier", "round", "verdict", "text", "role",
          "outcome", "reason", "tab")
OUTCOMES = ("resumed", "fresh", "failed", "unknown")
# Why an issue is deliberately waiting; any later progress event for the issue ends the wait (#33).
WAIT_REASONS = ("resource", "peer", "environment", "auth", "rate-limit", "scheduled", "other")
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


def open_decision(events: list[dict], issue: str) -> dict | None:
    """The issue's decision-needed that no later decision-made answers, if any."""
    for i, e in enumerate(events):
        if e["kind"] == "decision-needed" and e.get("issue") == issue and not any(
                x["kind"] == "decision-made" and x.get("issue") == issue for x in events[i + 1:]):
            return e
    return None


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
                if kind == "decision-needed" and open_decision(events, fields["issue"]):
                    return (f"#{fields['issue']} already has an open decision: "
                            f"{open_decision(events, fields['issue'])['text']}; record its decision-made first")
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
        add.add_argument(f"--{f}", **({"choices": OUTCOMES} if f == "outcome" else
                                      {"choices": WAIT_REASONS} if f == "reason" else {}))
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
