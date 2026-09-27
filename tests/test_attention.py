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


def test_each_run_brings_its_own_tab_and_the_monitor_follows_it(repo_with_worktree, monkeypatch, capsys):
    """A long-lived watcher or monitor must not keep an earlier run's tab (plan review #33 round 2)."""
    main, _ = repo_with_worktree
    write_log(main, ev("run-start", 90, run="A", tab="w1:tA"), ev("run-end", 80, run="A"),
              ev("run-start", 30, run="B", tab="w1:tB"), ev("dispatched", 25, run="B", issue="40"))
    monkeypatch.setattr(attention, "herdr_agents", lambda: [agent("pi_build", "working", tab="w1:tB"),
                                                            agent("old", "idle", tab="w1:tA")])
    assert attention.main(["monitor", "--repo", str(main), "--once"]) == 0
    out = capsys.readouterr().out
    assert "run tab w1:tB" in out
    assert "pi_build" in out.split("\n")[2] and "(outside run)" not in out.split("\n")[2]
    sent = attention.watch_once(main, [agent("pi_build", "idle", tab="w1:tB"), agent("old", "working", tab="w1:tA")],
                                NOW, sink=lambda t, b, s: True, tab=None)
    assert [i["kind"] for i in sent] == ["parked"]


def test_a_run_without_a_recorded_tab_claims_no_stall(repo_with_worktree):
    main, _ = repo_with_worktree
    write_log(main, ev("run-start", 60), ev("dispatched", 50, issue="32"))
    assert attention.watch_once(main, [agent("pi_build", "idle")], NOW, sink=lambda t, b, s: True, tab=None) == []


def test_a_decision_after_a_wait_ends_the_wait():
    events = log(ev("run-start", 90), ev("dispatched", 80, issue="32"), ev("wait", 75, issue="32", reason="peer"),
                 ev("decision-needed", 70, issue="32", text="scope?"), ev("decision-made", 60, issue="32", text="x"))
    assert "parked" in kinds(diagnose(events, [agent("pi_build", "idle")]))
    still = log(ev("run-start", 90), ev("dispatched", 80, issue="32"), ev("wait", 75, issue="32", reason="peer"))
    assert "parked" not in kinds(diagnose(still, [agent("pi_build", "idle")]))


def test_the_monitor_uses_the_same_thresholds_as_scan(repo_with_worktree, monkeypatch, capsys):
    main, _ = repo_with_worktree
    now = datetime.datetime.now(datetime.timezone.utc)
    stamp = lambda m: (now - datetime.timedelta(minutes=m)).isoformat(timespec="seconds")  # noqa: E731
    write_log(main, {"ts": stamp(40), "run": "R", "kind": "run-start", "tab": TAB},
              {"ts": stamp(30), "run": "R", "kind": "dispatched", "issue": "32"},
              {"ts": stamp(20), "run": "R", "kind": "blocked", "issue": "31", "text": "x"})
    monkeypatch.setattr(attention, "herdr_agents", lambda: [agent("pi_build", "idle")])
    attention.main(["monitor", "--repo", str(main), "--once", "--stall", "60", "--overdue", "60"])
    lenient = capsys.readouterr().out
    attention.main(["monitor", "--repo", str(main), "--once"])
    strict = capsys.readouterr().out
    assert "Run may be stalled" not in lenient and "overdue" not in lenient
    assert "Run may be stalled" in strict and "Lead intervention overdue: #31" in strict


def test_the_monitor_shows_lead_attention_evidence_and_unknown_provenance():
    events = log(ev("run-start", 60), ev("worktree-created", 55, issue="32", worktree="/w/32", branch="feat/32"),
                 ev("dispatched", 50, issue="32"), ev("blocked", 30, issue="32", text="anchor twice"))
    out = "\n".join(attention.monitor(events, [agent("pi_build", "idle")], NOW, tab=TAB))
    lead = out[out.index("LEAD"): out.index("NEEDS YOU")]
    assert "Lead intervention overdue: #32" in lead
    assert "/w/32" in out and "binding: unknown" in out and "(unassociated)" in out
