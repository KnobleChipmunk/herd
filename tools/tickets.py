"""Tickets agents can use, and one Markdown page per ticket (#36, #37).

usage: tickets.py create  --title T --to OWNER --by WHO [--parent ISSUE] [--repo PATH]
       tickets.py claim   ID --by OWNER
       tickets.py block   ID --by OWNER --on WHO --text WHY
       tickets.py close   ID --by OWNER --reason no-follow-on|denied|canceled|superseded|escalation [--target WHO]
       tickets.py handoff ID --by OWNER --to NEW_OWNER [--title T]
       tickets.py check   ID --by WHO --name NAME --status pass|fail|not-checked|blocked|omitted
                          [--candidate COMMIT] [--text WHY] [--evidence PATH]   (a pass needs --candidate)
       tickets.py list [--all] | show ID | page ID | pages

Owned work lives here; questions go as `herdr agent prompt` messages. The store
is <git common dir>/herd/tickets.jsonl, append-only, one event per line, shared
by every worktree and every run. Every write holds the run log's lock from
reading the store to writing, so a handoff closes one ticket and opens its
successor in one record (a line is complete only with its newline; an
incomplete last line from a crash is ignored when read and dropped, by an
atomic rewrite, before the next write). The contracts are copied from OpenRig's `rig queue`
(docs/openrig-evaluation.md): a ticket stays pending until its owner claims
it; it closes only with a reason from a closed set (handed_off_to comes from
handoff, blocked_on from block, which keeps the ticket open); a routed reason
names its target. A page is generated from the records at
<git common dir>/herd/tickets/<ID>.md; the verdict is PASS only when every
recorded check passed on one named candidate (commit or tree id). Owners,
actors and targets must not be blank.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import sys

import runlog

CLOSE_REASONS = ("no-follow-on", "denied", "canceled", "superseded", "escalation")
CHECK_STATUSES = ("pass", "fail", "not-checked", "blocked", "omitted")


def path(repo: pathlib.Path) -> pathlib.Path:
    return runlog.log_path(repo).with_name("tickets.jsonl")


def page_path(repo: pathlib.Path, tid: str) -> pathlib.Path:
    return runlog.log_path(repo).parent / "tickets" / f"{tid}.md"


def read(p: pathlib.Path) -> list[dict]:
    """Complete records only: text after the last newline is an interrupted write."""
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text().split("\n")[:-1] if ln]


def fold(events: list[dict]) -> dict[str, dict]:
    """Every ticket's current state, derived from its events in order."""
    out: dict[str, dict] = {}
    for e in events:
        tid, op = e["ticket"], e["op"]
        if op == "create":
            out[tid] = {"title": e["title"], "owner": e["owner"], "state": "pending", "parent": e.get("parent"),
                        "after": e.get("after"), "reason": None, "target": None, "checks": {}, "history": []}
        if op == "handoff":
            out[e["successor"]] = {"title": e["title"], "owner": e["to"], "state": "pending", "parent": e.get("parent"),
                                   "after": tid, "reason": None, "target": None, "checks": {}, "history": [e]}
            out[tid].update(state="closed", reason="handed_off_to", target=e["to"])
        t = out[tid]
        if op == "claim":
            t.update(state="in-progress", reason=None, target=None)
        elif op == "block":
            t.update(state="blocked", reason="blocked_on", target=e["on"])
        elif op == "close":
            t.update(state="closed", reason=e["reason"], target=e.get("target"))
        elif op == "check":
            t["checks"][e["name"]] = {"status": e["status"], "text": e.get("text"), "evidence": e.get("evidence"),
                                      "candidate": e.get("candidate")}
        t["history"].append(e)
    return out


def load(repo: pathlib.Path) -> dict[str, dict]:
    return fold(read(path(repo)))


def _write_fully(fd: int, data: bytes) -> None:
    while data:
        data = data[os.write(fd, data):]
    os.fsync(fd)


def _sync_dir(d: pathlib.Path) -> None:
    fd = os.open(d, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_all(p: pathlib.Path, events: list[dict]) -> None:
    """Append records durably; the caller holds the lock. An incomplete last line (a crashed write) is
    dropped first: the complete lines go to a synced temporary file that is renamed over the store,
    and the directory is synced. A newly created store also syncs its directory."""
    existed = p.exists()
    if existed:
        data = p.read_bytes()
        if data and not data.endswith(b"\n"):
            tmp = p.with_suffix(".tmp")
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
            try:
                _write_fully(fd, data[:data.rfind(b"\n") + 1])
            finally:
                os.close(fd)
            os.replace(tmp, p)
            _sync_dir(p.parent)
    fd = os.open(p, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        _write_fully(fd, "".join(json.dumps(e) + "\n" for e in events).encode())
    finally:
        os.close(fd)
    if not existed:
        _sync_dir(p.parent)


def stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def transact(repo: pathlib.Path, build) -> tuple[str | None, list[dict]]:
    """Under the lock: read the store, let `build(events, state)` return (refusal, new events), write them."""
    p = path(repo)
    try:
        with runlog.locked(p):
            events = read(p)
            why, new = build(events, fold(events))
            if why:
                return why, []
            _write_all(p, new)
            return None, new
    except TimeoutError:
        return f"run log is locked: {p.with_name('run-log.lock')}", []


def owned(state: dict, tid: str, by: str) -> str | None:
    if tid not in state:
        return f"no ticket {tid}"
    if state[tid]["state"] == "closed":
        return f"{tid} is closed"
    if state[tid]["owner"] != by:
        return f"{tid} is owned by {state[tid]['owner']}"
    return None


def next_id(events: list[dict]) -> str:
    return f"T{sum(e['op'] in ('create', 'handoff') for e in events) + 1}"


def create(events, state, a) -> tuple[str | None, list[dict]]:
    tid = next_id(events)
    return None, [{"ts": stamp(), "ticket": tid, "op": "create", "by": a.by, "title": a.title, "owner": a.to,
                   **({"parent": a.parent} if a.parent else {})}]


def claim(events, state, a):
    why = owned(state, a.id, a.by)
    if not why and state[a.id]["state"] not in ("pending", "blocked"):
        why = f"{a.id} is {state[a.id]['state']}, not pending or blocked"
    return why, [{"ts": stamp(), "ticket": a.id, "op": "claim", "by": a.by}]


def block(events, state, a):
    return owned(state, a.id, a.by), [{"ts": stamp(), "ticket": a.id, "op": "block", "by": a.by, "on": a.on,
                                       "text": a.text}]


def close(events, state, a):
    why = owned(state, a.id, a.by) or (f"{a.reason} needs --target" if a.reason == "escalation" and not a.target
                                       else None)
    return why, [{"ts": stamp(), "ticket": a.id, "op": "close", "by": a.by, "reason": a.reason,
                  **({"target": a.target} if a.target else {})}]


def handoff(events, state, a):
    why = owned(state, a.id, a.by)
    if why:
        return why, []
    old = state[a.id]
    return None, [{"ts": stamp(), "ticket": a.id, "op": "handoff", "by": a.by, "to": a.to,
                   "successor": next_id(events), "title": a.title or old["title"],
                   **({"parent": old["parent"]} if old["parent"] else {})}]


def check(events, state, a):
    why = None if a.id in state else f"no ticket {a.id}"
    if not why and a.status == "pass" and not a.candidate:
        why = "a pass needs --candidate (the commit or tree it was measured on)"
    return why, [{"ts": stamp(), "ticket": a.id, "op": "check", "by": a.by, "name": a.name, "status": a.status,
                  **({"text": a.text} if a.text else {}), **({"evidence": a.evidence} if a.evidence else {}),
                  **({"candidate": a.candidate} if a.candidate else {})}]


def verdict(checks: dict) -> str:
    if not checks:
        return "NO CHECKS"
    if not all(c["status"] == "pass" for c in checks.values()):
        return "NOT PASS"
    candidates = sorted({c["candidate"] for c in checks.values() if c["candidate"]})
    if len(candidates) > 1:
        return f"NOT PASS (checks on different candidates: {', '.join(candidates)})"
    return f"PASS on {candidates[0]}"


def history_line(e: dict) -> str:
    what = {"create": "created", "claim": "claimed", "check": f"check {e.get('name')}: {e.get('status')}",
            "handoff": f"handed off to {e.get('to')} as {e.get('successor')}",
            "block": f"blocked on {e.get('on')}", "close": f"closed ({e.get('reason')}"
            + (f" → {e['target']}" if e.get("target") else "") + ")"}[e["op"]]
    detail = f" — {e['text']}" if e.get("text") else ""
    return f"- {e['ts']} {what} by {e['by']}{detail}"


def render(repo: pathlib.Path, tid: str, t: dict) -> str:
    lines = [f"# {tid} — {t['title']}", "",
             f"Owner: {t['owner']} · State: {t['state']} · Parent: " + (f"#{t['parent']}" if t["parent"] else "—")
             + (f" · After: {t['after']}" if t["after"] else ""),
             f"Verdict: {verdict(t['checks'])}", "", "## Checks", "",
             "| Check | Status | Candidate | Evidence | Note |", "|---|---|---|---|---|"]
    lines += [f"| {n} | {c['status']} | {c['candidate'] or ''} | {c['evidence'] or ''} | {c['text'] or ''} |"
              for n, c in t["checks"].items()]
    lines += ["", "## History", ""] + [history_line(e) for e in t["history"]]
    if t["parent"]:
        issue_events = [e for e in runlog.read(repo) if e.get("issue") == t["parent"]]
        lines += ["", f"## Run log (#{t['parent']})", ""] + [f"- {e['ts']} {runlog.describe(e)}" for e in issue_events]
    return "\n".join(lines) + "\n"


def write_page(repo: pathlib.Path, tid: str, t: dict) -> None:
    p = page_path(repo, tid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render(repo, tid, t))


def nonblank(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("must not be blank")
    return value


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create")
    c.add_argument("--title", required=True, type=nonblank)
    c.add_argument("--to", required=True, type=nonblank)
    c.add_argument("--by", required=True, type=nonblank)
    c.add_argument("--parent")
    for name in ("claim", "block", "close", "handoff", "check", "show", "page"):
        s = sub.add_parser(name)
        s.add_argument("id")
        if name not in ("show", "page"):
            s.add_argument("--by", required=True, type=nonblank)
    sub.choices["block"].add_argument("--on", required=True, type=nonblank)
    sub.choices["block"].add_argument("--text", required=True)
    sub.choices["close"].add_argument("--reason", required=True, choices=CLOSE_REASONS)
    sub.choices["close"].add_argument("--target", type=nonblank)
    sub.choices["handoff"].add_argument("--to", required=True, type=nonblank)
    sub.choices["handoff"].add_argument("--title", type=nonblank)
    sub.choices["check"].add_argument("--name", required=True)
    sub.choices["check"].add_argument("--status", required=True, choices=CHECK_STATUSES)
    sub.choices["check"].add_argument("--text")
    sub.choices["check"].add_argument("--evidence")
    sub.choices["check"].add_argument("--candidate", type=nonblank)
    sub.add_parser("pages")
    sub.add_parser("list").add_argument("--all", action="store_true")
    for s in sub.choices.values():
        s.add_argument("--repo", default=".")
    a = ap.parse_args(argv)
    repo = pathlib.Path(a.repo)
    writers = {"create": create, "claim": claim, "block": block, "close": close, "handoff": handoff, "check": check}
    if a.cmd in writers:
        why, new = transact(repo, lambda events, state: writers[a.cmd](events, state, a))
        if why:
            print(why)
            return 2
        created = [e["successor"] if e["op"] == "handoff" else e["ticket"]
                   for e in new if e["op"] in ("create", "handoff")]
        if created:
            print(created[-1])
        return 0
    state = load(repo)
    if a.cmd == "list":
        for tid, t in state.items():
            if a.all or t["state"] != "closed":
                print(f"{tid}  {t['state']}  {t['owner']}  {t['title']}")
        return 0
    if a.cmd == "pages":
        for tid, t in state.items():
            write_page(repo, tid, t)
        return 0
    if a.id not in state:
        print(f"no ticket {a.id}")
        return 2
    if a.cmd == "show":
        print(json.dumps(state[a.id], indent=2))
    else:
        write_page(repo, a.id, state[a.id])
        print(page_path(repo, a.id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
