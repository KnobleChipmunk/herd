import json
import pathlib
import subprocess

import pytest

import merge_stack


@pytest.fixture(autouse=True)
def no_real_librarian(monkeypatch):
    """No test starts a real Hermes; tests that check the launch record it here."""
    started = []
    monkeypatch.setattr(merge_stack, "launch", lambda cmd, log: started.append((cmd, log)) or 4242)
    monkeypatch.setattr(merge_stack.shutil, "which", lambda name: f"/usr/bin/{name}")
    return started


def git(*args: str, cwd: pathlib.Path) -> str:
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout


class FakeGH:
    """gh with PR states in a dict; `pr merge` flips OPEN to MERGED unless told to fail."""

    def __init__(self, states: dict[str, str], bases: dict[str, str] | None = None, fail: set[str] = frozenset(),
                 queued: set[str] = frozenset()):
        self.states, self.bases, self.fail, self.queued, self.calls = dict(states), bases or {}, fail, queued, []

    def __call__(self, args: list[str]) -> subprocess.CompletedProcess:
        self.calls.append(args)
        pr = args[2]
        if args[:2] == ["pr", "view"]:
            out = json.dumps({"state": self.states[pr], "baseRefName": self.bases.get(pr, "main")})
            return subprocess.CompletedProcess(args, 0, out, "")
        if args[:2] == ["pr", "merge"]:
            if pr in self.fail:
                return subprocess.CompletedProcess(args, 1, "", "Pull request is not mergeable: conflicts")
            if pr not in self.queued:
                self.states[pr] = "MERGED"
            return subprocess.CompletedProcess(args, 0, "", "")
        raise AssertionError(args)


def pr_events(*prs: tuple[str, str]) -> list[dict]:
    return [{"kind": "run-start"}] + [{"kind": "pr-opened", "issue": i, "pr": p, "branch": f"fix/{i}"} for i, p in prs]


def test_merges_open_prs_in_the_order_they_were_opened():
    gh = FakeGH({"429": "OPEN", "431": "OPEN"})
    lines, merged, ok = merge_stack.merge_prs(pr_events(("421", "429"), ("422", "431")), gh, apply=True)
    assert ok and merged == {"421", "422"}
    assert [c[2] for c in gh.calls if c[1] == "merge"] == ["429", "431"]
    assert lines == ["merged PR #429 (#421)", "merged PR #431 (#422)"]


def test_every_merge_uses_a_true_merge_and_deletes_the_branch():
    gh = FakeGH({"429": "OPEN"})
    merge_stack.merge_prs(pr_events(("421", "429")), gh, apply=True)
    assert ["pr", "merge", "429", "--merge", "--delete-branch"] in gh.calls


def test_an_already_merged_pr_is_skipped_so_a_rerun_is_safe():
    gh = FakeGH({"429": "MERGED", "431": "OPEN"})
    lines, merged, ok = merge_stack.merge_prs(pr_events(("421", "429"), ("422", "431")), gh, apply=True)
    assert ok and merged == {"421", "422"}
    assert lines[0] == "already merged PR #429 (#421)"


def test_a_failed_merge_stops_the_stack():
    gh = FakeGH({"429": "OPEN", "431": "OPEN", "432": "OPEN"}, fail={"431"})
    lines, merged, ok = merge_stack.merge_prs(pr_events(("421", "429"), ("422", "431"), ("423", "432")), gh,
                                              apply=True)
    assert not ok and merged == {"421"}
    assert lines[-1] == "STOP PR #431 (#422): Pull request is not mergeable: conflicts; later PRs are stacked on it"
    assert "432" not in [c[2] for c in gh.calls if c[1] == "merge"]


def test_a_pr_that_does_not_target_main_stops_the_stack():
    gh = FakeGH({"429": "OPEN"}, bases={"429": "fix/420-x"})
    lines, _, ok = merge_stack.merge_prs(pr_events(("421", "429")), gh, apply=True)
    assert not ok
    assert lines == ["STOP PR #429 (#421): targets fix/420-x, not main"]
    assert not [c for c in gh.calls if c[1] == "merge"]


def test_a_closed_pr_stops_the_stack():
    gh = FakeGH({"429": "CLOSED"})
    lines, _, ok = merge_stack.merge_prs(pr_events(("421", "429")), gh, apply=True)
    assert not ok and lines == ["STOP PR #429 (#421): CLOSED"]


def test_a_dry_run_merges_nothing_and_says_what_it_would_do():
    gh = FakeGH({"429": "OPEN", "431": "MERGED"})
    lines, merged, ok = merge_stack.merge_prs(pr_events(("421", "429"), ("422", "431")), gh, apply=False)
    assert ok and merged == {"421", "422"}
    assert lines == ["would merge PR #429 (#421)", "already merged PR #431 (#422)"]
    assert not [c for c in gh.calls if c[1] == "merge"]


@pytest.fixture
def origin_and_main(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    """A bare origin, the operator's main checkout, and a second clone standing in for GitHub's merges."""
    origin = tmp_path / "origin.git"
    git("init", "-q", "--bare", "-b", "main", str(origin), cwd=tmp_path)
    main = tmp_path / "main"
    git("clone", "-q", str(origin), str(main), cwd=tmp_path)
    (main / "README").write_text("r\n")
    git("add", ".", cwd=main)
    git("commit", "-q", "-m", "base", cwd=main)
    git("push", "-q", "origin", "main", cwd=main)
    hub = tmp_path / "hub"
    git("clone", "-q", str(origin), str(hub), cwd=tmp_path)
    return origin, main, hub


def land_on_origin(hub: pathlib.Path, rel: str, body: str) -> None:
    (hub / rel).parent.mkdir(parents=True, exist_ok=True)
    (hub / rel).write_text(body)
    git("add", ".", cwd=hub)
    git("commit", "-q", "-m", "merged PR", cwd=hub)
    git("push", "-q", "origin", "main", cwd=hub)


def test_pull_removes_an_untracked_copy_identical_to_what_merged(origin_and_main):
    _, main, hub = origin_and_main
    land_on_origin(hub, "openspec/changes/x/tasks.md", "the spec\n")
    (main / "openspec" / "changes" / "x").mkdir(parents=True)
    (main / "openspec" / "changes" / "x" / "tasks.md").write_text("the spec\n")
    lines, ok = merge_stack.pull_main(main, apply=True)
    assert ok
    assert lines == ["removed untracked openspec/changes/x/tasks.md (identical to origin/main)", "pulled main"]
    assert git("log", "-1", "--format=%s", cwd=main).strip() == "merged PR"


def test_pull_stops_when_an_untracked_copy_differs_and_keeps_it(origin_and_main):
    _, main, hub = origin_and_main
    land_on_origin(hub, "openspec/changes/x/tasks.md", "the merged spec\n")
    (main / "openspec" / "changes" / "x").mkdir(parents=True)
    (main / "openspec" / "changes" / "x" / "tasks.md").write_text("a stale local spec\n")
    lines, ok = merge_stack.pull_main(main, apply=True)
    assert not ok
    assert lines == ["STOP untracked openspec/changes/x/tasks.md differs from origin/main; compare and move it first"]
    assert (main / "openspec" / "changes" / "x" / "tasks.md").read_text() == "a stale local spec\n"


def test_pull_refuses_when_the_main_checkout_is_not_on_main(origin_and_main):
    _, main, _ = origin_and_main
    git("checkout", "-q", "-b", "other", cwd=main)
    lines, ok = merge_stack.pull_main(main, apply=True)
    assert not ok and lines == ["STOP the main checkout is on other, not main"]


def test_a_dry_run_pull_changes_nothing(origin_and_main):
    _, main, hub = origin_and_main
    land_on_origin(hub, "x.txt", "x\n")
    head = git("rev-parse", "HEAD", cwd=main)
    lines, ok = merge_stack.pull_main(main, apply=False)
    assert ok and lines == ["would pull main"]
    assert git("rev-parse", "HEAD", cwd=main) == head


@pytest.fixture
def created(origin_and_main):
    """The main checkout with a merged build worktree, an unmerged one, and a scratch reference."""
    _, main, _ = origin_and_main
    trees = main.parent / "trees"
    git("worktree", "add", "-q", "-b", "fix/421", str(trees / "421"), cwd=main)
    git("worktree", "add", "-q", "-b", "fix/422", str(trees / "422"), cwd=main)
    (trees / "422" / "wip.py").write_text("x\n")
    git("-C", str(trees / "422"), "add", ".", cwd=main)
    git("-C", str(trees / "422"), "commit", "-q", "-m", "unmerged work", cwd=main)
    git("worktree", "add", "-q", "-b", "scratch/pre-421", str(trees / "pre-421"), cwd=main)
    (trees / "pre-421" / "ref.py").write_text("x\n")
    git("-C", str(trees / "pre-421"), "add", ".", cwd=main)
    git("-C", str(trees / "pre-421"), "commit", "-q", "-m", "reference", cwd=main)
    events = [{"kind": "run-start"},
              {"kind": "worktree-created", "issue": "421", "worktree": str(trees / "421"), "branch": "fix/421"},
              {"kind": "worktree-created", "issue": "422", "worktree": str(trees / "422"), "branch": "fix/422"},
              {"kind": "scratch-created", "issue": "421", "worktree": str(trees / "pre-421"),
               "branch": "scratch/pre-421"}]
    return main, trees, events


def branches(main: pathlib.Path) -> set[str]:
    return set(git("branch", "--format=%(refname:short)", cwd=main).split())


def test_cleanup_removes_only_what_the_log_created_for_merged_issues(created):
    main, trees, events = created
    lines = merge_stack.cleanup(main, events, merged={"421"}, apply=True)
    assert not (trees / "421").exists() and not (trees / "pre-421").exists()
    assert (trees / "422").exists()
    assert branches(main) == {"main", "fix/422"}
    assert lines == [f"removed worktree {trees / '421'}", "deleted branch fix/421",
                     f"kept worktree {trees / '422'} (#422 not merged)",
                     f"removed worktree {trees / 'pre-421'}", "deleted scratch branch scratch/pre-421"]


def test_cleanup_never_forces_a_worktree_with_uncommitted_work(created):
    main, trees, events = created
    (trees / "421" / "notes.txt").write_text("in progress\n")
    lines = merge_stack.cleanup(main, events, merged={"421"}, apply=True)
    assert (trees / "421" / "notes.txt").exists()
    assert lines[0].startswith(f"KEPT worktree {trees / '421'}: ")
    assert not any("fix/421" in ln for ln in lines)
    assert "fix/421" in branches(main)


def test_a_build_branch_with_commits_not_on_main_is_kept_not_forced(created):
    main, trees, events = created
    (trees / "421" / "late.py").write_text("x\n")
    git("-C", str(trees / "421"), "add", ".", cwd=main)
    git("-C", str(trees / "421"), "commit", "-q", "-m", "a commit that never reached the PR", cwd=main)
    lines = merge_stack.cleanup(main, events, merged={"421"}, apply=True)
    assert lines[0] == f"removed worktree {trees / '421'}"
    assert lines[1].startswith("KEPT branch fix/421: ")
    assert "fix/421" in branches(main)


def test_cleanup_skips_what_is_already_gone_so_a_rerun_is_safe(created):
    main, trees, events = created
    merge_stack.cleanup(main, events, merged={"421"}, apply=True)
    lines = merge_stack.cleanup(main, events, merged={"421"}, apply=True)
    assert lines[:2] == [f"already gone {trees / '421'}", "already gone fix/421"]


def test_a_dry_run_cleanup_removes_nothing(created):
    main, trees, events = created
    lines = merge_stack.cleanup(main, events, merged={"421"}, apply=False)
    assert (trees / "421").exists() and "fix/421" in branches(main)
    assert lines[0] == f"would remove worktree {trees / '421'}"


def test_main_merges_pulls_and_cleans_up_in_one_command(created, monkeypatch, capsys):
    main, trees, events = created
    log = main.parent / "run-log.jsonl"
    log.write_text("".join(json.dumps(e) + "\n" for e in
                           events + [{"kind": "pr-opened", "issue": "421", "pr": "429", "branch": "fix/421"}]))
    gh = FakeGH({"429": "OPEN"})
    monkeypatch.setattr(merge_stack, "gh_runner", lambda repo: gh)
    assert merge_stack.main(["--repo", str(main), "--log", str(log), "--apply"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "merged PR #429 (#421)"
    assert "pulled main" in out
    assert f"removed worktree {trees / '421'}" in out
    assert any(ln.startswith("next: archive the merged openspec changes") for ln in out)


def test_main_without_apply_is_a_dry_run(created, monkeypatch, capsys):
    main, trees, events = created
    log = main.parent / "run-log.jsonl"
    log.write_text("".join(json.dumps(e) + "\n" for e in
                           events + [{"kind": "pr-opened", "issue": "421", "pr": "429", "branch": "fix/421"}]))
    monkeypatch.setattr(merge_stack, "gh_runner", lambda repo: FakeGH({"429": "OPEN"}))
    assert merge_stack.main(["--repo", str(main), "--log", str(log)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "DRY RUN (pass --apply to act)"
    assert (trees / "421").exists()


def test_a_merge_that_reports_success_but_leaves_the_pr_open_stops_the_stack():
    gh = FakeGH({"429": "OPEN", "431": "OPEN"}, queued={"429"})
    lines, merged, ok = merge_stack.merge_prs(pr_events(("421", "429"), ("422", "431")), gh, apply=True)
    assert not ok and merged == set()
    assert lines[-1].startswith("STOP PR #429 (#421): ")


def test_main_exits_one_when_the_stack_stops(created, monkeypatch, capsys):
    main, _, events = created
    log = main.parent / "run-log.jsonl"
    log.write_text("".join(json.dumps(e) + "\n" for e in
                           events + [{"kind": "pr-opened", "issue": "421", "pr": "429", "branch": "fix/421"}]))
    monkeypatch.setattr(merge_stack, "gh_runner", lambda repo: FakeGH({"429": "CLOSED"}))
    assert merge_stack.main(["--repo", str(main), "--log", str(log), "--apply"]) == 1


def write_log(main: pathlib.Path, events: list[dict], extra: list[dict] = ()) -> pathlib.Path:
    log = main.parent / "run-log.jsonl"
    log.write_text("".join(json.dumps(e) + "\n" for e in [*events, *extra,
                   {"kind": "pr-opened", "issue": "421", "pr": "429", "branch": "fix/421"}]))
    return log


def test_a_successful_apply_starts_the_librarian_in_the_background(created, monkeypatch, capsys, no_real_librarian):
    main, _, events = created
    log = write_log(main, events)
    monkeypatch.setattr(merge_stack, "gh_runner", lambda repo: FakeGH({"429": "OPEN"}))
    assert merge_stack.main(["--repo", str(main), "--log", str(log), "--apply"]) == 0
    (cmd, librarian_log), = no_real_librarian
    assert cmd[:4] == ["hermes", "-s", "herd-librarian", "-z"] and str(main) in cmd[4]
    assert librarian_log.parent == log.parent and librarian_log.name.startswith("librarian-")
    out = capsys.readouterr().out.splitlines()
    assert out[-1] == f"librarian started in the background (pid 4242); its report: {librarian_log}"
    assert json.loads(log.read_text().splitlines()[-1])["text"].startswith("librarian started")


def test_a_rerun_does_not_start_the_librarian_twice(created, monkeypatch, capsys, no_real_librarian):
    main, _, events = created
    log = write_log(main, events, [{"kind": "note", "text": "librarian started (log: x)"}])
    monkeypatch.setattr(merge_stack, "gh_runner", lambda repo: FakeGH({"429": "MERGED"}))
    merge_stack.main(["--repo", str(main), "--log", str(log), "--apply"])
    assert no_real_librarian == []
    assert capsys.readouterr().out.splitlines()[-1] == "librarian already handled this run (see the run log); not starting it again"


def test_no_librarian_skips_it(created, monkeypatch, capsys, no_real_librarian):
    main, _, events = created
    log = write_log(main, events)
    monkeypatch.setattr(merge_stack, "gh_runner", lambda repo: FakeGH({"429": "OPEN"}))
    merge_stack.main(["--repo", str(main), "--log", str(log), "--apply", "--no-librarian"])
    assert no_real_librarian == []
    assert "librarian" not in capsys.readouterr().out.splitlines()[-1]


def test_a_stopped_stack_does_not_start_the_librarian(created, monkeypatch, no_real_librarian):
    main, _, events = created
    log = write_log(main, events)
    monkeypatch.setattr(merge_stack, "gh_runner", lambda repo: FakeGH({"429": "CLOSED"}))
    merge_stack.main(["--repo", str(main), "--log", str(log), "--apply"])
    assert no_real_librarian == []


def test_a_dry_run_says_it_would_start_the_librarian(created, monkeypatch, capsys, no_real_librarian):
    main, _, events = created
    log = write_log(main, events)
    monkeypatch.setattr(merge_stack, "gh_runner", lambda repo: FakeGH({"429": "OPEN"}))
    merge_stack.main(["--repo", str(main), "--log", str(log)])
    assert no_real_librarian == []
    assert capsys.readouterr().out.splitlines()[-1] == "would start the librarian (Hermes herd-librarian)"


def test_without_hermes_it_says_how_to_run_the_librarian_by_hand(created, monkeypatch, capsys, no_real_librarian):
    main, _, events = created
    log = write_log(main, events)
    monkeypatch.setattr(merge_stack, "gh_runner", lambda repo: FakeGH({"429": "OPEN"}))
    monkeypatch.setattr(merge_stack.shutil, "which", lambda name: None)
    merge_stack.main(["--repo", str(main), "--log", str(log), "--apply"])
    assert no_real_librarian == []
    last = capsys.readouterr().out.splitlines()[-1]
    assert last.startswith("librarian NOT started: hermes is not on PATH; run: hermes -s herd-librarian -z ")


def test_a_dry_run_on_a_run_the_librarian_already_handled_says_so(created, monkeypatch, capsys, no_real_librarian):
    main, _, events = created
    log = write_log(main, events, [{"kind": "note", "text": "librarian: skipped, reconstructed run"}])
    monkeypatch.setattr(merge_stack, "gh_runner", lambda repo: FakeGH({"429": "MERGED"}))
    merge_stack.main(["--repo", str(main), "--log", str(log)])
    assert capsys.readouterr().out.splitlines()[-1] == "librarian already handled this run (see the run log); not starting it again"
