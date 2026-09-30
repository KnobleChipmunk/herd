import sys

import pytest

import mkbrief


def write_tasks(worktree, body="# Plan\n\n## 0. Gates\n\n510 passed\nM1–M5\nFENCES OK (11 steps)\n\n## 1. Tests first\n"):
    path = worktree / "openspec/changes/fix-x/tasks.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return path


def brief(repo_with_worktree, **overrides):
    main, wt = repo_with_worktree
    if not (wt / "openspec/changes/fix-x/tasks.md").exists():
        write_tasks(wt)
    args = dict(id="42", worktree=wt, branch="fix/42-x", base="main", change="fix-x",
                allowed="  - src/x.py", python="/py/bin/python",
                lead_pane="w9:p9Z", reviewer="codex_review", has_xdist=False)
    args.update(overrides)
    return main, wt, mkbrief.build_briefing(**args), mkbrief.build_reviewer_prompt(**args)


def test_briefing_names_the_derived_main_checkout(repo_with_worktree):
    main, _, briefing, _ = brief(repo_with_worktree)
    assert f"Do NOT touch `{main.resolve()}`" in briefing


def test_briefing_sends_rounds_to_the_named_reviewer_and_sentinels_to_the_lead_pane(repo_with_worktree):
    _, _, briefing, _ = brief(repo_with_worktree, reviewer="claude_review", lead_pane="w3:p7Q")
    assert "tools/dispatch.py claude_review --file CODEX-PROMPT-42-round-N.md" in briefing
    assert "herdr agent wait" not in briefing  # the dispatch tool waits (proposal herdr-wait-not-idle)
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
    write_tasks(wt)
    allowed = tmp_path / "allowed.txt"
    allowed.write_text("  - src/x.py\n")
    mkbrief.main(["42", str(wt), "fix/42-x", "main", "fix-x", str(allowed)])
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
    write_tasks(wt)
    allowed = tmp_path / "allowed.txt"
    allowed.write_text("  - `src/x.py`\n")
    mkbrief.main(["42", str(wt), "fix/42-x", "main", "fix-x", str(allowed)])
    assert (wt / "ALLOWED-42.txt").read_text() == "  - `src/x.py`\n  - `openspec/changes/fix-x/`\n"


def test_briefing_has_the_builder_drive_mutations_with_the_runner(repo_with_worktree):
    _, _, briefing, _ = brief(repo_with_worktree)
    assert f"python3 {mkbrief.MUTATE} openspec/changes/fix-x/tasks.md ." in briefing


def test_reviewer_prompt_re_drives_two_mutations_on_a_scratch_copy(repo_with_worktree):
    _, wt, _, prompt = brief(repo_with_worktree)
    assert f"python3 {mkbrief.MUTATE} {wt}/openspec/changes/fix-x/tasks.md {wt} --scratch --only " in prompt


def test_builder_and_reviewer_log_friction_to_the_run_log_under_their_own_names(repo_with_worktree):
    _, wt, briefing, prompt = brief(repo_with_worktree, reviewer="codex_review", builder="pi_build")
    assert (f'python3 {mkbrief.RUNLOG} add friction --repo {wt} --issue 42 --agent pi_build --text "<what cost you'
            in briefing)
    assert (f'python3 {mkbrief.RUNLOG} add friction --repo {wt} --issue 42 --agent codex_review --text "<what cost'
            in prompt)


def test_reviewer_prompt_names_what_the_manifest_skips_from_the_manifests_own_list(repo_with_worktree):
    import gates
    _, _, _, prompt = brief(repo_with_worktree)
    for pattern in gates.COORDINATION:
        assert f"`{pattern}`" in prompt, pattern
    assert "`openspec/changes/fix-x/` is the change's own spec copy" in prompt


def test_reviewer_prompt_reads_the_fence_checkers_success_line_as_success(repo_with_worktree):
    import fencecheck
    _, _, _, prompt = brief(repo_with_worktree)
    assert "other than `FENCES OK` is a finding" not in prompt
    assert f"a line starting `{fencecheck.OK}`" in prompt


def test_a_codex_reviewer_runs_tests_and_herdr_outside_its_sandbox_from_the_first_try(repo_with_worktree):
    _, _, _, prompt = brief(repo_with_worktree)
    assert mkbrief.CODEX_SANDBOX in prompt
    assert "outside the sandbox" in mkbrief.CODEX_SANDBOX
    for command in ("pytest", "herdr agent prompt", "mutate.py"):
        assert command in mkbrief.CODEX_SANDBOX, command
    assert "timeout 600" in mkbrief.CODEX_SANDBOX


def test_a_claude_reviewer_gets_no_codex_sandbox_rule(repo_with_worktree):
    _, _, _, prompt = brief(repo_with_worktree, reviewer="claude_review")
    assert mkbrief.CODEX_SANDBOX not in prompt


def test_fence_owned_findings_block_in_the_same_review_round(repo_with_worktree):
    _, _, briefing, prompt = brief(repo_with_worktree)
    assert "FINDINGS: <n> (spec)" in prompt
    assert 'tag it "in the fence"' in prompt
    assert "never mark it FOLDED" in prompt
    assert "unresolved findings prevent REVIEW CLEAN" in prompt
    assert "FINDINGS: <n> (spec)" in briefing
    assert "send BLOCKED to the lead in the same round" in briefing
    assert "Do not edit the fence or the spec" in briefing
    recovery = briefing.split("Wait for the lead", 1)[1].split("Otherwise", 1)[0]
    assert "re-run ALL gates" in recovery
    assert "update the handoff" in recovery
    assert "send the next round" in recovery
    assert "once per build-state" in briefing
    assert "If the lead accepts a fence change" in recovery
    assert "If the lead rejects the finding" in recovery
    assert "without waiting for a fold" in recovery
    assert "the lead installs any regenerated test fences" in recovery
    assert "re-apply the affected implementation files" in recovery


def test_main_regenerates_suite_mutation_and_fence_literals_from_tasks(repo_with_worktree, tmp_path, monkeypatch):
    _, wt = repo_with_worktree
    monkeypatch.setenv("HERD_PYTHON", sys.executable)
    tasks = write_tasks(wt)
    allowed = tmp_path / "allowed.txt"
    allowed.write_text("tools/x.py\n")
    args = ["42", str(wt), "fix/42-x", "main", "fix-x", str(allowed), "--lead-pane", "w5:p5A"]
    mkbrief.main(args)
    first = (wt / "BUILD-BRIEFING-42.md").read_text()
    for literal in ("510 passed", "M1–M5", "FENCES OK (11 steps)"):
        assert literal in first
    tasks.write_text(tasks.read_text().replace("510 passed", "512 passed").replace("M1–M5", "M1–M7")
                     .replace("11 steps", "13 steps"))
    mkbrief.main(args)
    second = (wt / "BUILD-BRIEFING-42.md").read_text()
    for old, new in (("510 passed", "512 passed"), ("M1–M5", "M1–M7"), ("11 steps", "13 steps")):
        assert old not in second and new in second
    before = {p: p.read_bytes() for p in wt.glob("*-42.*")}
    tasks.write_text("# No gates\n")
    with pytest.raises(SystemExit, match="exactly one nonempty.*Gates"):
        mkbrief.main(args)
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("body", ["# no section\n", "## 0. Gates\n\n## 1. Tests\n",
                                   "## 0. Gates\nA\n## 0. Gates\nB\n", "    ## 0. Gates\nbody\n"])
def test_invalid_task_gates_fail_clearly(repo_with_worktree, body):
    _, wt = repo_with_worktree
    write_tasks(wt, body)
    with pytest.raises(SystemExit, match="exactly one nonempty.*Gates"):
        mkbrief.task_gates(wt, "fix-x")


def test_missing_tasks_names_the_unreadable_file(repo_with_worktree):
    _, wt = repo_with_worktree
    with pytest.raises(SystemExit, match="cannot read.*tasks.md"):
        mkbrief.task_gates(wt, "fix-x")


def test_gate_section_respects_fenced_headings_and_stops_at_next_section(repo_with_worktree):
    _, wt = repo_with_worktree
    body = ("# Plan\n````python\n## 0. Gates\nfalse\n````\n## 0. Gates\n"
            "510 passed\n```text\n## example output\n```\n## 1. Tests\nnot a gate\n"
            "~~~text\n## 0. Gates\nfalse again\n~~~\n")
    write_tasks(wt, body)
    assert mkbrief.task_gates(wt, "fix-x") == "510 passed\n```text\n## example output\n```\n"
    write_tasks(wt, "## 0. Gates\n \n    python3 -m pytest  \n\t\n## 1. Tests\n")
    assert mkbrief.task_gates(wt, "fix-x") == "    python3 -m pytest  \n"


def test_handoff_carries_a_match_line_for_every_pytest_count_gate(repo_with_worktree):
    # Two builders (pi on #333, Codex on #482) read the pytest counts off a
    # saved tail and ran the tool only for the grep gates; the handoff item
    # scoped the tool line to grep gates.
    _, _, briefing, _ = brief(repo_with_worktree)
    handoff = briefing[briefing.index("## Handoff"):]
    item = handoff[handoff.index("\n4. "):handoff.index("\n5. ")]
    assert f"python3 {mkbrief.GATES} match" in item
    assert "every pytest count gate" in item and "MATCH line" in item


def test_the_builder_logs_friction_under_the_name_it_is_given(repo_with_worktree):
    _, wt, briefing, _ = brief(repo_with_worktree, builder="codex_build")
    assert "--issue 42 --agent codex_build --text" in briefing
    assert "--agent pi_build" not in briefing


def test_a_codex_builder_gets_one_escalation_bullet_per_command_class(repo_with_worktree):
    _, _, briefing, _ = brief(repo_with_worktree, builder="codex_build")
    assert mkbrief.CODEX_BUILDER_SANDBOX in briefing
    bullets = [ln.strip() for ln in mkbrief.CODEX_BUILDER_SANDBOX.splitlines()[1:] if ln.strip().startswith("- ")]
    for command in ("pytest", "full suite", "network", "mutate.py", "dispatch.py", "herdr agent prompt"):
        hits = [b for b in bullets if command in b]
        assert len(hits) == 1 and "OUTSIDE the sandbox" in hits[0], command
    assert "timeout 900" in mkbrief.CODEX_BUILDER_SANDBOX


def test_a_pi_builder_gets_no_sandbox_rule(repo_with_worktree):
    _, _, briefing, _ = brief(repo_with_worktree, builder="pi_build")
    assert mkbrief.CODEX_BUILDER_SANDBOX not in briefing
    assert "--issue 42 --agent pi_build --text" in briefing


def test_the_builder_applies_steps_from_the_emitted_json_when_the_lead_wrote_one(repo_with_worktree):
    _, wt, without, _ = brief(repo_with_worktree)
    assert "STEPS-42.json" not in without
    (wt / "STEPS-42.json").write_text("[]\n")
    _, _, briefing, _ = brief(repo_with_worktree)
    assert "`STEPS-42.json`" in briefing
    assert "never copy fence text out of tasks.md" in briefing


def test_main_passes_the_builder_name_through(repo_with_worktree, tmp_path, monkeypatch):
    _, wt = repo_with_worktree
    monkeypatch.setenv("HERDR_PANE_ID", "w5:p5A")
    monkeypatch.setenv("HERD_PYTHON", sys.executable)
    write_tasks(wt)
    allowed = tmp_path / "allowed.txt"
    allowed.write_text("  - src/x.py\n")
    mkbrief.main(["42", str(wt), "fix/42-x", "main", "fix-x", str(allowed), "--builder", "codex_build"])
    assert "--agent codex_build" in (wt / "BUILD-BRIEFING-42.md").read_text()


def test_the_default_builder_is_the_codex_builder_with_its_sandbox_list(repo_with_worktree, tmp_path, monkeypatch):
    # The roster's builder is Codex on the local profile (2026-09-30); the
    # command line's default names it, so its briefing carries the sandbox list.
    main, wt = repo_with_worktree
    write_tasks(wt)
    allowed = tmp_path / "allowed.txt"
    allowed.write_text("  - src/x.py\n")
    monkeypatch.setenv("HERDR_PANE_ID", "w9:p9Z")
    mkbrief.main(["42", str(wt), "fix/42-x", "main", "fix-x", str(allowed)])
    briefing = (wt / "BUILD-BRIEFING-42.md").read_text()
    assert "--issue 42 --agent codex_build --text" in briefing
    assert mkbrief.CODEX_BUILDER_SANDBOX in briefing
