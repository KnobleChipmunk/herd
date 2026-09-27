# Tasks — attention (#33, #34)

Tier: **full** (new module, new mechanism). DEPENDS ON #32: the branch is stacked on `feat/32-run-recovery`.
Fences are generated from the lead's pre-executed tree; `tools/fencecheck.py` must print `FENCES OK (5 steps)`.

## 1. Tests first — apply T1, T2, then observe RED

- [ ] **T1** `tests/test_attention.py` — acceptance tests for the attention rules, watcher and monitor

Create this file with exactly this body (byte-exact, ends with one newline):

```python
import datetime
import json

import attention
import runlog

NOW = datetime.datetime(2026, 9, 27, 12, 0, 0, tzinfo=datetime.timezone.utc)
TAB = "w1:tZ"


def ev(kind, minutes_ago=0, run="R1", **fields):
    ts = (NOW - datetime.timedelta(minutes=minutes_ago)).isoformat(timespec="seconds")
    return {"ts": ts, "run": run, "kind": kind, **fields}


def log(*events):
    """Events as read from a log: each gets a distinct record id `_id`."""
    return [{"_id": f"{n * 100}:fixture{n}", **e} for n, e in enumerate(events)]


def agent(name, status, tab=TAB, pane="w1:p1", seq=1, kind="pi"):
    return {"name": name, "agent": kind, "agent_status": status, "tab_id": tab, "pane_id": pane,
            "state_change_seq": seq}


def diagnose(events, agents, **kw):
    return attention.diagnose(events, agents, NOW, tab=TAB, **kw)


def kinds(items, audience=None):
    return [i["kind"] for i in items if audience is None or i["audience"] == audience]


# --- operator attention ------------------------------------------------------

def test_an_open_decision_from_any_run_needs_the_operator():
    events = log(ev("run-start", 90, run="A"), ev("decision-needed", 80, run="A", issue="426", text="source?"),
                 ev("run-end", 70, run="A"), ev("run-start", 10, run="B"))
    items = diagnose(events, [])
    decision = [i for i in items if i["kind"] == "decision"]
    assert len(decision) == 1 and decision[0]["audience"] == "operator"
    assert "#426" in decision[0]["title"] and "source?" in decision[0]["body"]


def test_a_decision_answered_later_is_not_attention_but_one_answered_earlier_is():
    events = log(ev("run-start", 90), ev("decision-made", 85, issue="426", text="old"),
                 ev("decision-needed", 80, issue="426", text="source?"),
                 ev("decision-needed", 70, issue="427", text="budget?"), ev("decision-made", 60, issue="427", text="ok"))
    assert [i["title"] for i in diagnose(events, []) if i["kind"] == "decision"] == ["Decision needed: #426"]


def test_a_blocked_pane_is_a_permission_request_keyed_by_its_episode():
    first = diagnose(log(ev("run-start", 5)), [agent("pi_build", "blocked", seq=4)])
    again = diagnose(log(ev("run-start", 5)), [agent("pi_build", "blocked", seq=4)])
    later = diagnose(log(ev("run-start", 5)), [agent("pi_build", "blocked", seq=9)])
    assert kinds(first, "operator") == ["permission"]
    assert first[0]["key"] == again[0]["key"] != later[0]["key"]


def test_a_blocked_pane_in_another_tab_is_still_the_operators():
    items = diagnose(log(ev("run-start", 5)), [agent("claude-fix", "blocked", tab="w1:tP", kind="claude")])
    assert kinds(items, "operator") == ["permission"]


def test_each_opened_pr_is_ready_for_merge():
    events = log(ev("run-start", 30), ev("pr-opened", 20, issue="32", pr="47", branch="feat/32"),
                 ev("pr-opened", 10, issue="31", pr="48", branch="feat/31"))
    ready = [i for i in diagnose(events, []) if i["kind"] == "pr-ready"]
    assert [i["subject"] for i in ready] == ["#32", "#31"] and {i["audience"] for i in ready} == {"operator"}


def test_run_end_is_informational():
    items = diagnose(log(ev("run-start", 30), ev("run-end", 1)), [])
    assert [(i["kind"], i["audience"]) for i in items] == [("run-end", "info")]


# --- the lead's attention ----------------------------------------------------

def test_a_worker_block_becomes_overdue_for_the_lead_not_the_operator():
    fresh = diagnose(log(ev("run-start", 30), ev("blocked", 5, issue="32", text="anchor twice")), [])
    aged = diagnose(log(ev("run-start", 30), ev("blocked", 20, issue="32", text="anchor twice")), [])
    assert kinds(fresh) == []
    assert [(i["kind"], i["audience"]) for i in aged] == [("overdue", "lead")]
    assert "anchor twice" in aged[0]["body"]


def test_a_resolved_block_is_not_overdue():
    events = log(ev("run-start", 30), ev("blocked", 20, issue="32", text="x"), ev("done", 19, issue="32"))
    assert kinds(diagnose(events, [])) == []


# --- stalls: PARKED vs HELD vs peer waits -------------------------------------

IN_FLIGHT = (ev("run-start", 60), ev("dispatched", 50, issue="32"))


def test_in_flight_work_with_nobody_working_and_a_quiet_log_is_a_stall():
    items = diagnose(log(*IN_FLIGHT), [agent("pi_build", "idle"), agent("lead", "idle", kind="claude", pane="w1:p0")])
    stall = [i for i in items if i["kind"] == "parked"]
    assert len(stall) == 1 and stall[0]["audience"] == "operator"
    assert "#32" in stall[0]["body"]


def test_a_working_peer_is_a_wait_not_a_stall():
    items = diagnose(log(*IN_FLIGHT), [agent("pi_build", "idle"), agent("codex_review", "working", pane="w1:p2")])
    assert "parked" not in kinds(items)


def test_a_recent_log_event_is_not_a_stall():
    items = diagnose(log(*IN_FLIGHT, ev("review-round", 3, issue="32", round="1", verdict="FINDINGS: 1")),
                     [agent("pi_build", "idle")])
    assert "parked" not in kinds(items)


def test_a_held_issue_suppresses_only_the_stall_alarm():
    """In flight AND waiting on the operator: the decision alert stays, the stall alarm does not fire."""
    events = log(ev("run-start", 60), ev("decision-needed", 55, issue="32", text="scope?"), ev("dispatched", 50, issue="32"))
    items = diagnose(events, [agent("pi_build", "idle")])
    assert "parked" not in kinds(items)
    assert "decision" in kinds(items, "operator")


def test_an_agent_of_unknown_state_prevents_a_stall_claim():
    items = diagnose(log(*IN_FLIGHT), [agent("pi_build", "unknown")])
    assert "parked" not in kinds(items)


def test_agents_outside_the_run_tab_do_not_count_as_working():
    items = diagnose(log(*IN_FLIGHT), [agent("pi_build", "idle"), agent("other", "working", tab="w1:tP")])
    assert "parked" in kinds(items)


def test_no_stall_once_the_run_has_ended():
    assert "parked" not in kinds(diagnose(log(*IN_FLIGHT, ev("run-end", 30)), [agent("pi_build", "idle")]))


def test_done_unseen_is_not_attention():
    assert kinds(diagnose(log(ev("run-start", 5)), [agent("pi_build", "done")])) == []


# --- the watcher: dedup, sinks, state ----------------------------------------

def write_log(repo, *events):
    path = runlog.log_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(e) + "\n" for e in events))
    return path


def test_read_events_ids_each_line_by_offset_and_content(repo_with_worktree):
    """Offset alone would collide when a replaced log reuses offsets (plan review #32 round 1)."""
    import hashlib

    main, _ = repo_with_worktree
    path = write_log(main, ev("run-start"), ev("note", text="x"))
    lines = path.read_bytes().splitlines(keepends=True)
    events = attention.read_events(path)
    assert [e["_id"] for e in events] == [f"0:{hashlib.sha1(lines[0]).hexdigest()[:12]}",
                                          f"{len(lines[0])}:{hashlib.sha1(lines[1]).hexdigest()[:12]}"]
    assert attention.read_events(path.with_name("missing.jsonl")) == []


def test_watch_notifies_each_item_once_across_restarts(repo_with_worktree):
    main, _ = repo_with_worktree
    write_log(main, ev("run-start", 30), ev("decision-needed", 20, issue="426", text="source?"))
    sent = []
    sink = lambda title, body, sound: sent.append((title, sound))  # noqa: E731
    attention.watch_once(main, [], NOW, sink=sink, tab=TAB)
    attention.watch_once(main, [], NOW, sink=sink, tab=TAB)
    assert sent == [("Decision needed: #426", "request")]
    with runlog.log_path(main).open("a") as f:
        f.write(json.dumps(ev("decision-needed", 1, issue="427", text="budget?")) + "\n")
    attention.watch_once(main, [], NOW, sink=sink, tab=TAB)
    assert sent[-1] == ("Decision needed: #427", "request") and len(sent) == 2


def test_a_replaced_log_does_not_suppress_new_alerts_at_reused_offsets(repo_with_worktree):
    main, _ = repo_with_worktree
    path = write_log(main, ev("run-start", 30), ev("decision-needed", 20, issue="426", text="a?"))
    sent = []
    sink = lambda title, body, sound: sent.append(title)  # noqa: E731
    attention.watch_once(main, [], NOW, sink=sink, tab=TAB)
    path.unlink()
    write_log(main, ev("run-start", 30), ev("decision-needed", 20, issue="999", text="b?"))
    attention.watch_once(main, [], NOW, sink=sink, tab=TAB)
    assert sent == ["Decision needed: #426", "Decision needed: #999"]


def test_new_ready_prs_are_batched_into_one_notification(repo_with_worktree):
    main, _ = repo_with_worktree
    write_log(main, ev("run-start", 30), ev("pr-opened", 20, issue="32", pr="47", branch="a"),
              ev("pr-opened", 10, issue="31", pr="48", branch="b"))
    sent = []
    attention.watch_once(main, [], NOW, sink=lambda t, b, s: sent.append((t, b)), tab=TAB)
    assert len(sent) == 1 and sent[0][0] == "2 PRs ready to merge" and "#47" in sent[0][1] and "#48" in sent[0][1]


def test_lead_items_are_never_sent_to_the_operator(repo_with_worktree):
    main, _ = repo_with_worktree
    write_log(main, ev("run-start", 30), ev("blocked", 20, issue="32", text="x"))
    sent = []
    attention.watch_once(main, [], NOW, sink=lambda t, b, s: sent.append(t), tab=TAB)
    assert sent == []


def test_informational_items_are_sent_without_a_sound(repo_with_worktree):
    main, _ = repo_with_worktree
    write_log(main, ev("run-start", 30), ev("run-end", 1))
    sent = []
    attention.watch_once(main, [], NOW, sink=lambda t, b, s: sent.append((t, s)), tab=TAB)
    assert sent == [("Run ended", "none")]


def test_the_herdr_sink_calls_herdr_notification_show(monkeypatch):
    calls = []
    monkeypatch.setattr(attention.subprocess, "run", lambda argv, **kw: calls.append(argv))
    attention.herdr_sink("Decision needed: #426", "source?", "request")
    assert calls == [["herdr", "notification", "show", "Decision needed: #426", "--body", "source?",
                      "--sound", "request"]]


def test_the_ntfy_sink_posts_the_title_and_body(monkeypatch):
    posted = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def urlopen(request, timeout):
        posted.append((request.full_url, request.data, request.get_header("Title")))
        return Response()

    monkeypatch.setattr(attention.urllib.request, "urlopen", urlopen)
    attention.ntfy_sink("https://ntfy.sh/herd-test")("2 PRs ready to merge", "#47 #48", "request")
    assert posted == [("https://ntfy.sh/herd-test", b"#47 #48", "2 PRs ready to merge")]


# --- the monitor --------------------------------------------------------------

def test_the_monitor_lists_every_agent_and_marks_the_ones_outside_the_run():
    events = log(ev("run-start", 60), ev("dispatched", 50, issue="32"),
                 ev("session", 50, agent="pi_build", role="builder", outcome="fresh"))
    agents = [agent("pi_build", "working"), agent("claude-fix", "idle", tab="w1:tP", kind="claude"),
              agent(None, "working", kind="claude", pane="w1:p0")]
    out = "\n".join(attention.monitor(events, agents, NOW, tab=TAB))
    assert "pi_build" in out and "builder" in out and "working" in out
    assert "claude-fix" in out and "(outside run)" in out
    assert "w1:p0" in out


def test_the_monitor_shows_issue_progress_and_a_needs_you_section():
    events = log(ev("run-start", 60), ev("dispatched", 50, issue="32"),
                 ev("decision-needed", 40, issue="31", text="scope?"))
    lines = attention.monitor(events, [], NOW, tab=TAB)
    out = "\n".join(lines)
    assert "NEEDS YOU" in out and "Decision needed: #31" in out
    assert "#32 dispatched" in out and "50m ago" in out


def test_the_monitor_says_unknown_rather_than_guessing_a_role():
    out = "\n".join(attention.monitor(log(ev("run-start", 5)), [agent("pi_build", "idle")], NOW, tab=TAB))
    assert "unknown" in out
```

- [ ] **T2** `tests/test_skill_text.py` — the skill names the watcher and the monitor

Append exactly this text at the END of the file. The fence below BEGINS with the blank lines that separate it from the existing last line — keep them. The file must end with one newline:

```python


def test_the_lead_starts_the_attention_watcher_and_names_the_monitor():
    text = " ".join(SKILL.read_text().split())
    monitoring = text[text.index("## Monitoring"): text.index("## Rulings")]
    assert "attention.py watch --repo <repo>" in monitoring
    assert "attention.py monitor --repo <repo>" in monitoring
    assert "run-start" in monitoring

```

RED after T1–T2 (measured by the lead): `python3 -m pytest -q tests/test_attention.py tests/test_skill_text.py` fails collecting `tests/test_attention.py` (no module `attention`) and the new skill-text test fails.

## 2. Implementation — apply I1–I3

- [ ] **I1** `pyproject.toml` — register the new module for isort

Find this exact text (it occurs exactly once):

```python
known-first-party = ["fencecheck",
```

Replace it with exactly:

```python
known-first-party = ["attention", "fencecheck",
```

- [ ] **I2** `tools/attention.py` — the attention rules, watcher and monitor

Create this file with exactly this body (byte-exact, ends with one newline):

```python
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
  tab is working, no agent there is of unknown state, and the log has been
  quiet for --stall minutes. An issue waiting on the operator is HELD, not
  parked: it keeps its decision alert and never raises a stall.

The watcher sends each operator or info item once: its key is the log record's
byte offset plus a hash of the line, so a replaced log cannot suppress a new
alert at a reused offset. Sent keys live in <git common dir>/herd/attention-state.json.
"""
from __future__ import annotations

import argparse
import datetime
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


def latest_progress(run: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for e in run:
        if e.get("issue") and e["kind"] in runlog.PROGRESS:
            out[e["issue"]] = e
    return out


def diagnose(events: list[dict], agents: list[dict], now: datetime.datetime, *, tab: str | None,
             stall_after: float = STALL_MINUTES, overdue_after: float = OVERDUE_MINUTES) -> list[dict]:
    """Every attention item, in a fixed order: decisions, permissions, PRs, run end, overdue blocks, stall."""
    run = runlog.latest(events)
    items = []
    decisions = open_decisions(events)
    for e in decisions:
        items.append(item("decision", "operator", e["_id"], f"Decision needed: #{e.get('issue', '?')}",
                          e.get("text", ""), f"#{e.get('issue', '?')}"))
    for a in agents:
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
    if run and not ended:
        held = {e.get("issue") for e in decisions}
        flying = [i for i, e in latest_progress(run).items() if e["kind"] in IN_FLIGHT and i not in held]
        mine = [a for a in agents if a.get("tab_id") == tab]
        quiet = age_minutes(run[-1], now)
        if flying and quiet >= stall_after and not any(a.get("agent_status") in ("working", "unknown", "blocked")
                                                       for a in mine):
            items.append(item("parked", "operator", f"parked:{run[-1]['_id']}", "Run may be stalled",
                              f"in flight: {' '.join('#' + i for i in flying)}; nobody working; "
                              f"last log event {int(quiet)}m ago", " ".join('#' + i for i in flying)))
    return items


def herdr_sink(title: str, body: str, sound: str) -> None:
    subprocess.run(["herdr", "notification", "show", title, "--body", body, "--sound", sound],
                   capture_output=True, text=True, check=False)


def ntfy_sink(url: str):
    def send(title: str, body: str, sound: str) -> None:
        request = urllib.request.Request(url, data=body.encode(), method="POST",
                                         headers={"Title": title, "Priority": "high" if sound == "request" else "default"})
        with urllib.request.urlopen(request, timeout=10):
            pass
    return send


def state_path(repo: pathlib.Path) -> pathlib.Path:
    return git_common_dir(repo) / "herd" / "attention-state.json"


def watch_once(repo: pathlib.Path, agents: list[dict], now: datetime.datetime, *, sink, tab: str | None,
               stall_after: float = STALL_MINUTES, overdue_after: float = OVERDUE_MINUTES) -> list[dict]:
    """Send every operator/info item not sent before; return what was sent."""
    items = diagnose(read_events(runlog.log_path(repo)), agents, now, tab=tab, stall_after=stall_after,
                     overdue_after=overdue_after)
    path = state_path(repo)
    sent = set(json.loads(path.read_text())["sent"]) if path.exists() else set()
    new = [i for i in items if i["audience"] != "lead" and i["key"] not in sent]
    prs = [i for i in new if i["kind"] == "pr-ready"]
    if len(prs) > 1:
        sink(f"{len(prs)} PRs ready to merge", " ".join(i["title"].split()[1] for i in prs), "request")
    for i in new:
        if i["kind"] != "pr-ready" or len(prs) == 1:
            sink(i["title"], i["body"], "request" if i["audience"] == "operator" else "none")
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"sent": sorted(sent | {i["key"] for i in new})}))
    return new


def monitor(events: list[dict], agents: list[dict], now: datetime.datetime, *, tab: str | None) -> list[str]:
    """The text monitor: every agent, every issue of the latest run, and what needs the operator."""
    run = runlog.latest(events)
    roles = {e["agent"]: e["role"] for e in run if e["kind"] == "session"}
    lines = ["AGENTS"]
    for a in agents:
        who = a.get("name") or a["pane_id"]
        where = "" if a.get("tab_id") == tab else "  (outside run)"
        lines.append(f"  {who:<22} {a.get('agent', '?'):<7} {a.get('agent_status', 'unknown'):<8} "
                     f"role: {roles.get(a.get('name'), 'unknown')}{where}")
    lines.append("ISSUES")
    for issue, e in latest_progress(run).items():
        lines.append(f"  #{issue} {runlog.describe(e)} ({int(age_minutes(e, now))}m ago)")
    lines.append("NEEDS YOU")
    needs = [i for i in diagnose(events, agents, now, tab=tab) if i["audience"] == "operator"]
    lines += [f"  {i['title']}: {i['body']}" for i in needs] or ["  nothing"]
    return lines


def herdr_agents() -> list[dict]:
    r = subprocess.run(["herdr", "agent", "list"], capture_output=True, text=True, check=False)
    if r.returncode:
        print(f"herdr agent list failed: {r.stderr.strip()}", file=sys.stderr)
        return []
    return json.loads(r.stdout)["result"]["agents"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("scan", "watch", "monitor"))
    ap.add_argument("--repo", default=".")
    ap.add_argument("--tab", default=None, help="the run's Herdr tab (default: $HERDR_TAB_ID)")
    ap.add_argument("--interval", type=float, default=30)
    ap.add_argument("--stall", type=float, default=STALL_MINUTES)
    ap.add_argument("--overdue", type=float, default=OVERDUE_MINUTES)
    ap.add_argument("--ntfy")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    repo = pathlib.Path(a.repo)
    tab = a.tab or os.environ.get("HERDR_TAB_ID")
    sinks = [herdr_sink] + ([ntfy_sink(a.ntfy)] if a.ntfy else [])

    def fan_out(title: str, body: str, sound: str) -> None:
        for s in sinks:
            s(title, body, sound)

    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        agents = herdr_agents()
        if a.cmd == "scan":
            items = diagnose(read_events(runlog.log_path(repo)), agents, now, tab=tab, stall_after=a.stall,
                             overdue_after=a.overdue)
            print(json.dumps(items, indent=2) if a.json else
                  "\n".join(f"{i['audience']:<8} {i['kind']:<10} {i['title']}: {i['body']}" for i in items))
            return 0
        if a.cmd == "watch":
            watch_once(repo, agents, now, sink=fan_out, tab=tab, stall_after=a.stall, overdue_after=a.overdue)
        else:
            print("\033[2J\033[H" if not a.once else "", end="")
            print("\n".join(monitor(read_events(runlog.log_path(repo)), agents, now, tab=tab)))
        if a.once:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **I3** `skill/SKILL.md` — the lead starts the watcher; the operator's monitor

Find this exact text (it occurs exactly once):

```python
## Monitoring

The backgrounded prompt/wait notifications are the primary wake signal.
```

Replace it with exactly:

```python
## Monitoring

At `run-start`, the lead starts the attention watcher as a background task:
`python3 <herd>/tools/attention.py watch --repo <repo>` (add `--ntfy <url>` to
also push to a phone). It raises a Herdr notification once per open
decision, permission dialog, batch of ready PRs, and stalled run, and never
for a worker block the lead has not yet ruled on. The operator's view of
every agent and issue is `python3 <herd>/tools/attention.py monitor --repo
<repo>`, run in any pane (#33, #34).

The backgrounded prompt/wait notifications are the primary wake signal.
```

## 3. Gates

- Full suite at the base (`feat/32-run-recovery`): `248 passed`. After: `248 + 28 = 276 passed` (27 in `tests/test_attention.py`, 1 new skill-text test). Wall time about 8 s.
- `ruff check tools tests` → `All checks passed!`
- `openspec validate attention` valid.
- Live smoke (lead, read-only): `python3 tools/attention.py monitor --repo <herd main checkout> --once` prints AGENTS / ISSUES / NEEDS YOU from the real run.

## 4. Mutations

Drive with `python3 tools/mutate.py openspec/changes/attention/tasks.md <tree>`; every one KILLED.

- [ ] **M1** in `tools/attention.py`: replace

```python
and not any(x["kind"] == "decision-made" and x.get("issue") == e.get("issue") for x in events[i + 1:])]
```

with

```python
and not any(x["kind"] == "decision-made" and x.get("issue") == e.get("issue") for x in events)]
```

Killer: `tests/test_attention.py::test_a_decision_answered_later_is_not_attention_but_one_answered_earlier_is`

- [ ] **M2** in `tools/attention.py`: replace

```python
f"blocked:{a['pane_id']}:{a.get('state_change_seq')}"
```

with

```python
f"blocked:{a['pane_id']}"
```

Killer: `tests/test_attention.py::test_a_blocked_pane_is_a_permission_request_keyed_by_its_episode`

- [ ] **M3** in `tools/attention.py`: replace

```python
new = [i for i in items if i["audience"] != "lead" and i["key"] not in sent]
```

with

```python
new = [i for i in items if i["key"] not in sent]
```

Killer: `tests/test_attention.py::test_lead_items_are_never_sent_to_the_operator`

- [ ] **M4** in `tools/attention.py`: replace

```python
    if len(prs) > 1:
```

with

```python
    if False:
```

Killer: `tests/test_attention.py::test_new_ready_prs_are_batched_into_one_notification`

- [ ] **M5** in `tools/attention.py`: replace

```python
e["kind"] in IN_FLIGHT and i not in held]
```

with

```python
e["kind"] in IN_FLIGHT]
```

Killer: `tests/test_attention.py::test_a_held_issue_suppresses_only_the_stall_alarm`

- [ ] **M6** in `tools/attention.py`: replace

```python
a.get("agent_status") in ("working", "unknown", "blocked")
```

with

```python
a.get("agent_status") in ("working", "blocked")
```

Killer: `tests/test_attention.py::test_an_agent_of_unknown_state_prevents_a_stall_claim`

- [ ] **M7** in `tools/attention.py`: replace

```python
mine = [a for a in agents if a.get("tab_id") == tab]
```

with

```python
mine = agents
```

Killer: `tests/test_attention.py::test_agents_outside_the_run_tab_do_not_count_as_working`

- [ ] **M8** in `tools/attention.py`: replace

```python
{"_id": f"{at}:{hashlib.sha1(line).hexdigest()[:12]}", **json.loads(line)}
```

with

```python
{"_id": f"{at}", **json.loads(line)}
```

Killer: `tests/test_attention.py::test_a_replaced_log_does_not_suppress_new_alerts_at_reused_offsets`

- [ ] **M9** in `tools/attention.py`: replace

```python
if flying and quiet >= stall_after and not any(
```

with

```python
if flying and not any(
```

Killer: `tests/test_attention.py::test_a_recent_log_event_is_not_a_stall`

- [ ] **M10** in `tools/attention.py`: replace

```python
if e["kind"] == "blocked" and age_minutes(e, now) >= overdue_after and not any(
```

with

```python
if e["kind"] == "blocked" and not any(
```

Killer: `tests/test_attention.py::test_a_worker_block_becomes_overdue_for_the_lead_not_the_operator`
