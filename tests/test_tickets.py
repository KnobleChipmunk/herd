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

