import pathlib
import subprocess
import sys
import time

import pytest

import herdtool
import mutate

MUTATIONS = [
    ("M1", "src/calc.py", "return a + b\n", "return a - b\n", "tests/test_calc.py::test_add"),
    ("M2", "src/calc.py", "return a * b\n", "return a * b + 0\n", "tests/test_calc.py::test_add"),
    ("M3", "src/calc.py", "a * b", "b * a", "tests/test_calc.py::test_add"),
]


def render_tasks(muts=MUTATIONS) -> str:
    return "## 1. Tests first\n\n## 3. Mutation drives\n\n" + herdtool.render_mutations(muts)


def git(*args: str, cwd: pathlib.Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def build(tmp_path: pathlib.Path, monkeypatch) -> pathlib.Path:
    monkeypatch.setenv("HERD_PYTHON", sys.executable)
    w = tmp_path / "build"
    (w / "src").mkdir(parents=True)
    (w / "tests").mkdir()
    (w / "src" / "calc.py").write_text("def add(a, b):\n    return a + b\n\n\ndef mul(a, b):\n    return a * b\n")
    (w / "tests" / "test_calc.py").write_text("from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n")
    git("init", "-q", "-b", "main", cwd=w)
    git("add", ".", cwd=w)
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "base", cwd=w)
    return w


def test_parse_mutations_reads_name_file_texts_and_killer():
    parsed = herdtool.parse_mutations(render_tasks())
    assert [(m["name"], m["path"], m["test"]) for m in parsed] == [
        ("M1", "src/calc.py", "tests/test_calc.py::test_add"), ("M2", "src/calc.py", "tests/test_calc.py::test_add"),
        ("M3", "src/calc.py", "tests/test_calc.py::test_add")]
    assert parsed[0]["old"] == "return a + b\n" and parsed[0]["new"] == "return a - b\n"


def test_render_mutations_matches_what_render_printed_before():
    old, new = "x = 1\n", "x = 2\n"
    expected = (f"- [ ] **M1** in `src/a.py`: replace\n\n```python\n{old}```\n\nwith\n\n```python\n{new}```\n\n"
                "Killer: `tests/t.py::k`\n\n")
    assert herdtool.render_mutations([("M1", "src/a.py", old, new, "tests/t.py::k")]) == expected


def test_drive_reports_killed_and_survived_and_restores_every_file(build):
    before = (build / "src" / "calc.py").read_bytes()
    lines, failures = mutate.drive(render_tasks(), build)
    assert [ln.split(" ", 2)[:2] for ln in lines] == [["M1", "KILLED"], ["M2", "SURVIVED"], ["M3", "SURVIVED"]]
    assert "FAILED tests/test_calc.py::test_add" in lines[0]
    assert failures == 2
    assert (build / "src" / "calc.py").read_bytes() == before
    assert git("status", "--porcelain", cwd=build) == ""


def test_a_fragment_mutation_uses_the_newline_form_that_occurs_once(build):
    lines, _ = mutate.drive(render_tasks([MUTATIONS[2]]), build)
    assert lines[0].startswith("M3 SURVIVED")


def test_an_anchor_that_does_not_occur_once_voids_the_drive(build):
    muts = [("M9", "src/calc.py", "    return", "    return -", "tests/test_calc.py::test_add")]
    lines, failures = mutate.drive(render_tasks(muts), build)
    assert lines == ["M9 VOID anchor occurs 2 times in src/calc.py"]
    assert failures == 1


def test_a_drive_that_leaves_the_tree_changed_is_reported(build):
    (build / "tests" / "test_side.py").write_text(
        "import pathlib\n\n\ndef test_side():\n    pathlib.Path('stray.txt').write_text('x')\n")
    git("add", ".", cwd=build)
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "side", cwd=build)
    muts = [("M1", "src/calc.py", "return a + b\n", "return a - b\n", "tests/test_side.py::test_side")]
    lines, failures = mutate.drive(render_tasks(muts), build)
    assert lines[-1] == "TREE CHANGED after the drives: ?? stray.txt"
    assert failures == 2


def test_bytecode_is_cleared_everywhere_in_the_tree_not_only_src(build):
    subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_calc.py"],
                   cwd=build, env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin"}, capture_output=True)
    assert (build / "tests" / "__pycache__").exists()
    lines, _ = mutate.drive(render_tasks([MUTATIONS[0]]), build)
    assert lines[0].startswith("M1 KILLED")
    assert not list(build.rglob("__pycache__"))


def test_scratch_mode_drives_a_copy_and_never_touches_the_build(build):
    stamp = (build / "src" / "calc.py").stat().st_mtime_ns
    lines, _ = mutate.drive(render_tasks([MUTATIONS[0]]), build, scratch=True)
    assert lines[0].startswith("M1 KILLED")
    assert (build / "src" / "calc.py").stat().st_mtime_ns == stamp


def test_only_drives_the_named_mutations(build):
    lines, _ = mutate.drive(render_tasks(), build, only={"M2"})
    assert [ln.split(" ")[0] for ln in lines] == ["M2"]


@pytest.mark.parametrize("worktree", [".", "./", "absolute"])
def test_main_scratch_accepts_current_directory_and_preserves_source(build, monkeypatch, capsys, worktree):
    tasks = build / "SCRATCH-tasks.md"
    tasks.write_text(render_tasks())
    calc = build / "src" / "calc.py"
    before = calc.read_bytes()
    stamp = calc.stat().st_mtime_ns
    status = git("status", "--porcelain", cwd=build)
    monkeypatch.chdir(build)
    tree = str(build) if worktree == "absolute" else worktree

    assert mutate.main([str(tasks), tree, "--only", "M1", "--scratch"]) == 0

    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1 and lines[0].startswith("M1 KILLED")
    assert calc.read_bytes() == before
    assert calc.stat().st_mtime_ns == stamp
    assert git("status", "--porcelain", cwd=build) == status


def test_refuses_while_pytest_runs_in_the_worktree(build):
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)", "pytest"], cwd=build)
    try:
        time.sleep(0.2)
        with pytest.raises(SystemExit, match=f"pytest is running in {build}"):
            mutate.drive(render_tasks(), build)
    finally:
        proc.kill()
        proc.wait()


def test_a_process_that_only_mentions_pytest_does_not_block_the_drive(build):
    """A builder's `herdr agent prompt codex_review "<prompt>"`, run from the
    worktree, carries a prompt that says "pytest"; it is not pytest."""
    prompt = "Run the touched test files with pytest, then re-drive two mutations."
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)", prompt], cwd=build)
    try:
        time.sleep(0.2)
        lines, _ = mutate.drive(render_tasks(), build, only={"M1"})
        assert lines[0].startswith("M1 KILLED")
    finally:
        proc.kill()
        proc.wait()


@pytest.mark.parametrize("argv", [["pytest", "-q"], ["/venv/bin/pytest"], ["python", "-m", "pytest", "-q"]])
def test_each_way_of_running_pytest_is_seen(build, argv):
    assert mutate.is_pytest(argv)


def test_main_exits_nonzero_when_anything_survives(build, capsys):
    tasks = build / "SCRATCH-tasks.md"
    tasks.write_text(render_tasks([MUTATIONS[0], MUTATIONS[1]]))
    assert mutate.main([str(tasks), str(build)]) == 1
    out = capsys.readouterr().out
    assert "M1 KILLED" in out and "M2 SURVIVED" in out


def test_main_refuses_an_only_name_it_does_not_know_and_lists_the_names(build, capsys):
    # Proposal mutation-only-full-name (project-mera #502): `--only M1,M9` matched
    # no full label and exited 0 with no output, which read as a clean drive.
    tasks = build / "SCRATCH-tasks.md"
    tasks.write_text(render_tasks([("M1 swap the sign", *MUTATIONS[0][1:]), ("M2 add zero", *MUTATIONS[1][1:])]))

    assert mutate.main([str(tasks), str(build), "--only", "M1 swap the sign,M2"]) == 2

    out = capsys.readouterr().out.splitlines()
    assert out[0] == "--only names no mutation in this tasks.md: M2"
    assert out[1:] == ["available: M1 swap the sign", "available: M2 add zero"]
    assert "KILLED" not in "\n".join(out)


def test_main_with_no_mutations_is_an_error(build, capsys):
    tasks = build / "SCRATCH-tasks.md"
    tasks.write_text("## 3. Mutation drives\n")
    assert mutate.main([str(tasks), str(build)]) == 2
    assert "no mutations found" in capsys.readouterr().out


def test_parse_mutations_keeps_a_descriptive_name_suffix():
    muts = [("M1-pick-row-kept", "src/calc.py", "return a + b\n", "return a - b\n", "tests/test_calc.py::test_add")]
    assert herdtool.parse_mutations(render_tasks(muts))[0]["name"] == "M1-pick-row-kept"


def test_a_mid_line_fragment_resolves_both_texts_without_the_fence_newline(tmp_path):
    (tmp_path / "m.py").write_text("x = f(a, b) + 1\n")
    rendered = {"name": "M1", "path": "m.py", "old": "f(a, b)\n", "new": "g(a, b)\n", "test": "t"}
    assert mutate.resolve(tmp_path, rendered) == ("M1", "m.py", "f(a, b)", "g(a, b)", "t")


# A drive whose killer never ran proves nothing either way (project-mera
# #460): node-driven killers were skipped because the drive's PATH had no
# node, pytest exited 0 on the skips, and six page mutations read SURVIVED;
# a killer id pytest could not resolve exited non-zero and read KILLED.

def test_a_skipped_killer_is_not_run_rather_than_survived(build):
    (build / "tests" / "test_skip.py").write_text(
        "import pytest\n\n\n@pytest.mark.skip(reason='no node')\ndef test_skipped():\n    assert False\n")
    muts = [("M1", "src/calc.py", "return a + b\n", "return a - b\n", "tests/test_skip.py::test_skipped")]
    lines, failures = mutate.drive(render_tasks(muts), build)
    assert lines[0].startswith("M1 NOT RUN")
    assert failures == 1


def test_a_killer_pytest_cannot_find_is_not_run_rather_than_killed(build):
    muts = [("M1", "src/calc.py", "return a + b\n", "return a - b\n", "tests/test_calc.py::test_nope")]
    lines, failures = mutate.drive(render_tasks(muts), build)
    assert lines[0].startswith("M1 NOT RUN")
    assert failures == 1


def test_a_mutation_that_breaks_the_import_is_still_killed(build):
    muts = [("M1", "src/calc.py", "return a + b\n", "return a +\n", "tests/test_calc.py::test_add")]
    lines, _ = mutate.drive(render_tasks(muts), build)
    assert lines[0].startswith("M1 KILLED")


def test_a_test_that_rewrites_an_already_changed_file_is_reported(build):
    """A fixture the tests write was already untracked, so its status letter
    never changed when a mutated run rewrote its contents."""
    (build / "fixture.json").write_text("good\n")
    (build / "tests" / "test_writes.py").write_text(
        "import pathlib\n\n\ndef test_writes():\n    pathlib.Path('fixture.json').write_text('bad\\n')\n")
    muts = [("M1", "src/calc.py", "return a + b\n", "return a - b\n", "tests/test_writes.py::test_writes")]
    lines, failures = mutate.drive(render_tasks(muts), build)
    assert lines[-1] == "TREE CHANGED after the drives: content of fixture.json"
    assert failures == 2


def test_a_mutation_an_interrupted_drive_left_behind_is_restored_first(build):
    calc = build / "src" / "calc.py"
    original = calc.read_text()
    calc.write_text(original.replace("return a + b\n", "return a - b\n"))
    herdtool.write_inflight(build, calc, original)
    lines, _ = mutate.drive(render_tasks([MUTATIONS[0]]), build)
    assert lines[0] == "RESTORED src/calc.py, left mutated by an interrupted drive"
    assert lines[1].startswith("M1 KILLED")
    assert calc.read_text() == original
    assert not herdtool.inflight_path(build).exists()


def test_a_journal_naming_a_path_outside_the_tree_is_refused(build, tmp_path):
    """The journal names the file to restore; a path that resolves outside
    the tree is never written, only reported."""
    outside = tmp_path / "outside.txt"
    outside.write_text("keep\n")
    herdtool.inflight_path(build).write_text(
        '{"path": "../outside.txt", "original": "overwritten\\n"}', encoding="utf-8")
    lines, failures = mutate.drive(render_tasks([MUTATIONS[0]]), build)
    assert lines[0] == "REFUSED an interrupted-drive journal naming ../outside.txt, outside the tree"
    assert outside.read_text() == "keep\n"
    assert not herdtool.inflight_path(build).exists()
    assert failures >= 1


def test_render_mutations_refuses_a_name_the_parser_cannot_read_back():
    # project-mera #502: "P1" rendered fine and parsed to zero mutations, so
    # the builder's mutate.py found nothing to drive.
    with pytest.raises(ValueError, match="must start with 'M'"):
        herdtool.render_mutations([("P1 a drive", "src/a.py", "x\n", "y\n", "tests/t.py::k")])


def test_every_rendered_mutation_parses_back():
    muts = [("M1 one", "src/a.py", "x\n", "y\n", "tests/t.py::k"),
            ("M2 two", "src/b.py", "p\n", "q\n", "tests/t.py::j")]

    parsed = herdtool.parse_mutations(herdtool.render_mutations(muts))

    assert [m["name"] for m in parsed] == ["M1 one", "M2 two"]
