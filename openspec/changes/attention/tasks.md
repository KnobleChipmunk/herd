# Tasks — attention (#33, #34)

Tier: **full**. DEPENDS ON #32: the branch is stacked on `feat/32-run-recovery`.
Fences are generated from the lead's pre-executed tree; `tools/fencecheck.py` must print `FENCES OK (7 steps)`.

## 1. Tests first — apply T1–T3, then observe RED

- [ ] **T1** `tests/test_attention.py` — acceptance tests for the attention rules, watcher and monitor

Create this file with exactly this body (byte-exact, ends with one newline):

```python
import datetime
import json

import pytest

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
    sink = lambda title, body, sound: sent.append((title, sound)) or True  # noqa: E731
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
    sink = lambda title, body, sound: sent.append(title) or True  # noqa: E731
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
    attention.watch_once(main, [], NOW, sink=lambda t, b, s: sent.append((t, b)) or True, tab=TAB)
    assert len(sent) == 1 and sent[0][0] == "2 PRs ready to merge" and "#47" in sent[0][1] and "#48" in sent[0][1]


def test_lead_items_are_never_sent_to_the_operator(repo_with_worktree):
    main, _ = repo_with_worktree
    write_log(main, ev("run-start", 30), ev("blocked", 20, issue="32", text="x"))
    sent = []
    attention.watch_once(main, [], NOW, sink=lambda t, b, s: sent.append(t) or True, tab=TAB)
    assert sent == []


def test_informational_items_are_sent_without_a_sound(repo_with_worktree):
    main, _ = repo_with_worktree
    write_log(main, ev("run-start", 30), ev("run-end", 1))
    sent = []
    attention.watch_once(main, [], NOW, sink=lambda t, b, s: sent.append((t, s)) or True, tab=TAB)
    assert sent == [("Run ended", "none")]


def test_the_herdr_sink_calls_herdr_notification_show(monkeypatch):
    calls = []
    replies = iter([
        '{"result":{"shown":true,"type":"notification_show"}}',
        '{"result":{"reason":"rate_limited","shown":false,"type":"notification_show"}}',  # real Herdr, exit 0
        "not json",
    ])

    def run(argv, **kw):
        calls.append(argv)
        return attention.subprocess.CompletedProcess(argv, 0, stdout=next(replies))

    monkeypatch.setattr(attention.subprocess, "run", run)
    assert attention.herdr_sink("Decision needed: #426", "source?", "request") is True
    assert calls == [["herdr", "notification", "show", "Decision needed: #426", "--body", "source?",
                      "--sound", "request"]]
    assert attention.herdr_sink("Decision needed: #426", "source?", "request") is False
    assert attention.herdr_sink("Decision needed: #426", "source?", "request") is False


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


# --- plan review #33 round 1 -------------------------------------------------

def test_answering_a_hold_makes_unfinished_work_eligible_for_a_stall_again():
    events = log(ev("run-start", 90), ev("dispatched", 80, issue="32"),
                 ev("decision-needed", 70, issue="32", text="scope?"), ev("decision-made", 60, issue="32", text="narrow"))
    items = diagnose(events, [agent("pi_build", "idle")])
    assert "decision" not in kinds(items) and "parked" in kinds(items)
    recent = log(*events[:-1], ev("decision-made", 5, issue="32", text="narrow"))
    assert "parked" not in kinds(diagnose(recent, [agent("pi_build", "idle")]))


@pytest.mark.parametrize("reason", ["resource", "peer", "environment", "auth", "rate-limit", "scheduled"])
def test_a_deliberate_wait_is_not_a_stall(reason):
    events = log(*IN_FLIGHT, ev("wait", 40, issue="32", reason=reason, text="why"))
    assert "parked" not in kinds(diagnose(events, [agent("pi_build", "idle")]))


def test_a_failed_agent_observation_claims_nothing_about_who_is_working():
    items = diagnose(log(*IN_FLIGHT), None)
    assert "parked" not in kinds(items) and "permission" not in kinds(items)
    assert "unavailable" in "\n".join(attention.monitor(log(*IN_FLIGHT), None, NOW, tab=TAB))


def test_an_unknown_run_tab_claims_no_stall():
    assert "parked" not in kinds(attention.diagnose(log(*IN_FLIGHT), [agent("pi_build", "idle")], NOW, tab=None))


def test_a_failed_notification_is_retried_on_the_next_poll(repo_with_worktree):
    main, _ = repo_with_worktree
    write_log(main, ev("run-start", 30), ev("decision-needed", 20, issue="426", text="source?"))
    tries = []
    attention.watch_once(main, [], NOW, sink=lambda t, b, s: tries.append(t) and False, tab=TAB)
    attention.watch_once(main, [], NOW, sink=lambda t, b, s: tries.append(t) or True, tab=TAB)
    attention.watch_once(main, [], NOW, sink=lambda t, b, s: tries.append(t) or True, tab=TAB)
    assert tries == ["Decision needed: #426", "Decision needed: #426"]


def test_a_failing_optional_push_neither_stops_the_watcher_nor_undoes_the_primary(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    write_log(main, ev("run-start", 30), ev("decision-needed", 20, issue="426", text="source?"))

    def broken(title, body, sound):
        raise OSError("ntfy down")

    sent = attention.watch_once(main, [], NOW, sink=lambda t, b, s: True, tab=TAB, extra=[broken])
    assert [i["kind"] for i in sent] == ["decision"]
    assert "ntfy failed: ntfy down" in capsys.readouterr().err
    assert attention.watch_once(main, [], NOW, sink=lambda t, b, s: True, tab=TAB, extra=[broken]) == []


def test_only_one_watcher_runs_per_repository(repo_with_worktree):
    main, _ = repo_with_worktree
    with attention.single_watcher(main) as first:
        with attention.single_watcher(main) as second:
            assert first is True and second is False
    with attention.single_watcher(main) as again:
        assert again is True


def test_the_watcher_records_the_run_tab_and_the_monitor_uses_it(repo_with_worktree, monkeypatch, capsys):
    main, _ = repo_with_worktree
    write_log(main, ev("run-start", 30))
    attention.watch_once(main, [], NOW, sink=lambda t, b, s: True, tab="w1:tA")
    monkeypatch.setattr(attention, "herdr_agents", lambda: [agent("pi_build", "working", tab="w1:tA")])
    monkeypatch.delenv("HERDR_TAB_ID", raising=False)
    assert attention.main(["monitor", "--repo", str(main), "--once"]) == 0
    out = capsys.readouterr().out
    assert "run tab w1:tA" in out and "(outside run)" not in out


def test_the_monitor_shows_lead_attention_evidence_and_unknown_provenance():
    events = log(ev("run-start", 60), ev("worktree-created", 55, issue="32", worktree="/w/32", branch="feat/32"),
                 ev("dispatched", 50, issue="32"), ev("blocked", 30, issue="32", text="anchor twice"))
    out = "\n".join(attention.monitor(events, [agent("pi_build", "idle")], NOW, tab=TAB))
    lead = out[out.index("LEAD"): out.index("NEEDS YOU")]
    assert "Lead intervention overdue: #32" in lead
    assert "/w/32" in out and "binding: unknown" in out and "(unassociated)" in out

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

- [ ] **T3** `tests/test_runlog.py` — one open decision per issue; the wait kind

Append exactly this text at the END of the file. The fence below BEGINS with the blank lines that separate it from the existing last line — keep them. The file must end with one newline:

```python


# --- #33: one open decision per issue, and deliberate waits -----------------

def test_a_decision_needs_an_issue(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    assert add(main, "decision-needed", "--text", "which source?") == 2
    assert "decision-needed needs --issue" in capsys.readouterr().out


def test_a_second_open_decision_for_one_issue_is_refused_even_across_runs(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    add(main, "decision-needed", "--issue", "426", "--text", "which source?")
    assert add(main, "decision-needed", "--issue", "426", "--text", "which budget?") == 2
    assert "#426 already has an open decision: which source?" in capsys.readouterr().out
    add(main, "run-end")
    add(main, "run-start")
    assert add(main, "decision-needed", "--issue", "426", "--text", "which budget?") == 2
    assert add(main, "decision-needed", "--issue", "427", "--text", "other issue") == 0


def test_an_answered_decision_can_be_followed_by_a_new_one(repo_with_worktree):
    main, _ = repo_with_worktree
    add(main, "run-start")
    add(main, "decision-needed", "--issue", "426", "--text", "which source?")
    add(main, "decision-made", "--issue", "426", "--text", "Raidbots")
    assert add(main, "decision-needed", "--issue", "426", "--text", "which budget?") == 0


def test_a_wait_records_its_reason_from_a_closed_set(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    assert add(main, "wait", "--issue", "35", "--reason", "rate-limit", "--text", "codex usage limit") == 0
    assert events(main)[-1]["reason"] == "rate-limit"
    with pytest.raises(SystemExit):
        add(main, "wait", "--issue", "35", "--reason", "lunch")
    assert "invalid choice: 'lunch'" in capsys.readouterr().err
    assert add(main, "wait", "--issue", "35") == 2
```

RED after T1–T3: `tests/test_attention.py` fails to collect (no module `attention`); the new skill-text test and the new run-log tests for decisions and waits fail.

## 2. Implementation — apply I1–I4

- [ ] **I1** `pyproject.toml` — register the new module for isort

Find this exact text (it occurs exactly once):

```python
known-first-party = ["fencecheck",
```

Replace it with exactly:

```python
known-first-party = ["attention", "fencecheck",
```

- [ ] **I2** `tools/runlog.py` — wait kind; one open decision per issue

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
          "outcome", "reason")
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
```

- [ ] **I3** `tools/attention.py` — the attention rules, watcher and monitor

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
best effort. Sent keys and the run's tab live in
<git common dir>/herd/attention-state.json, written atomically. One watcher
runs per repository: a second one exits at once.
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
        flying = [i for i, e in latest_progress(run, DECISIONS).items() if e["kind"] in IN_FLIGHT and i not in held]
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


def state_path(repo: pathlib.Path) -> pathlib.Path:
    return git_common_dir(repo) / "herd" / "attention-state.json"


def load_state(repo: pathlib.Path) -> dict:
    p = state_path(repo)
    return json.loads(p.read_text()) if p.exists() else {"sent": [], "tab": None}


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
    tab = tab or state.get("tab")
    items = diagnose(read_events(runlog.log_path(repo)), agents, now, tab=tab, stall_after=stall_after,
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
    if delivered or tab != state.get("tab"):
        save_state(repo, {"sent": sorted(sent | {i["key"] for i in delivered}), "tab": tab})
    return delivered


def monitor(events: list[dict], agents: list[dict] | None, now: datetime.datetime, *, tab: str | None) -> list[str]:
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
        where = "" if tab and a.get("tab_id") == tab else "  (outside run)"
        role = roles.get(a.get("name"))
        lines.append(f"  {who:<22} {a['pane_id']:<8} {a.get('agent', '?'):<7} {a.get('agent_status', 'unknown'):<8} "
                     f"role: {role or 'unknown'}{'' if role else ' (unassociated)'} · binding: unknown{where}")
    lines.append("ISSUES")
    for issue, e in latest_progress(run).items():
        wait = f" [waiting: {e.get('reason')}]" if e["kind"] == "wait" else ""
        where = f" · {worktrees[issue]}" if issue in worktrees else ""
        lines.append(f"  #{issue} {runlog.describe(e)}{wait} ({int(age_minutes(e, now))}m ago){where}")
    items = diagnose(events, agents, now, tab=tab)
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
    ap.add_argument("--tab", default=None,
                    help="the run's Herdr tab (watch: default $HERDR_TAB_ID, recorded for the others; "
                         "scan/monitor: default the watcher's recorded tab)")
    ap.add_argument("--interval", type=float, default=30)
    ap.add_argument("--stall", type=float, default=STALL_MINUTES)
    ap.add_argument("--overdue", type=float, default=OVERDUE_MINUTES)
    ap.add_argument("--ntfy")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    repo = pathlib.Path(a.repo)
    if a.cmd == "watch":
        tab = a.tab or os.environ.get("HERDR_TAB_ID")
        with single_watcher(repo) as mine:
            if not mine:
                print("a watcher is already running for this repository")
                return 0
            while True:
                now = datetime.datetime.now(datetime.timezone.utc)
                for i in watch_once(repo, herdr_agents(), now, sink=herdr_sink, tab=tab,
                                    extra=[ntfy_sink(a.ntfy)] if a.ntfy else [], stall_after=a.stall,
                                    overdue_after=a.overdue):
                    print(f"{now.isoformat(timespec='seconds')} sent {i['kind']}: {i['title']}", flush=True)
                if a.once:
                    return 0
                time.sleep(a.interval)
    tab = a.tab or load_state(repo).get("tab")
    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        events = read_events(runlog.log_path(repo))
        if a.cmd == "scan":
            items = diagnose(events, herdr_agents(), now, tab=tab, stall_after=a.stall, overdue_after=a.overdue)
            print(json.dumps(items, indent=2) if a.json else
                  "\n".join(f"{i['audience']:<8} {i['kind']:<10} {i['title']}: {i['body']}" for i in items))
            return 0
        print("" if a.once else "\033[2J\033[H", end="")
        print("\n".join(monitor(events, herdr_agents(), now, tab=tab)))
        if a.once:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **I4** `skill/SKILL.md` — the lead starts the watcher; waits; the operator's monitor

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
also push to a phone; a second watcher for the same repo exits at once). It
raises a Herdr notification once per open decision, permission dialog,
batch of ready PRs, and stalled run, retries one Herdr drops, and never
pages the operator for a worker block the lead has not yet ruled on. When
an issue is deliberately waiting, say so with `runlog.py add wait --issue
<id> --reason resource|peer|environment|auth|rate-limit|scheduled|other`, so
it is not read as a stall. The operator's view of every agent and issue is
`python3 <herd>/tools/attention.py monitor --repo <repo>`, run in any pane;
it uses the run tab the watcher recorded (#33, #34).

The backgrounded prompt/wait notifications are the primary wake signal.
```

## 3. Gates

- Full suite at the base (`feat/32-run-recovery`): `248 passed`. After: `294 passed` (41 in `tests/test_attention.py` with parametrized cases, 4 new in `tests/test_runlog.py`, 1 new skill-text test). ~8 s.
- `ruff check tools tests` → `All checks passed!`; `openspec validate attention` valid.
- Live checks (lead-owned, at final review; the lead ran them in pre-execution on 2026-09-27): `attention.py watch --repo <scratch repo with one decision> --tab <tab> --once` shows one Herdr notification (`shown: true`) and records it; a second run sends nothing. `attention.py monitor --repo <herd> --once` prints AGENTS / ISSUES / LEAD / NEEDS YOU from the real run. ntfy delivery is unverified.

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
    batches = [([i for i in prs], f"{len(prs)} PRs ready to merge", " ".join(i["title"].split()[1] for i in prs),
                "request")] if len(prs) > 1 else []
    batches += [([i], i["title"], i["body"], "request" if i["audience"] == "operator" else "none")
                for i in new if i["kind"] != "pr-ready" or len(prs) == 1]
```

with

```python
    batches = [([i], i["title"], i["body"], "request" if i["audience"] == "operator" else "none")
               for i in new]
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

- [ ] **M11** in `tools/attention.py`: replace

```python
latest_progress(run, DECISIONS).items()
```

with

```python
latest_progress(run).items()
```

Killer: `tests/test_attention.py::test_answering_a_hold_makes_unfinished_work_eligible_for_a_stall_again`

- [ ] **M12** in `tools/attention.py`: replace

```python
    if run and not ended and agents is not None and tab:
```

with

```python
    if run and not ended:
```

Killer: `tests/test_attention.py::test_a_failed_agent_observation_claims_nothing_about_who_is_working`

- [ ] **M13** in `tools/attention.py`: replace

```python
        return r.returncode == 0 and json.loads(r.stdout)["result"]["shown"] is True
```

with

```python
        return r.returncode == 0
```

Killer: `tests/test_attention.py::test_the_herdr_sink_calls_herdr_notification_show`

- [ ] **M14** in `tools/attention.py`: replace

```python
        if sink(title, body, sound):
```

with

```python
        if sink(title, body, sound) or True:
```

Killer: `tests/test_attention.py::test_a_failed_notification_is_retried_on_the_next_poll`

- [ ] **M15** in `tools/attention.py`: replace

```python
            yield False
            return
```

with

```python
            yield True
            return
```

Killer: `tests/test_attention.py::test_only_one_watcher_runs_per_repository`

- [ ] **M16** in `tools/runlog.py`: replace

```python
                if kind == "decision-needed" and open_decision(events, fields["issue"]):
```

with

```python
                if False:
```

Killer: `tests/test_runlog.py::test_a_second_open_decision_for_one_issue_is_refused_even_across_runs`
