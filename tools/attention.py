"""Tell the operator when a human is needed, and show every agent and ticket in one place (#33, #34).

usage: attention.py scan    [--repo PATH] [--tab TAB] [--json]
       attention.py watch   [--repo PATH] [--tab TAB] [--interval S] [--ntfy URL] [--once]
       attention.py monitor [--repo PATH] [--tab TAB] [--interval S] [--once]

One rule set, read by both the watcher and the monitor. It joins the run log
(what is owed) with `herdr agent list` (what each agent is doing), in the
spirit of OpenRig's state taxonomy: activity and obligations stay separate,
and a diagnosis is computed at read time, never stored.

- decision (operator): a `decision-needed` from any run with no later
  `decision-made` for the same issue.
- permission (operator): a pane Herdr reports `blocked` (an approval or
  question dialog), one alert per blocked episode.
- pr-ready (operator): each `pr-opened` of the latest run; the watcher batches them.
- run-end (info): the latest run ended.
- overdue (lead): a worker `blocked` event older than --overdue minutes. It is
  the lead's to rule on, so it is shown, never sent to the operator.
- parked (operator): the run is open, work is in flight, nobody in the run's
  tab is working, no agent there is of unknown or blocked state, and the log
  has been quiet for --stall minutes. An issue waiting on the operator is
  HELD: it keeps its decision alert and never raises a stall, and answering
  the decision makes it eligible again. An issue with an open `wait` (a
  deliberate wait with a reason: resource, peer, environment, auth,
  rate-limit, scheduled) is not a stall either. When `herdr agent list` fails
  or the run's tab is unknown, nothing is claimed about who is working.

The watcher sends each operator or info item once: its key is the log record's
byte offset plus a hash of the line, so a replaced log cannot suppress a new
alert at a reused offset. An item counts as sent only when the Herdr
notification succeeded; a failed one is retried on the next poll, and ntfy is
best effort. Sent keys live in <git common dir>/herd/attention-state.json,
written atomically. One watcher runs per repository: a second one exits at
once. The run's tab is the one its `run-start` recorded (`--tab`), re-read on
every poll, so one watcher follows successive runs.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

import runlog
from herdtool import git_common_dir

IN_FLIGHT = ("spec-approved", "plan-review", "worktree-created", "dispatched", "review-round")
DECISIONS = ("decision-needed", "decision-made")
STALL_MINUTES = 20
OVERDUE_MINUTES = 15


def read_events(path: pathlib.Path) -> list[dict]:
    """The log's events, each with `_id` = "<byte offset>:<12 hex of the line's sha1>"."""
    if not path.exists():
        return []
    events, at = [], 0
    for line in path.read_bytes().splitlines(keepends=True):
        if line.strip():
            events.append({"_id": f"{at}:{hashlib.sha1(line).hexdigest()[:12]}", **json.loads(line)})
        at += len(line)
    return events


def age_minutes(e: dict, now: datetime.datetime) -> float:
    return (now - datetime.datetime.fromisoformat(e["ts"])).total_seconds() / 60


def item(kind: str, audience: str, key: str, title: str, body: str, subject: str) -> dict:
    return {"kind": kind, "audience": audience, "key": key, "title": title, "body": body, "subject": subject}


def open_decisions(events: list[dict]) -> list[dict]:
    return [e for i, e in enumerate(events) if e["kind"] == "decision-needed"
            and not any(x["kind"] == "decision-made" and x.get("issue") == e.get("issue") for x in events[i + 1:])]


def latest_progress(run: list[dict], skip: tuple = ()) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for e in run:
        if e.get("issue") and e["kind"] in runlog.PROGRESS and e["kind"] not in skip:
            out[e["issue"]] = e
    return out


def diagnose(events: list[dict], agents: list[dict] | None, now: datetime.datetime, *, tab: str | None,
             stall_after: float = STALL_MINUTES, overdue_after: float = OVERDUE_MINUTES) -> list[dict]:
    """Every attention item, in a fixed order: decisions, permissions, PRs, run end, overdue blocks, stall.
    `agents` is None when `herdr agent list` failed: then no permission or stall is claimed."""
    run = runlog.latest(events)
    items = []
    decisions = open_decisions(events)
    for e in decisions:
        items.append(item("decision", "operator", e["_id"], f"Decision needed: #{e.get('issue', '?')}",
                          e.get("text", ""), f"#{e.get('issue', '?')}"))
    for a in agents or []:
        if a.get("agent_status") == "blocked":
            who = a.get("name") or a["pane_id"]
            items.append(item("permission", "operator", f"blocked:{a['pane_id']}:{a.get('state_change_seq')}",
                              f"Permission needed: {who}",
                              f"{a.get('agent', 'agent')} in {a['pane_id']} is waiting at an approval or question",
                              who))
    for e in run:
        if e["kind"] == "pr-opened":
            items.append(item("pr-ready", "operator", e["_id"], f"PR #{e['pr']} ready to merge",
                              f"#{e.get('issue', '?')} {e.get('branch', '')}".strip(), f"#{e.get('issue', '?')}"))
    ended = [e for e in run if e["kind"] == "run-end"]
    if ended:
        items.append(item("run-end", "info", ended[-1]["_id"], "Run ended", ended[-1].get("text", run[0]["run"]),
                          run[0]["run"]))
    for i, e in enumerate(run):
        if e["kind"] == "blocked" and age_minutes(e, now) >= overdue_after and not any(
                x["kind"] in ("done", "pr-opened") and x.get("issue") == e.get("issue") for x in run[i + 1:]):
            items.append(item("overdue", "lead", e["_id"], f"Lead intervention overdue: #{e.get('issue', '?')}",
                              e.get("text", ""), f"#{e.get('issue', '?')}"))
    if run and not ended and agents is not None and tab:
        held = {e.get("issue") for e in decisions}
        waiting = {i for i, e in latest_progress(run).items() if e["kind"] == "wait"}
        flying = [i for i, e in latest_progress(run, DECISIONS + ("wait",)).items()
                  if e["kind"] in IN_FLIGHT and i not in held and i not in waiting]
        mine = [a for a in agents if a.get("tab_id") == tab]
        quiet = age_minutes(run[-1], now)
        if flying and quiet >= stall_after and not any(a.get("agent_status") in ("working", "unknown", "blocked")
                                                       for a in mine):
            items.append(item("parked", "operator", f"parked:{run[-1]['_id']}", "Run may be stalled",
                              f"in flight: {' '.join('#' + i for i in flying)}; nobody working; "
                              f"last log event {int(quiet)}m ago", " ".join('#' + i for i in flying)))
    return items


def herdr_sink(title: str, body: str, sound: str) -> bool:
    """True only when Herdr reports the notification shown: it exits 0 even when it drops one as
    rate-limited (`"shown": false, "reason": "rate_limited"`), and a dropped one must be retried."""
    r = subprocess.run(["herdr", "notification", "show", title, "--body", body, "--sound", sound],
                       capture_output=True, text=True, check=False)
    try:
        return r.returncode == 0 and json.loads(r.stdout)["result"]["shown"] is True
    except (ValueError, KeyError, TypeError):
        return False


def ntfy_sink(url: str):
    def send(title: str, body: str, sound: str) -> bool:
        request = urllib.request.Request(url, data=body.encode(), method="POST",
                                         headers={"Title": title, "Priority": "high" if sound == "request" else "default"})
        with urllib.request.urlopen(request, timeout=10):
            pass
        return True
    return send


def run_tab(events: list[dict]) -> str | None:
    """The Herdr tab the current run recorded at run-start (`runlog.py add run-start --tab ...`)."""
    run = runlog.latest(events)
    return run[0].get("tab") if run else None


def state_path(repo: pathlib.Path) -> pathlib.Path:
    return git_common_dir(repo) / "herd" / "attention-state.json"


def load_state(repo: pathlib.Path) -> dict:
    p = state_path(repo)
    return json.loads(p.read_text()) if p.exists() else {"sent": []}


def save_state(repo: pathlib.Path, state: dict) -> None:
    p = state_path(repo)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state))
    os.replace(tmp, p)


@contextlib.contextmanager
def single_watcher(repo: pathlib.Path):
    """Hold the repository's watcher lock for the watcher's lifetime; yield False if another holds it."""
    lock = git_common_dir(repo) / "herd" / "attention-watch.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "a") as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        yield True


def watch_once(repo: pathlib.Path, agents: list[dict] | None, now: datetime.datetime, *, sink, tab: str | None,
               extra=(), stall_after: float = STALL_MINUTES, overdue_after: float = OVERDUE_MINUTES) -> list[dict]:
    """Send every operator/info item not sent before; return what was sent. `sink` is primary: an item
    counts as sent only when it returns True. `extra` sinks are best effort."""
    state = load_state(repo)
    events = read_events(runlog.log_path(repo))
    items = diagnose(events, agents, now, tab=tab or run_tab(events), stall_after=stall_after,
                     overdue_after=overdue_after)
    sent = set(state["sent"])
    new = [i for i in items if i["audience"] != "lead" and i["key"] not in sent]
    prs = [i for i in new if i["kind"] == "pr-ready"]
    batches = [([i for i in prs], f"{len(prs)} PRs ready to merge", " ".join(i["title"].split()[1] for i in prs),
                "request")] if len(prs) > 1 else []
    batches += [([i], i["title"], i["body"], "request" if i["audience"] == "operator" else "none")
                for i in new if i["kind"] != "pr-ready" or len(prs) == 1]
    delivered = []
    for group, title, body, sound in batches:
        if sink(title, body, sound):
            delivered += group
            for s in extra:
                try:
                    s(title, body, sound)
                except Exception as exc:  # optional push never stops the watcher
                    print(f"ntfy failed: {exc}", file=sys.stderr)
    if delivered:
        save_state(repo, {"sent": sorted(sent | {i["key"] for i in delivered})})
    return delivered


def monitor(events: list[dict], agents: list[dict] | None, now: datetime.datetime, *, tab: str | None,
            stall_after: float = STALL_MINUTES, overdue_after: float = OVERDUE_MINUTES) -> list[str]:
    """The text monitor: every agent, every issue of the latest run, what the lead owes, what needs the operator.
    Data no producer supplies yet (binding provenance until #38) is shown as unknown, never guessed."""
    run = runlog.latest(events)
    roles = {e["agent"]: e["role"] for e in run if e["kind"] == "session"}
    worktrees = {e.get("issue"): e["worktree"] for e in run if e["kind"] == "worktree-created"}
    lines = [f"observed {now.isoformat(timespec='seconds')} · run tab {tab or 'unknown'}", "AGENTS"]
    if agents is None:
        lines.append("  unavailable: herdr agent list failed")
    for a in agents or []:
        who = a.get("name") or a["pane_id"]
        where = "  (run tab unknown)" if not tab else "" if a.get("tab_id") == tab else "  (outside run)"
        role = roles.get(a.get("name"))
        lines.append(f"  {who:<22} {a['pane_id']:<8} {a.get('agent', '?'):<7} {a.get('agent_status', 'unknown'):<8} "
                     f"role: {role or 'unknown'}{'' if role else ' (unassociated)'} · binding: unknown{where}")
    lines.append("ISSUES")
    for issue, e in latest_progress(run).items():
        wait = f" [waiting: {e.get('reason')}]" if e["kind"] == "wait" else ""
        where = f" · {worktrees[issue]}" if issue in worktrees else ""
        lines.append(f"  #{issue} {runlog.describe(e)}{wait} ({int(age_minutes(e, now))}m ago){where}")
    items = diagnose(events, agents, now, tab=tab, stall_after=stall_after, overdue_after=overdue_after)
    lines.append("LEAD")
    lines += [f"  {i['title']}: {i['body']}" for i in items if i["audience"] == "lead"] or ["  nothing"]
    lines.append("NEEDS YOU")
    lines += [f"  {i['title']}: {i['body']}" for i in items if i["audience"] == "operator"] or ["  nothing"]
    return lines


def herdr_agents() -> list[dict] | None:
    """Every agent Herdr sees, or None when the observation failed."""
    r = subprocess.run(["herdr", "agent", "list"], capture_output=True, text=True, check=False)
    if r.returncode:
        print(f"herdr agent list failed: {r.stderr.strip()}", file=sys.stderr)
        return None
    try:
        return json.loads(r.stdout)["result"]["agents"]
    except (ValueError, KeyError):
        return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("scan", "watch", "monitor"))
    ap.add_argument("--repo", default=".")
    ap.add_argument("--tab", default=None, help="override the run's Herdr tab (default: the tab the current "
                                                  "run recorded at run-start, re-read on every poll)")
    ap.add_argument("--interval", type=float, default=30)
    ap.add_argument("--stall", type=float, default=STALL_MINUTES)
    ap.add_argument("--overdue", type=float, default=OVERDUE_MINUTES)
    ap.add_argument("--ntfy")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    repo = pathlib.Path(a.repo)
    if a.cmd == "watch":
        with single_watcher(repo) as mine:
            if not mine:
                print("a watcher is already running for this repository")
                return 0
            while True:
                now = datetime.datetime.now(datetime.timezone.utc)
                for i in watch_once(repo, herdr_agents(), now, sink=herdr_sink, tab=a.tab,
                                    extra=[ntfy_sink(a.ntfy)] if a.ntfy else [], stall_after=a.stall,
                                    overdue_after=a.overdue):
                    print(f"{now.isoformat(timespec='seconds')} sent {i['kind']}: {i['title']}", flush=True)
                if a.once:
                    return 0
                time.sleep(a.interval)
    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        events = read_events(runlog.log_path(repo))
        tab = a.tab or run_tab(events)
        if a.cmd == "scan":
            items = diagnose(events, herdr_agents(), now, tab=tab, stall_after=a.stall, overdue_after=a.overdue)
            print(json.dumps(items, indent=2) if a.json else
                  "\n".join(f"{i['audience']:<8} {i['kind']:<10} {i['title']}: {i['body']}" for i in items))
            return 0
        print("" if a.once else "\033[2J\033[H", end="")
        print("\n".join(monitor(events, herdr_agents(), now, tab=tab, stall_after=a.stall,
                                overdue_after=a.overdue)))
        if a.once:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
