import json

import pytest

import runlog


def add(repo, *args: str) -> int:
    return runlog.main(["add", *args, "--repo", str(repo)])


def events(repo) -> list[dict]:
    return [json.loads(ln) for ln in runlog.log_path(repo).read_text().splitlines()]


def test_the_log_lives_in_the_git_common_dir_so_every_worktree_shares_it(repo_with_worktree):
    main, wt = repo_with_worktree
    assert runlog.log_path(wt) == runlog.log_path(main) == main.resolve() / ".git" / "herd" / "run-log.jsonl"


def test_add_appends_one_json_line_with_time_kind_and_run(repo_with_worktree):
    main, wt = repo_with_worktree
    assert add(main, "run-start", "--text", "420-427 overnight") == 0
    assert add(wt, "worktree-created", "--issue", "421", "--worktree", str(wt), "--branch", "fix/421-x") == 0
    first, second = events(main)
    assert first["kind"] == "run-start" and first["text"] == "420-427 overnight"
    assert second["run"] == first["run"] == first["ts"]
    assert second["issue"] == "421" and second["worktree"] == str(wt) and second["branch"] == "fix/421-x"
    assert "pr" not in second


def test_an_unknown_kind_is_refused(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    with pytest.raises(SystemExit):
        add(main, "made-up-kind")
    assert "invalid choice: 'made-up-kind'" in capsys.readouterr().err


@pytest.mark.parametrize("kind, missing", [
    ("worktree-created", "--worktree"), ("branch-created", "--branch"), ("pr-opened", "--pr"),
    ("friction", "--agent"), ("decision-needed", "--text"),
])
def test_a_kind_without_its_required_field_is_refused(repo_with_worktree, capsys, kind, missing):
    main, _ = repo_with_worktree
    add(main, "run-start")
    assert add(main, kind, "--issue", "421") == 2
    assert f"{kind} needs {missing}" in capsys.readouterr().out
    assert [e["kind"] for e in events(main)] == ["run-start"]


def test_an_event_before_any_run_start_is_refused(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    assert add(main, "note", "--text", "x") == 2
    assert "no run-start in the log" in capsys.readouterr().out


def test_status_shows_each_issue_latest_event_for_the_latest_run_only(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start", "--text", "old run")
    add(main, "dispatched", "--issue", "300")
    add(main, "run-end")
    add(main, "run-start", "--text", "new run")
    add(main, "dispatched", "--issue", "421")
    add(main, "pr-opened", "--issue", "421", "--pr", "429", "--branch", "fix/421-x")
    add(main, "dispatched", "--issue", "422")
    assert runlog.main(["status", "--repo", str(main)]) == 0
    out = capsys.readouterr().out
    assert "#300" not in out
    assert "#421 pr-opened PR #429 fix/421-x" in out
    assert "#422 dispatched" in out


def test_status_lists_open_blocks_and_decisions_until_they_are_resolved(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    add(main, "blocked", "--issue", "421", "--text", "anchor I3 matches twice")
    add(main, "decision-needed", "--issue", "427", "--text", "input budget per check?")
    add(main, "decision-needed", "--issue", "426", "--text", "Raidbots as the source?")
    add(main, "decision-made", "--issue", "426", "--text", "yes, Raidbots")
    runlog.main(["status", "--repo", str(main)])
    out = capsys.readouterr().out
    assert "OPEN blocked #421: anchor I3 matches twice" in out
    assert "OPEN decision #427: input budget per check?" in out
    assert "#426: Raidbots as the source?" not in out


def test_a_later_done_resolves_a_block(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    add(main, "blocked", "--issue", "421", "--text", "reviewer down")
    add(main, "done", "--issue", "421")
    runlog.main(["status", "--repo", str(main)])
    assert "OPEN blocked" not in capsys.readouterr().out


def test_created_lists_worktrees_branches_and_scratch_of_the_latest_run(repo_with_worktree, capsys):
    main, wt = repo_with_worktree
    add(main, "run-start")
    add(main, "worktree-created", "--issue", "421", "--worktree", str(wt), "--branch", "fix/421-x")
    add(main, "scratch-created", "--issue", "422", "--worktree", "/tmp/pre-422", "--branch", "scratch/pre-422")
    add(main, "pr-opened", "--issue", "421", "--pr", "429", "--branch", "fix/421-x")
    assert runlog.main(["created", "--repo", str(main)]) == 0
    assert capsys.readouterr().out.splitlines() == [
        f"worktree-created #421 {wt} fix/421-x", "scratch-created #422 /tmp/pre-422 scratch/pre-422"]


def test_friction_lists_every_friction_line_with_agent_and_text(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    add(main, "friction", "--issue", "423", "--agent", "codex_review", "--text", "cd needed on every command")
    runlog.main(["friction", "--repo", str(main)])
    assert capsys.readouterr().out.strip() == "#423 codex_review: cd needed on every command"


def test_latest_run_events_are_parsed_by_other_tools(repo_with_worktree):
    main, _ = repo_with_worktree
    add(main, "run-start")
    add(main, "pr-opened", "--issue", "421", "--pr", "429", "--branch", "fix/421-x")
    assert [e["pr"] for e in runlog.latest_run(main) if e["kind"] == "pr-opened"] == ["429"]


def test_every_event_carries_the_id_of_the_run_it_belongs_to(repo_with_worktree):
    main, _ = repo_with_worktree
    path = runlog.log_path(main)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"ts": "2000-01-01T00:00:00+00:00", "run": "2000-01-01T00:00:00+00:00",
                                "kind": "run-start"}) + "\n")
    add(main, "dispatched", "--issue", "421")
    assert events(main)[-1]["run"] == "2000-01-01T00:00:00+00:00"


def test_status_shows_progress_not_friction_fallbacks_or_notes_and_keeps_the_pr(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    add(main, "pr-opened", "--issue", "421", "--pr", "429", "--branch", "fix/421-x")
    add(main, "fallback", "--issue", "421", "--agent", "opus_review", "--model", "opus")
    add(main, "friction", "--issue", "421", "--agent", "opus_review", "--text", "cd on every command")
    add(main, "note", "--issue", "421", "--text", "fyi")
    runlog.main(["status", "--repo", str(main)])
    first = capsys.readouterr().out.splitlines()[0]
    assert first.startswith("#421 pr-opened PR #429 fix/421-x")


def test_status_names_the_pr_on_a_later_progress_event(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    add(main, "pr-opened", "--issue", "421", "--pr", "429", "--branch", "fix/421-x")
    add(main, "review-round", "--issue", "421", "--round", "2", "--verdict", "FINDINGS: 1")
    runlog.main(["status", "--repo", str(main)])
    assert capsys.readouterr().out.startswith("#421 review-round FINDINGS: 1 [PR #429]")


@pytest.mark.parametrize("kind, args, missing", [
    ("spec-approved", [], "--tier"),
    ("plan-review", ["--round", "1"], "--verdict"),
    ("review-round", ["--round", "1"], "--verdict"),
    ("ruling", [], "--text"),
    ("gate-miss", [], "--text"),
    ("lead-finding", [], "--text"),
])
def test_ledger_kinds_require_the_field_their_column_counts(repo_with_worktree, capsys, kind, args, missing):
    main, _ = repo_with_worktree
    add(main, "run-start")
    assert add(main, kind, "--issue", "421", *args) == 2
    assert f"{kind} needs {missing}" in capsys.readouterr().out


def test_spec_approved_records_the_tier(repo_with_worktree):
    main, _ = repo_with_worktree
    add(main, "run-start")
    assert add(main, "spec-approved", "--issue", "421", "--tier", "small") == 0
    assert events(main)[-1]["tier"] == "small"


# --- #32: run recovery -----------------------------------------------------

@pytest.fixture(autouse=True)
def bounded():
    """Fail, rather than hang, any test in this file that runs over 60 s (plan review #32 round 3)."""
    import signal

    def expire(signum, frame):
        raise TimeoutError("test ran over 60 s: a run-log lock is probably stuck")

    previous = signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, 60)
    yield
    signal.setitimer(signal.ITIMER_REAL, 0)
    signal.signal(signal.SIGALRM, previous)


def close(repo, *args: str) -> int:
    return runlog.main(["close", *args, "--repo", str(repo)])


def test_a_second_run_start_is_refused_while_a_run_is_open(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start", "--text", "first")
    first = events(main)[0]["run"]
    assert add(main, "run-start", "--text", "second") == 2
    out = capsys.readouterr().out
    assert f"run {first} is still open" in out
    assert "runlog.py close --reason" in out
    assert [e["kind"] for e in events(main)] == ["run-start"]


def test_a_run_start_after_run_end_opens_a_new_run(repo_with_worktree):
    main, _ = repo_with_worktree
    add(main, "run-start")
    add(main, "run-end")
    assert add(main, "run-start") == 0
    starts = [e for e in events(main) if e["kind"] == "run-start"]
    assert len(starts) == 2 and starts[0]["run"] != starts[1]["run"]


def test_close_ends_the_open_run_with_its_reason(repo_with_worktree):
    main, _ = repo_with_worktree
    add(main, "run-start")
    run = events(main)[0]["run"]
    assert close(main, "--reason", "crashed at 3am") == 0
    last = events(main)[-1]
    assert last["kind"] == "run-end" and last["text"] == "closed: crashed at 3am" and last["run"] == run
    assert add(main, "run-start") == 0


@pytest.mark.parametrize("setup", [[], ["run-start", "run-end"]])
def test_close_with_no_open_run_is_refused(repo_with_worktree, capsys, setup):
    main, _ = repo_with_worktree
    for kind in setup:
        add(main, kind)
    before = runlog.read(main)
    assert close(main, "--reason", "x") == 2
    assert "no open run" in capsys.readouterr().out
    assert runlog.read(main) == before


def test_close_requires_a_reason(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    with pytest.raises(SystemExit):
        close(main)
    assert "the following arguments are required: --reason" in capsys.readouterr().err


def test_an_event_after_run_end_still_belongs_to_the_ended_run(repo_with_worktree):
    """merge_stack appends its librarian note after the lead's run-end (tools/merge_stack.py:189)."""
    main, _ = repo_with_worktree
    add(main, "run-start")
    add(main, "run-end")
    assert add(main, "note", "--text", "librarian started") == 0
    assert events(main)[-1]["run"] == events(main)[0]["run"]


def test_run_ids_are_unique_even_when_the_clock_repeats(repo_with_worktree, monkeypatch):
    main, _ = repo_with_worktree
    fixed = runlog.datetime.datetime(2026, 9, 27, 12, 0, 0, 123456, tzinfo=runlog.datetime.timezone.utc)
    monkeypatch.setattr(runlog, "now", lambda: fixed)
    for _ in range(3):
        add(main, "run-start")
        add(main, "run-end")
    base = fixed.isoformat(timespec="microseconds")
    starts = [e for e in events(main) if e["kind"] == "run-start"]
    assert [s["run"] for s in starts] == [base, f"{base}+2", f"{base}+3"]
    assert all(s["run"] == s["ts"] for s in starts)


def test_run_start_ids_carry_microseconds(repo_with_worktree):
    main, _ = repo_with_worktree
    add(main, "run-start")
    assert "." in events(main)[0]["run"]


def test_concurrent_run_starts_admit_exactly_one(repo_with_worktree):
    import threading

    main, _ = repo_with_worktree
    barrier = threading.Barrier(8, timeout=10)
    results: list = []

    def start():
        try:
            barrier.wait()
            results.append(runlog.append(main, "run-start", {}))
        except BaseException as exc:  # surfaced by the assertion below, never swallowed
            results.append(exc)

    threads = [threading.Thread(target=start, daemon=True) for _ in range(8)]  # daemon: a hung one cannot block exit
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=45)
    assert not any(t.is_alive() for t in threads), "a run-start never returned"
    assert not [r for r in results if isinstance(r, BaseException)], results
    logged = events(main)
    assert [e["kind"] for e in logged] == ["run-start"]
    refusals = [r for r in results if r is not None]
    assert len(results) == 8 and results.count(None) == 1 and len(refusals) == 7
    assert all(f"run {logged[0]['run']} is still open" in r and "runlog.py close --reason" in r for r in refusals)


def lock_is_held(lock) -> bool:
    """True when another open file description holds the run-log lock."""
    import fcntl

    with open(lock, "a") as probe:
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(probe, fcntl.LOCK_UN)
        return False


def test_every_append_holds_the_lock_from_its_read_to_its_write(repo_with_worktree, monkeypatch):
    """Plan review #32 rounds 1-2: an append that read run A must not write after a close and a new start.
    Checked directly, without threads: the lock is held at the read and at the write, in one acquisition."""
    import contextlib

    main, _ = repo_with_worktree
    add(main, "run-start")
    lock = runlog.log_path(main).with_name("run-log.lock")
    seen: list = []
    real_locked, real_read, real_write = runlog.locked, runlog.read_file, runlog._write

    @contextlib.contextmanager
    def traced_locked(path):
        with real_locked(path):
            seen.append("enter")
            yield
            seen.append("exit")

    def traced_read(path):
        seen.append(("read", lock_is_held(lock)))
        return real_read(path)

    def traced_write(path, event):
        seen.append(("write", lock_is_held(lock)))
        return real_write(path, event)

    monkeypatch.setattr(runlog, "locked", traced_locked)
    monkeypatch.setattr(runlog, "read_file", traced_read)
    monkeypatch.setattr(runlog, "_write", traced_write)
    one_acquisition = ["enter", ("read", True), ("write", True), "exit"]
    for call in (lambda: add(main, "note", "--text", "x"), lambda: add(main, "run-end"),
                 lambda: add(main, "run-start"), lambda: close(main, "--reason", "x")):
        seen.clear()
        assert call() == 0
        assert seen == one_acquisition


def test_an_append_waits_out_brief_contention(repo_with_worktree, monkeypatch):
    """Plan review #32 round 3: a held lock is retried, not refused on the first try."""
    import fcntl

    main, _ = repo_with_worktree
    add(main, "run-start")
    lock = runlog.log_path(main).with_name("run-log.lock")
    sleeps: list = []
    with open(lock, "a") as holder:
        fcntl.flock(holder, fcntl.LOCK_EX)

        def release_on_first_sleep(seconds):
            sleeps.append(seconds)
            if len(sleeps) == 1:
                fcntl.flock(holder, fcntl.LOCK_UN)

        monkeypatch.setattr(runlog, "_sleep", release_on_first_sleep)
        assert add(main, "note", "--text", "after the wait") == 0
    assert len(sleeps) == 1
    assert [e["kind"] for e in events(main)] == ["run-start", "note"]


def test_an_append_gives_up_at_the_lock_deadline_not_before(repo_with_worktree, monkeypatch, capsys):
    """A stuck holder fails the append with a message at LOCK_TIMEOUT, measured on a controlled clock."""
    import fcntl

    main, _ = repo_with_worktree
    add(main, "run-start")
    monkeypatch.setattr(runlog, "LOCK_TIMEOUT", 0.25)
    monkeypatch.setattr(runlog, "LOCK_POLL", 0.0625)
    clock = {"now": 0.0, "sleeps": 0}

    def fake_sleep(seconds):
        clock["sleeps"] += 1
        if clock["sleeps"] > 100:
            raise AssertionError("still polling after 100 sleeps: the deadline never arrives")
        clock["now"] += seconds

    monkeypatch.setattr(runlog, "_monotonic", lambda: clock["now"])
    monkeypatch.setattr(runlog, "_sleep", fake_sleep)
    lock = runlog.log_path(main).with_name("run-log.lock")
    with open(lock, "a") as holder:
        fcntl.flock(holder, fcntl.LOCK_EX)
        for call in (lambda: add(main, "note", "--text", "x"), lambda: close(main, "--reason", "x")):
            clock.update(now=0.0, sleeps=0)
            assert call() == 2
            assert 0.25 <= clock["now"] <= 0.25 + 0.0625
            assert 3 <= clock["sleeps"] <= 5
    out = capsys.readouterr().out
    assert out.count(f"run log is locked: {lock}") == 2
    assert [e["kind"] for e in events(main)] == ["run-start"]


def test_status_keeps_a_decision_left_open_by_an_earlier_run(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start", "--text", "run A")
    run_a = events(main)[0]["run"]
    add(main, "decision-needed", "--issue", "426", "--text", "Raidbots as the source?")
    add(main, "run-end")
    add(main, "run-start", "--text", "run B")
    add(main, "dispatched", "--issue", "427")
    add(main, "decision-made", "--issue", "427", "--text", "another issue's answer")
    runlog.main(["status", "--repo", str(main)])
    out = capsys.readouterr().out
    assert f"OPEN decision #426: Raidbots as the source? (from run {run_a})" in out
    assert "#427 decision-made another issue's answer" in out


def test_a_decision_made_in_a_later_run_resolves_the_earlier_one(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    add(main, "decision-needed", "--issue", "426", "--text", "Raidbots as the source?")
    add(main, "run-end")
    add(main, "run-start")
    add(main, "decision-made", "--issue", "426", "--text", "yes, Raidbots")
    runlog.main(["status", "--repo", str(main)])
    assert "OPEN decision #426" not in capsys.readouterr().out


def test_a_block_is_not_carried_into_the_next_run(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    add(main, "blocked", "--issue", "421", "--text", "reviewer down")
    add(main, "run-end")
    add(main, "run-start")
    runlog.main(["status", "--repo", str(main)])
    assert "OPEN blocked #421" not in capsys.readouterr().out


@pytest.mark.parametrize("outcome", ["resumed", "fresh", "failed", "unknown"])
def test_session_records_agent_role_and_outcome(repo_with_worktree, outcome):
    main, _ = repo_with_worktree
    add(main, "run-start")
    assert add(main, "session", "--agent", "pi_build", "--role", "builder", "--outcome", outcome) == 0
    last = events(main)[-1]
    assert (last["kind"], last["agent"], last["role"], last["outcome"]) == ("session", "pi_build", "builder", outcome)


@pytest.mark.parametrize("drop", ["agent", "role", "outcome"])
def test_session_needs_agent_role_and_outcome(repo_with_worktree, capsys, drop):
    main, _ = repo_with_worktree
    add(main, "run-start")
    fields = {"agent": "pi_build", "role": "builder", "outcome": "fresh"}
    del fields[drop]
    assert add(main, "session", *[x for k, v in fields.items() for x in (f"--{k}", v)]) == 2
    assert f"session needs --{drop}" in capsys.readouterr().out
    assert [e["kind"] for e in events(main)] == ["run-start"]


def test_session_outcome_must_be_one_of_four(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    with pytest.raises(SystemExit):
        add(main, "session", "--agent", "pi_build", "--role", "builder", "--outcome", "maybe")
    assert "invalid choice: 'maybe'" in capsys.readouterr().err
    assert [e["kind"] for e in events(main)] == ["run-start"]


def test_a_decision_made_before_the_question_does_not_resolve_it(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    add(main, "decision-made", "--issue", "426", "--text", "an older answer")
    add(main, "run-end")
    add(main, "run-start")
    add(main, "decision-needed", "--issue", "426", "--text", "Raidbots as the source?")
    runlog.main(["status", "--repo", str(main)])
    assert "OPEN decision #426: Raidbots as the source?" in capsys.readouterr().out


def test_status_does_not_render_session_events(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    add(main, "dispatched", "--issue", "421")
    add(main, "session", "--issue", "421", "--agent", "pi_build", "--role", "builder", "--outcome", "resumed")
    runlog.main(["status", "--repo", str(main)])
    out = capsys.readouterr().out
    assert "#421 dispatched" in out and "session" not in out
