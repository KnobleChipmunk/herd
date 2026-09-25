"""The herd's run log: one JSON line per checkpoint, shared by every worktree of a repo.

usage: runlog.py add <kind> [--issue N] [--pr N] [--branch B] [--worktree W]
                 [--agent A] [--model M] [--round N] [--verdict V] [--text T] [--repo PATH]
       runlog.py status | created | friction | path [--repo PATH]

The log is <git common dir>/herd/run-log.jsonl: every worktree of the repo
resolves to the same file, `git clean` never touches it, and it can never be
committed. Lines are only appended. `run-start` opens a run; every later
event carries that run's id. status, created and friction read the latest run.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import sys

from herdtool import git_common_dir

KINDS = ("run-start", "run-end", "spec-approved", "worktree-created", "branch-created", "scratch-created",
         "dispatched", "review-round", "done", "blocked", "pr-opened", "fallback", "friction",
         "decision-needed", "decision-made", "note")
REQUIRED = {"worktree-created": ("worktree",), "scratch-created": ("worktree",), "branch-created": ("branch",),
            "pr-opened": ("pr", "branch"), "friction": ("agent", "text"), "decision-needed": ("text",),
            "blocked": ("text",), "fallback": ("agent", "model")}
# Events that move an issue forward; friction, fallbacks and notes are side channels.
PROGRESS = ("spec-approved", "worktree-created", "dispatched", "review-round", "done", "blocked", "pr-opened",
            "decision-needed", "decision-made")
FIELDS = ("issue", "pr", "branch", "worktree", "agent", "model", "round", "verdict", "text")


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


def append(repo: pathlib.Path, kind: str, fields: dict) -> str | None:
    """Append one event; return why it was refused, or None."""
    missing = [f for f in REQUIRED.get(kind, ()) if not fields.get(f)]
    if missing:
        return f"{kind} needs --{missing[0]}"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    if kind == "run-start":
        run = now
    else:
        run_events = latest_run(repo)
        if not run_events:
            return "no run-start in the log; start a run first"
        run = run_events[0]["run"]
    event = {"ts": now, "run": run, "kind": kind, **{k: v for k, v in fields.items() if v}}
    path = log_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, (json.dumps(event) + "\n").encode())
    finally:
        os.close(fd)
    return None


def describe(e: dict) -> str:
    parts = [e["kind"]]
    if e.get("pr"):
        parts.append(f"PR #{e['pr']}")
    parts += [e[k] for k in ("branch", "agent", "model", "verdict", "text") if e.get(k)]
    return " ".join(parts)


def status(events: list[dict]) -> list[str]:
    """Each issue's latest progress event (with its PR once opened), then what is still open."""
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
    for kind, closers, label in (("blocked", ("done", "pr-opened"), "blocked"),
                                 ("decision-needed", ("decision-made",), "decision")):
        for i, e in enumerate(events):
            later = events[i + 1:]
            if e["kind"] == kind and not any(x["kind"] in closers and x.get("issue") == e.get("issue")
                                             for x in later):
                lines.append(f"OPEN {label} #{e.get('issue', '?')}: {e['text']}")
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add")
    add.add_argument("kind", choices=KINDS)
    for f in FIELDS:
        add.add_argument(f"--{f}")
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
    if a.cmd == "path":
        print(log_path(repo))
        return 0
    events = latest_run(repo)
    if a.cmd == "status":
        out = status(events)
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
