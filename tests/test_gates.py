import pathlib
import subprocess

import pytest

import gates


@pytest.mark.parametrize("line, counts", [
    ("6386 passed, 1 skipped, 7 deselected, 1 warning in 499.80s (0:08:19)",
     {"passed": 6386, "skipped": 1, "deselected": 7}),
    ("53 failed, 2 passed", {"failed": 53, "passed": 2}),
    ("===== 3 failed, 1 error in 0.2s =====", {"failed": 3, "error": 1}),
    ("1 passed, 2 errors", {"passed": 1, "error": 2}),
    ("2 xfailed, 1 xpassed, 4 passed", {"xfailed": 2, "xpassed": 1, "passed": 4}),
    ("no tests ran in 0.01s", {}),
])
def test_pytest_lines_parse_to_counts_without_warnings_or_time(line, counts):
    assert gates.parse(line) == ("pytest", counts)


@pytest.mark.parametrize("line, counts", [
    ("Success: no issues found in 10 source files", {"errors": 0, "files": 0, "checked": 10}),
    ("Found 9 errors in 2 files (checked 13 source files)", {"errors": 9, "files": 2, "checked": 13}),
    ("Found 1 error in 1 file (checked 1 source file)", {"errors": 1, "files": 1, "checked": 1}),
])
def test_mypy_lines_parse_to_error_file_and_checked_counts(line, counts):
    assert gates.parse(line) == ("mypy", counts)


def test_any_other_line_is_compared_literally():
    assert gates.parse("  All checks passed!  ") == ("literal", "All checks passed!")


def test_counts_match_when_pytest_appends_warnings_and_time():
    assert gates.compare("6524 passed, 1 skipped, 7 deselected",
                         "6524 passed, 1 skipped, 7 deselected, 1 warning in 752.47s (0:12:32)") == []


def test_a_count_difference_names_the_count():
    assert gates.compare("6524 passed, 1 skipped", "6523 passed, 1 failed, 1 skipped") == [
        "passed: expected 6524, got 6523", "failed: expected 0, got 1"]


def test_mypy_checked_count_is_part_of_the_gate():
    assert gates.compare("Success: no issues found in 10 source files",
                         "Success: no issues found in 11 source files") == ["checked: expected 10, got 11"]


def test_a_different_kind_of_line_is_a_mismatch():
    assert gates.compare("7 passed", "Success: no issues found in 7 source files") == [
        "expected a pytest line, got a mypy line"]


def test_literal_lines_must_match_exactly():
    assert gates.compare("All checks passed!", "Found 1 error.") == [
        "expected 'All checks passed!', got 'Found 1 error.'"]


def test_match_reads_the_last_nonblank_line_of_a_file(tmp_path, capsys):
    out = tmp_path / "suite.txt"
    out.write_text("...\nFAILED tests/x.py::t\n6523 passed, 1 failed in 3s\n\n")
    assert gates.main(["match", "6524 passed", str(out)]) == 1
    assert capsys.readouterr().out.splitlines() == [
        "MISMATCH 6524 passed", "  passed: expected 6524, got 6523", "  failed: expected 0, got 1"]


def test_match_prints_match_and_exits_zero(tmp_path, capsys):
    out = tmp_path / "suite.txt"
    out.write_text("6524 passed, 1 warning in 3s\n")
    assert gates.main(["match", "6524 passed", str(out)]) == 0
    assert capsys.readouterr().out.strip() == "MATCH 6524 passed"


def git(*args: str, cwd: pathlib.Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def build(tmp_path: pathlib.Path) -> pathlib.Path:
    git("init", "-q", "-b", "main", cwd=tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("a = 1\n")
    (tmp_path / "src" / "b.py").write_text("b = 1\n")
    git("add", ".", cwd=tmp_path)
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "base", cwd=tmp_path)
    (tmp_path / "src" / "a.py").write_text("a = 2\n")
    (tmp_path / "src" / "new.py").write_text("n = 1\n")
    for coord in ("BUILD-BRIEFING-7.md", "HANDOFF-7.md", "REVIEW-7-round-1.md", "CODEX-PROMPT-7.md",
                  "ALLOWED-7.txt", "RED-7-tail.txt", "GREEN-runner.log", "FULLSUITE-7-tail.txt",
                  "MUTATION-LOG.txt", "SCRATCH-apply.py"):
        (tmp_path / coord).write_text("x\n")
    return tmp_path


def test_manifest_lists_modified_and_untracked_files_but_not_coordination_files(build):
    assert gates.manifest(build, "main") == [("M", "src/a.py"), ("A", "src/new.py")]


def test_manifest_reports_a_stray_root_file(build):
    (build / "mutate.py").write_text("x\n")
    assert ("A", "mutate.py") in gates.manifest(build, "main")


def test_manifest_includes_a_deleted_file(build):
    (build / "src" / "b.py").unlink()
    assert ("D", "src/b.py") in gates.manifest(build, "main")


def test_outside_allowed_lists_files_not_in_the_allowed_list(build):
    changed = gates.manifest(build, "main")
    assert gates.outside_allowed(changed, "  - src/a.py\n  - `src/new.py`\n") == []
    assert gates.outside_allowed(changed, "- src/a.py\n") == ["src/new.py"]


def test_manifest_command_exits_one_on_a_file_outside_allowed(build, capsys):
    allowed = build / "ALLOWED-7.txt"
    allowed.write_text("  - src/a.py\n")
    assert gates.main(["manifest", str(build), "main", "--allowed", str(allowed)]) == 1
    assert capsys.readouterr().out.splitlines() == [
        "M src/a.py", "A src/new.py", "OUTSIDE ALLOWED: src/new.py"]


def test_an_allowed_entry_is_its_backticked_path_without_the_annotation():
    changed = [("M", "src/mera/check/compare.py"), ("M", "src/x.py")]
    allowed = "  - `src/mera/check/compare.py` (rewritten whole)\n  - plus your own `HANDOFF-7.md`\n  - src/x.py\n"
    assert gates.outside_allowed(changed, allowed) == []


def test_an_allowed_entry_ending_in_a_slash_allows_everything_under_it():
    changed = [("A", "openspec/changes/fix-x/tasks.md"), ("A", "openspec/changes/fix-y/tasks.md")]
    assert gates.outside_allowed(changed, "  - `openspec/changes/fix-x/`\n") == ["openspec/changes/fix-y/tasks.md"]


def test_only_root_level_files_count_as_coordination(build):
    (build / "REVIEW-tools").mkdir()
    (build / "REVIEW-tools" / "helper.py").write_text("x\n")
    assert ("A", "REVIEW-tools/helper.py") in gates.manifest(build, "main")


def test_a_lead_ruling_file_is_coordination_not_a_change(build):
    (build / "RULING-7-1.md").write_text("x\n")
    assert gates.manifest(build, "main") == [("M", "src/a.py"), ("A", "src/new.py")]


def test_the_changes_own_spec_copy_is_allowed_through_the_allowed_file_mkbrief_writes(build):
    """mkbrief appends `openspec/changes/<change>/` to ALLOWED; only that change's copy passes."""
    for name in ("fix-x", "fix-y"):
        (build / "openspec" / "changes" / name).mkdir(parents=True)
        (build / "openspec" / "changes" / name / "tasks.md").write_text("x\n")
    changed = gates.manifest(build, "main")
    allowed = "- src/a.py\n- src/new.py\n  - `openspec/changes/fix-x/`\n"
    assert gates.outside_allowed(changed, allowed) == ["openspec/changes/fix-y/tasks.md"]


def test_count_is_literal_so_shell_and_regex_characters_mean_themselves(tmp_path):
    page = tmp_path / "check.html"
    page.write_text("$('press').disabled = x;\n$('press').disabled = y;\nother\n")
    assert gates.count("$('press').disabled", [page]) == 2
    assert gates.count("a.b", [page]) == 0


def test_count_sweeps_only_python_files_in_a_directory_and_skips_bytecode(tmp_path):
    src = tmp_path / "src"
    (src / "__pycache__").mkdir(parents=True)
    (src / "a.py").write_text("folded over every pull\n")
    (src / "b.txt").write_text("folded over every pull\n")
    (src / "__pycache__" / "a.cpython-312.pyc").write_bytes(b"folded over every pull\n")
    assert gates.count("folded over every pull", [src]) == 1
    assert gates.count("folded over every pull", [src], include="*.txt") == 1


def test_count_command_prints_zero_and_exits_zero_on_no_match(tmp_path, capsys):
    f = tmp_path / "a.py"
    f.write_text("x = 1\n")
    assert gates.main(["count", "nothing here", str(f)]) == 0
    assert capsys.readouterr().out == "0\n"


def test_count_regex_is_opt_in(tmp_path):
    f = tmp_path / "a.py"
    f.write_text('group["difficulty"])\n')
    assert gates.count(r'group\["difficulty"\]\)', [f], regex=True) == 1


# --- accepted proposal 2026-09-25-full-suite-rerun-after-fold --------------------

def test_the_full_suite_is_refused_while_a_fold_is_pending(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    gates.main(["fold", "start", "--issue", "40", "--repo", str(main)])
    assert gates.main(["suite-ok", "--issue", "40", "--repo", str(main)]) == 2
    assert "a fold of #40 is pending" in capsys.readouterr().out
    gates.main(["fold", "done", "--issue", "40", "--repo", str(main)])
    assert gates.main(["suite-ok", "--issue", "40", "--repo", str(main)]) == 0


def test_a_second_suite_run_in_one_build_state_is_warned_unless_a_ruling_reopens_it(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    assert gates.main(["suite-ok", "--issue", "40", "--repo", str(main)]) == 0
    assert gates.main(["suite-ok", "--issue", "40", "--repo", str(main)]) == 1
    assert "already ran for this build-state" in capsys.readouterr().out
    assert gates.main(["suite-ok", "--issue", "40", "--ruling", "--repo", str(main)]) == 0
    assert gates.main(["suite-ok", "--issue", "40", "--ruling", "--repo", str(main)]) == 1


def test_a_finished_fold_starts_a_new_build_state(repo_with_worktree):
    main, _ = repo_with_worktree
    gates.main(["suite-ok", "--issue", "40", "--repo", str(main)])
    gates.main(["fold", "start", "--issue", "40", "--repo", str(main)])
    gates.main(["fold", "done", "--issue", "40", "--repo", str(main)])
    assert gates.main(["suite-ok", "--issue", "40", "--repo", str(main)]) == 0
    assert gates.main(["suite-ok", "--issue", "41", "--repo", str(main)]) == 0  # issues are independent
