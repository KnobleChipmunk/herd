# Tasks — tickets (#36, #37)

Tier: **full**. DEPENDS ON #33: the branch is stacked on `feat/33-attention` (which is stacked on #32).
Fences are generated from the lead's pre-executed tree; `tools/fencecheck.py` must print `FENCES OK (5 steps)`.

## 1. Tests first — apply T1, T2, then observe RED

- [ ] **T1** `tests/test_tickets.py` — acceptance tests for tickets and pages

Create this file with exactly this body (byte-exact, ends with one newline):

```python
import json

import pytest

import runlog
import tickets


def t(repo, *args: str) -> int:
    return tickets.main([*args, "--repo", str(repo)])


def created_id(capsys) -> str:
    return capsys.readouterr().out.strip().splitlines()[-1]


def state(repo) -> dict:
    return {k: v for k, v in tickets.load(repo).items()}


def new(repo, capsys, title="Build the watcher", to="builder", **kw) -> str:
    args = ["create", "--title", title, "--to", to, "--by", kw.get("by", "lead")]
    if "parent" in kw:
        args += ["--parent", kw["parent"]]
    assert t(repo, *args) == 0
    return created_id(capsys)


# --- create, claim, ownership ------------------------------------------------

def test_create_opens_a_pending_ticket_with_an_owner_and_prints_its_id(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    tid = new(main, capsys, parent="33")
    ticket = state(main)[tid]
    assert tid == "T1"
    assert (ticket["state"], ticket["owner"], ticket["parent"], ticket["title"]) == ("pending", "builder", "33",
                                                                                     "Build the watcher")


def test_ids_count_up_and_survive_across_runs(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    assert [new(main, capsys), new(main, capsys)] == ["T1", "T2"]
    assert tickets.path(main).parent == runlog.log_path(main).parent


def test_only_the_owner_can_claim(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    tid = new(main, capsys)
    assert t(main, "claim", tid, "--by", "reviewer") == 2
    assert "T1 is owned by builder" in capsys.readouterr().out
    assert t(main, "claim", tid, "--by", "builder") == 0
    assert state(main)[tid]["state"] == "in-progress"


def test_a_claimed_ticket_cannot_be_claimed_again(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    tid = new(main, capsys)
    t(main, "claim", tid, "--by", "builder")
    assert t(main, "claim", tid, "--by", "builder") == 2
    assert "T1 is in-progress, not pending or blocked" in capsys.readouterr().out


def test_an_unknown_ticket_is_refused(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    assert t(main, "claim", "T9", "--by", "builder") == 2
    assert "no ticket T9" in capsys.readouterr().out


# --- closing with a reason from a closed set ---------------------------------

@pytest.mark.parametrize("reason", ["no-follow-on", "denied", "canceled", "superseded"])
def test_close_needs_a_reason_from_the_closed_set(repo_with_worktree, capsys, reason):
    main, _ = repo_with_worktree
    tid = new(main, capsys)
    t(main, "claim", tid, "--by", "builder")
    assert t(main, "close", tid, "--by", "builder", "--reason", reason) == 0
    assert (state(main)[tid]["state"], state(main)[tid]["reason"]) == ("closed", reason)


def test_a_reason_outside_the_set_is_refused(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    tid = new(main, capsys)
    with pytest.raises(SystemExit):
        t(main, "close", tid, "--by", "builder", "--reason", "finished")
    assert "invalid choice: 'finished'" in capsys.readouterr().err
    assert state(main)[tid]["state"] == "pending"


def test_escalation_needs_a_target(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    tid = new(main, capsys)
    assert t(main, "close", tid, "--by", "builder", "--reason", "escalation") == 2
    assert "escalation needs --target" in capsys.readouterr().out
    assert t(main, "close", tid, "--by", "builder", "--reason", "escalation", "--target", "lead") == 0
    assert state(main)[tid]["target"] == "lead"


def test_a_closed_ticket_stays_closed(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    tid = new(main, capsys)
    t(main, "close", tid, "--by", "builder", "--reason", "canceled")
    capsys.readouterr()
    assert t(main, "claim", tid, "--by", "builder") == 2
    assert t(main, "close", tid, "--by", "builder", "--reason", "denied") == 2
    assert "T1 is closed" in capsys.readouterr().out


def test_only_the_owner_can_close(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    tid = new(main, capsys)
    assert t(main, "close", tid, "--by", "reviewer", "--reason", "denied") == 2
    assert state(main)[tid]["state"] == "pending"


# --- block and handoff ---------------------------------------------------------

def test_block_keeps_the_owner_names_what_it_waits_on_and_claim_resumes_it(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    tid = new(main, capsys)
    t(main, "claim", tid, "--by", "builder")
    assert t(main, "block", tid, "--by", "builder", "--on", "lead", "--text", "anchor matches twice") == 0
    ticket = state(main)[tid]
    assert (ticket["state"], ticket["owner"], ticket["reason"], ticket["target"]) == ("blocked", "builder",
                                                                                      "blocked_on", "lead")
    assert t(main, "claim", tid, "--by", "builder") == 0
    assert state(main)[tid]["state"] == "in-progress"


def test_handoff_closes_one_ticket_and_opens_its_successor_in_one_write(repo_with_worktree, capsys, monkeypatch):
    main, _ = repo_with_worktree
    tid = new(main, capsys, parent="33")
    t(main, "claim", tid, "--by", "builder")
    capsys.readouterr()
    writes = []
    real = tickets._write_all
    monkeypatch.setattr(tickets, "_write_all", lambda p, events: (writes.append(len(events)), real(p, events)))
    assert t(main, "handoff", tid, "--by", "builder", "--to", "reviewer", "--title", "Review the watcher") == 0
    successor = created_id(capsys)
    tickets_now = state(main)
    assert writes == [1]  # one record closes T1 and opens its successor
    assert (tickets_now[tid]["state"], tickets_now[tid]["reason"], tickets_now[tid]["target"]) == (
        "closed", "handed_off_to", "reviewer")
    assert (tickets_now[successor]["state"], tickets_now[successor]["owner"], tickets_now[successor]["parent"],
            tickets_now[successor]["after"]) == ("pending", "reviewer", "33", tid)


def test_every_ticket_write_holds_the_run_log_lock(repo_with_worktree, capsys, monkeypatch):
    """Reuses #32's lock: a create and a handoff each read and write inside one acquisition."""
    import contextlib

    main, _ = repo_with_worktree
    seen = []
    real = runlog.locked

    @contextlib.contextmanager
    def traced(p):
        with real(p):
            seen.append("enter")
            yield
            seen.append("exit")

    monkeypatch.setattr(runlog, "locked", traced)
    tid = new(main, capsys)
    t(main, "claim", tid, "--by", "builder")
    t(main, "handoff", tid, "--by", "builder", "--to", "reviewer")
    assert seen == ["enter", "exit"] * 3


# --- checks and the ticket page (#37) --------------------------------------------

def test_a_check_records_status_reason_and_evidence(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    tid = new(main, capsys)
    assert t(main, "check", tid, "--by", "lead", "--name", "qa", "--status", "omitted", "--text", "small tier") == 0
    assert t(main, "check", tid, "--by", "qa", "--name", "suite", "--status", "pass",
             "--evidence", "HANDOFF-33.md", "--candidate", "abc123") == 0
    checks = state(main)[tid]["checks"]
    assert checks == {"qa": {"status": "omitted", "text": "small tier", "evidence": None, "candidate": None},
                      "suite": {"status": "pass", "text": None, "evidence": "HANDOFF-33.md", "candidate": "abc123"}}


def test_a_check_status_outside_the_set_is_refused(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    tid = new(main, capsys)
    with pytest.raises(SystemExit):
        t(main, "check", tid, "--by", "qa", "--name", "qa", "--status", "ok")
    assert "invalid choice: 'ok'" in capsys.readouterr().err


def test_the_page_is_generated_at_a_stable_address_from_records(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    tid = new(main, capsys, parent="33")
    t(main, "claim", tid, "--by", "builder")
    t(main, "check", tid, "--by", "builder", "--name", "suite", "--status", "pass", "--evidence", "HANDOFF-33.md",
      "--candidate", "abc123")
    assert t(main, "page", tid) == 0
    page = tickets.page_path(main, tid)
    assert page == runlog.log_path(main).parent / "tickets" / "T1.md"
    text = page.read_text()
    assert text.startswith("# T1 — Build the watcher\n")
    assert "Owner: builder · State: in-progress · Parent: #33" in text
    assert "| suite | pass | abc123 | HANDOFF-33.md |" in text
    assert "created by lead" in text and "claimed by builder" in text


@pytest.mark.parametrize("status", ["omitted", "not-checked", "blocked", "fail"])
def test_the_verdict_is_never_pass_while_any_check_is_not_a_pass(repo_with_worktree, capsys, status):
    main, _ = repo_with_worktree
    tid = new(main, capsys)
    t(main, "check", tid, "--by", "qa", "--name", "suite", "--status", "pass", "--candidate", "c1")
    t(main, "check", tid, "--by", "qa", "--name", "qa", "--status", status, "--text", "why")
    t(main, "page", tid)
    text = tickets.page_path(main, tid).read_text()
    assert "Verdict: NOT PASS" in text and "Verdict: PASS" not in text


def test_the_verdict_is_pass_only_when_every_recorded_check_passed(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    tid = new(main, capsys)
    t(main, "page", tid)
    assert "Verdict: NO CHECKS" in tickets.page_path(main, tid).read_text()
    t(main, "check", tid, "--by", "qa", "--name", "suite", "--status", "pass", "--candidate", "c1")
    t(main, "page", tid)
    assert "Verdict: PASS on c1" in tickets.page_path(main, tid).read_text()


def test_the_page_links_the_parent_issues_run_log_events(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    runlog.main(["add", "run-start", "--repo", str(main)])
    runlog.main(["add", "pr-opened", "--repo", str(main), "--issue", "33", "--pr", "49", "--branch", "feat/33-attention"])
    tid = new(main, capsys, parent="33")
    t(main, "page", tid)
    assert "pr-opened PR #49 feat/33-attention" in tickets.page_path(main, tid).read_text()


def test_pages_regenerates_every_ticket(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    new(main, capsys)
    new(main, capsys)
    assert t(main, "pages") == 0
    assert sorted(p.name for p in tickets.page_path(main, "T1").parent.iterdir()) == ["T1.md", "T2.md"]


def test_list_shows_open_tickets_with_owner_and_state(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    a = new(main, capsys)
    b = new(main, capsys, title="Review it", to="reviewer")
    t(main, "close", a, "--by", "builder", "--reason", "canceled")
    capsys.readouterr()
    assert t(main, "list") == 0
    out = capsys.readouterr().out
    assert f"{b}  pending  reviewer  Review it" in out and f"{a} " not in out
    assert t(main, "list", "--all") == 0
    assert f"{a}  closed" in capsys.readouterr().out


def test_the_store_is_append_only_json_lines(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    tid = new(main, capsys)
    t(main, "claim", tid, "--by", "builder")
    ops = [json.loads(ln)["op"] for ln in tickets.path(main).read_text().splitlines()]
    assert ops == ["create", "claim"]


# --- plan review #36 round 1 -------------------------------------------------

def test_a_pass_needs_the_candidate_it_was_measured_on(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    tid = new(main, capsys)
    assert t(main, "check", tid, "--by", "qa", "--name", "suite", "--status", "pass") == 2
    assert "a pass needs --candidate" in capsys.readouterr().out
    assert state(main)[tid]["checks"] == {}


def test_passes_on_different_candidates_are_not_a_pass(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    tid = new(main, capsys)
    t(main, "check", tid, "--by", "qa", "--name", "suite", "--status", "pass", "--candidate", "c1")
    t(main, "check", tid, "--by", "qa", "--name", "qa", "--status", "pass", "--candidate", "c2")
    t(main, "page", tid)
    text = tickets.page_path(main, tid).read_text()
    assert "Verdict: NOT PASS (checks on different candidates: c1, c2)" in text


@pytest.mark.parametrize("args", [
    ["create", "--title", "x", "--to", "", "--by", "lead"],
    ["create", "--title", "x", "--to", "builder", "--by", "  "],
    ["block", "T1", "--by", "builder", "--on", " ", "--text", "waiting"],
    ["handoff", "T1", "--by", "builder", "--to", ""],
    ["close", "T1", "--by", "builder", "--reason", "escalation", "--target", "   "],
])
def test_blank_owners_actors_and_targets_are_refused(repo_with_worktree, capsys, args):
    main, _ = repo_with_worktree
    new(main, capsys)
    before = tickets.path(main).read_bytes()
    with pytest.raises(SystemExit):
        t(main, *args)
    assert "must not be blank" in capsys.readouterr().err
    assert tickets.path(main).read_bytes() == before


def test_an_interrupted_last_line_is_ignored_and_dropped_before_the_next_write(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    new(main, capsys)
    with tickets.path(main).open("a") as f:
        f.write('{"ticket": "T2", "op": "cre')  # a crash mid-write: no newline
    assert list(state(main)) == ["T1"]
    assert new(main, capsys, title="after the crash") == "T2"
    lines = tickets.path(main).read_text().splitlines()
    assert [json.loads(ln)["ticket"] for ln in lines] == ["T1", "T2"]
    assert state(main)["T2"]["title"] == "after the crash"


def test_a_handoff_successor_counts_toward_the_next_id(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    tid = new(main, capsys)
    t(main, "handoff", tid, "--by", "builder", "--to", "reviewer")
    capsys.readouterr()
    assert new(main, capsys) == "T3"

```

- [ ] **T2** `tests/test_skill_text.py` — the skill separates messages from owned work

Append exactly this text at the END of the file. The fence below BEGINS with the blank lines that separate it from the existing last line — keep them. The file must end with one newline:

```python


def test_the_skill_separates_messages_from_owned_work():
    text = " ".join(SKILL.read_text().split())
    tickets = text[text.index("## Tickets"): text.index("## Run log")]
    assert "A question goes as a message" in tickets and "goes as a ticket" in tickets
    assert "tickets.py create" in tickets and "handoff" in tickets and "never a PASS" in tickets

```

RED after T1–T2: `tests/test_tickets.py` fails to collect (no module `tickets`) and the new skill-text test fails.

## 2. Implementation — apply I1–I3

- [ ] **I1** `pyproject.toml` — register the new module for isort

Find this exact text (it occurs exactly once):

```python
"probe", "runlog"]
```

Replace it with exactly:

```python
"probe", "runlog", "tickets"]
```

- [ ] **I2** `tools/tickets.py` — the ticket store, contracts and pages

Create this file with exactly this body (byte-exact, ends with one newline):

```python
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
```

- [ ] **I3** `skill/SKILL.md` — the Tickets section

Find this exact text (it occurs exactly once):

```python
## Run log (`tools/runlog.py`)
```

Insert exactly this text IMMEDIATELY BEFORE it (the fence carries its own trailing blank lines):

```python
## Tickets (`tools/tickets.py`)

A question goes as a message (`herdr agent prompt`); work someone must own
goes as a ticket. `tickets.py create --title <t> --to <owner> --by <you>
[--parent <issue>]` opens one; its owner `claim`s it, then `close`s it with
a reason (`no-follow-on`, `denied`, `canceled`, `superseded`, or
`escalation --target <who>`), `block`s it `--on <who>`, or `handoff`s it `--to <next owner>`,
which closes it and opens the successor in one write. Record each gate
with `check <id> --name <n> --status pass|fail|not-checked|blocked|omitted
[--candidate <commit>]` (a pass names the candidate it was measured on);
`page <id>` writes the ticket's page to `<git common dir>/herd/tickets/`.
An omitted, blocked or unchecked gate is never a PASS (#36, #37).

```

## 3. Gates

- Full suite at the base (`feat/33-attention` after its build): `297 passed`. After: `297 + 38 = 335 passed` (37 in `tests/test_tickets.py` with parametrized cases, 1 new skill-text test). ~8 s.
- `ruff check tools tests` → `All checks passed!`; `openspec validate tickets` valid.

## 4. Mutations

Drive with `python3 tools/mutate.py openspec/changes/tickets/tasks.md <tree>`; every one KILLED.

- [ ] **M1** in `tools/tickets.py`: replace

```python
    if state[tid]["owner"] != by:
```

with

```python
    if False:
```

Killer: `tests/test_tickets.py::test_only_the_owner_can_claim`

- [ ] **M2** in `tools/tickets.py`: replace

```python
state[a.id]["state"] not in ("pending", "blocked"):
```

with

```python
state[a.id]["state"] not in ("pending", "blocked", "in-progress"):
```

Killer: `tests/test_tickets.py::test_a_claimed_ticket_cannot_be_claimed_again`

- [ ] **M3** in `tools/tickets.py`: replace

```python
if a.reason == "escalation" and not a.target
```

with

```python
if False and not a.target
```

Killer: `tests/test_tickets.py::test_escalation_needs_a_target`

- [ ] **M4** in `tools/tickets.py`: replace

```python
        if data and not data.endswith(b"\n"):
```

with

```python
        if False:
```

Killer: `tests/test_tickets.py::test_an_interrupted_last_line_is_ignored_and_dropped_before_the_next_write`

- [ ] **M5** in `tools/tickets.py`: replace

```python
all(c["status"] == "pass" for c in checks.values())
```

with

```python
any(c["status"] == "pass" for c in checks.values())
```

Killer: `tests/test_tickets.py::test_the_verdict_is_never_pass_while_any_check_is_not_a_pass`

- [ ] **M6** in `tools/tickets.py`: replace

```python
    if state[tid]["state"] == "closed":
```

with

```python
    if False:
```

Killer: `tests/test_tickets.py::test_a_closed_ticket_stays_closed`

- [ ] **M7** in `tools/tickets.py`: replace

```python
        with runlog.locked(p):
```

with

```python
        with open(os.devnull):
```

Killer: `tests/test_tickets.py::test_every_ticket_write_holds_the_run_log_lock`

- [ ] **M8** in `tools/tickets.py`: replace

```python
t.update(state="blocked", reason="blocked_on", target=e["on"])
```

with

```python
t.update(state="closed", reason="blocked_on", target=e["on"])
```

Killer: `tests/test_tickets.py::test_block_keeps_the_owner_names_what_it_waits_on_and_claim_resumes_it`

- [ ] **M9** in `tools/tickets.py`: replace

```python
if a.all or t["state"] != "closed":
```

with

```python
if True:
```

Killer: `tests/test_tickets.py::test_list_shows_open_tickets_with_owner_and_state`

- [ ] **M10** in `tools/tickets.py`: replace

```python
            out[tid].update(state="closed", reason="handed_off_to", target=e["to"])
```

with

```python

```

Killer: `tests/test_tickets.py::test_handoff_closes_one_ticket_and_opens_its_successor_in_one_write`

- [ ] **M11** in `tools/tickets.py`: replace

```python
    if not why and a.status == "pass" and not a.candidate:
```

with

```python
    if False:
```

Killer: `tests/test_tickets.py::test_a_pass_needs_the_candidate_it_was_measured_on`

- [ ] **M12** in `tools/tickets.py`: replace

```python
    if not value.strip():
```

with

```python
    if False:
```

Killer: `tests/test_tickets.py::test_blank_owners_actors_and_targets_are_refused`

- [ ] **M13** in `tools/tickets.py`: replace

```python
    if len(candidates) > 1:
```

with

```python
    if False:
```

Killer: `tests/test_tickets.py::test_passes_on_different_candidates_are_not_a_pass`
