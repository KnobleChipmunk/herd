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
