import sys

import pytest

import mkbrief


def brief(repo_with_worktree, **overrides):
    main, wt = repo_with_worktree
    args = dict(id="42", worktree=wt, branch="fix/42-x", base="main", change="fix-x",
                gates="GATES\n", allowed="  - src/x.py", python="/py/bin/python",
                lead_pane="w9:p9Z", reviewer="codex_review", has_xdist=False)
    args.update(overrides)
    return main, wt, mkbrief.build_briefing(**args), mkbrief.build_reviewer_prompt(**args)


def test_briefing_names_the_derived_main_checkout(repo_with_worktree):
    main, _, briefing, _ = brief(repo_with_worktree)
    assert f"Do NOT touch `{main.resolve()}`" in briefing


def test_briefing_sends_rounds_to_the_named_reviewer_and_sentinels_to_the_lead_pane(repo_with_worktree):
    _, _, briefing, _ = brief(repo_with_worktree, reviewer="claude_review", lead_pane="w3:p7Q")
    assert 'herdr agent prompt claude_review "$(cat CODEX-PROMPT-42-round-N.md)"' in briefing
    assert "herdr agent wait claude_review --timeout 540000" in briefing
    assert 'herdr agent prompt w3:p7Q "DONE: build for 42' in briefing
    assert 'herdr agent prompt w3:p7Q "BLOCKED: 42' in briefing


def test_reviewer_prompt_signs_off_to_the_lead_pane(repo_with_worktree):
    _, _, _, prompt = brief(repo_with_worktree, lead_pane="w3:p7Q")
    assert 'herdr agent prompt w3:p7Q "REVIEW CLEAN for 42 after ROUND_N rounds"' in prompt


def test_briefing_and_prompt_use_the_given_python(repo_with_worktree):
    _, _, briefing, prompt = brief(repo_with_worktree, python="/venvs/x/bin/python")
    assert "`/venvs/x/bin/python`" in briefing
    assert "PYTHONPATH=src /venvs/x/bin/python -m pytest" in prompt


def test_reviewer_prompt_runs_the_fence_checker_instead_of_reading_fences_by_eye(repo_with_worktree):
    _, wt, _, prompt = brief(repo_with_worktree)
    cmd = f"python3 {mkbrief.FENCECHECK} {wt}/openspec/changes/fix-x/tasks.md {wt}"
    assert cmd in prompt
    assert mkbrief.FENCECHECK.name == "fencecheck.py" and mkbrief.FENCECHECK.is_absolute()


def test_briefing_has_the_builder_run_the_fence_checker_into_the_handoff(repo_with_worktree):
    _, wt, briefing, _ = brief(repo_with_worktree)
    assert f"python3 {mkbrief.FENCECHECK} openspec/changes/fix-x/tasks.md ." in briefing
    assert "`FENCES OK (<n> steps)`" in briefing


def test_briefing_says_xdist_is_missing_when_it_is(repo_with_worktree):
    _, _, briefing, _ = brief(repo_with_worktree, has_xdist=False)
    assert "`pytest-xdist` is NOT installed. Do not install anything." in briefing


def test_briefing_says_xdist_is_available_when_it_is(repo_with_worktree):
    _, _, briefing, _ = brief(repo_with_worktree, has_xdist=True)
    assert "`pytest-xdist` is installed" in briefing
    assert "NOT installed" not in briefing


def test_lead_pane_comes_from_herdr_pane_id(monkeypatch):
    monkeypatch.setenv("HERDR_PANE_ID", "w5:p5A")
    assert mkbrief.resolve_lead_pane(None) == "w5:p5A"


def test_explicit_lead_pane_wins_over_herdr_pane_id(monkeypatch):
    monkeypatch.setenv("HERDR_PANE_ID", "w5:p5A")
    assert mkbrief.resolve_lead_pane("w1:p1B") == "w1:p1B"


def test_missing_lead_pane_is_an_error_naming_both_sources(monkeypatch):
    monkeypatch.delenv("HERDR_PANE_ID", raising=False)
    with pytest.raises(SystemExit, match="--lead-pane.*HERDR_PANE_ID"):
        mkbrief.resolve_lead_pane(None)


def test_main_writes_both_files(repo_with_worktree, tmp_path, monkeypatch):
    _, wt = repo_with_worktree
    monkeypatch.setenv("HERDR_PANE_ID", "w5:p5A")
    monkeypatch.setenv("HERD_PYTHON", sys.executable)
    gates = tmp_path / "gates.txt"
    gates.write_text("G\n")
    allowed = tmp_path / "allowed.txt"
    allowed.write_text("  - src/x.py\n")
    mkbrief.main(["42", str(wt), "fix/42-x", "main", "fix-x", str(gates), str(allowed)])
    assert "w5:p5A" in (wt / "BUILD-BRIEFING-42.md").read_text()
    assert "codex_review" in (wt / "BUILD-BRIEFING-42.md").read_text()
    assert (wt / "CODEX-PROMPT-42.md").exists()


def head_sha(path):
    import subprocess
    return subprocess.run(["git", "-C", str(path), "rev-parse", "main"], capture_output=True, text=True,
                          check=True).stdout.strip()


def test_briefing_and_prompt_pin_the_base_to_one_sha(repo_with_worktree):
    main, wt, briefing, prompt = brief(repo_with_worktree)
    sha = head_sha(main)
    assert f"cut from main ({sha})" in briefing
    assert f"git -C {wt} diff {sha}" in prompt


def test_a_base_that_is_not_a_git_ref_is_an_error(repo_with_worktree):
    with pytest.raises(SystemExit, match="not a git ref.*origin/nowhere"):
        brief(repo_with_worktree, base="origin/nowhere")


def test_reviewer_prompt_lists_changes_with_the_manifest_against_the_allowed_file(repo_with_worktree):
    main, wt, _, prompt = brief(repo_with_worktree)
    assert f"python3 {mkbrief.GATES} manifest {wt} {head_sha(main)} --allowed {wt}/ALLOWED-42.txt" in prompt
    assert "OUTSIDE ALLOWED" in prompt


def test_briefing_gates_are_matched_by_counts_with_the_gate_tool(repo_with_worktree):
    _, _, briefing, _ = brief(repo_with_worktree)
    assert f'python3 {mkbrief.GATES} match "<expected line>" <output file>' in briefing
    assert "literal last lines" not in briefing


def test_briefing_names_temporary_files_scratch(repo_with_worktree):
    _, _, briefing, _ = brief(repo_with_worktree)
    assert "name them `SCRATCH-<anything>`" in briefing


def test_main_writes_the_allowed_file_with_the_spec_directory(repo_with_worktree, tmp_path, monkeypatch):
    _, wt = repo_with_worktree
    monkeypatch.setenv("HERDR_PANE_ID", "w5:p5A")
    monkeypatch.setenv("HERD_PYTHON", sys.executable)
    gates_file = tmp_path / "gates.txt"
    gates_file.write_text("G\n")
    allowed = tmp_path / "allowed.txt"
    allowed.write_text("  - `src/x.py`\n")
    mkbrief.main(["42", str(wt), "fix/42-x", "main", "fix-x", str(gates_file), str(allowed)])
    assert (wt / "ALLOWED-42.txt").read_text() == "  - `src/x.py`\n  - `openspec/changes/fix-x/`\n"


def test_briefing_has_the_builder_drive_mutations_with_the_runner(repo_with_worktree):
    _, _, briefing, _ = brief(repo_with_worktree)
    assert f"python3 {mkbrief.MUTATE} openspec/changes/fix-x/tasks.md ." in briefing


def test_reviewer_prompt_re_drives_two_mutations_on_a_scratch_copy(repo_with_worktree):
    _, wt, _, prompt = brief(repo_with_worktree)
    assert f"python3 {mkbrief.MUTATE} {wt}/openspec/changes/fix-x/tasks.md {wt} --scratch --only " in prompt


def test_builder_and_reviewer_log_friction_to_the_run_log_under_their_own_names(repo_with_worktree):
    _, wt, briefing, prompt = brief(repo_with_worktree, reviewer="codex_review")
    assert (f'python3 {mkbrief.RUNLOG} add friction --repo {wt} --issue 42 --agent pi_build --text "<what cost you'
            in briefing)
    assert (f'python3 {mkbrief.RUNLOG} add friction --repo {wt} --issue 42 --agent codex_review --text "<what cost'
            in prompt)
