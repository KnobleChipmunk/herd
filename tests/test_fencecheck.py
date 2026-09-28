import pathlib

import pytest

import fencecheck
import herdtool

BASE = {
    "src/replace.py": "a = 1\nb = 2\nc = 3\n",
    "src/insert.py": "def f():\n    pass\n",
    "src/append.py": "x = 1\n",
    "src/whole.py": "old body\n",
    "src/desc.py": "def g():\n    return 1\n",
    "src/inline.py": "value = compute(a, b) + 1\n",
    "src/anchor.py": "total = base + extra\n",
}

TESTS = [
    {"kind": "new_file", "path": "tests/test_new.py", "new": "def test_x():\n    assert '```' != ''\n",
     "why": "a new file whose body holds a triple backtick"},
    {"kind": "replace", "path": "src/replace.py", "old": "b = 2\n", "new": "b = 20\n", "why": "replace a line"},
]
IMPL = [
    {"kind": "insert_before", "path": "src/insert.py", "old": "def f():\n", "new": "import os\n\n\n",
     "why": "insert before an anchor"},
    {"kind": "append", "path": "src/append.py", "new": "\n\ny = 2\n", "why": "append at the end"},
    {"kind": "whole_file", "path": "src/whole.py", "new": "new body\nline two\n", "why": "replace the whole file"},
    {"kind": "replace", "path": "src/desc.py", "old": "    return 1\n", "new": "    return 2\n",
     "old_desc": "Replace the body of `g`.", "why": "replace described in prose"},
    {"kind": "replace", "path": "src/inline.py", "old": "compute(a, b)", "new": "compute(a, b, c)",
     "why": "replace a mid-line fragment with no trailing newline"},
    {"kind": "insert_before", "path": "src/anchor.py", "old": "extra", "new": "2 * ",
     "why": "insert before a mid-line anchor"},
]


def render(tests=TESTS, impl=IMPL) -> str:
    return ("# header the lead wrote\n\n```text\nnot a step fence\n```\n\n## 1. Tests first (expect RED)\n\n"
            + herdtool.render_steps(tests, 1, "T") + "\n\n## 2. Implementation (expect GREEN)\n\n"
            + herdtool.render_steps(impl, 1, "I")
            + "\n\n## 3. Mutation drives\n\n- [ ] **M1** in `src/replace.py`: replace\n\n```python\nb = 20\n```\n")


@pytest.fixture
def built(tmp_path: pathlib.Path) -> pathlib.Path:
    for rel, body in BASE.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(body)
    for step in TESTS + IMPL:
        herdtool.apply_step(tmp_path, step)
    return tmp_path


def test_parse_finds_every_step_and_no_mutation_or_header_fence():
    steps = herdtool.parse_tasks(render())
    assert [s["name"] for s in steps] == ["T1", "T2", "I1", "I2", "I3", "I4", "I5", "I6"]
    assert [s["kind"] for s in steps] == ["new_file", "replace", "insert_before", "append", "whole_file",
                                         "replace", "replace", "insert_before"]


def test_parse_reads_a_four_backtick_fence_whole():
    new_file = herdtool.parse_tasks(render())[0]
    assert new_file["new"] == TESTS[0]["new"]


def test_parse_leaves_old_empty_for_a_prose_described_replace():
    desc = herdtool.parse_tasks(render())[5]
    assert desc["old"] is None
    assert desc["new"] == "    return 2\n"


def test_a_correct_build_passes_every_step(built):
    assert fencecheck.check(render(), built) == []


@pytest.mark.parametrize("rel, mutate, step, reason", [
    ("tests/test_new.py", lambda t: t.replace("!=", "=="), "T1", "file differs from the fence at line 2"),
    ("src/replace.py", lambda t: t.replace("b = 20", "b = 21"), "T2", "replacement text not found"),
    ("src/replace.py", lambda t: t + "b = 2\n", "T2", "replaced text still present"),
    ("src/insert.py", lambda t: t.replace("import os\n\n\n", "import os\n\n"), "I1",
     "inserted text not found exactly once before its anchor"),
    ("src/append.py", lambda t: t + "z = 3\n", "I2", "file does not end with the appended text"),
    ("src/whole.py", lambda t: t.replace("line two", "line 2"), "I3", "file differs from the fence at line 2"),
    ("src/desc.py", lambda t: t.replace("return 2", "return 3"), "I4", "replacement text not found"),
    ("src/inline.py", lambda t: t.replace("compute(a, b, c)", "compute(a, c)"), "I5",
     "replacement text not found"),
    ("src/inline.py", lambda t: t.replace("+ 1", "+ compute(a, b) + 1"), "I5", "replaced text still present"),
    ("src/anchor.py", lambda t: t.replace("2 * extra", "3 * extra"), "I6",
     "inserted text not found exactly once before its anchor"),
])
def test_a_deviation_names_the_step_and_why(built, rel, mutate, step, reason):
    path = built / rel
    path.write_text(mutate(path.read_text()))
    assert fencecheck.check(render(), built) == [f"{step} `{rel}`: {reason}"]


def test_a_missing_file_is_reported(built):
    (built / "tests" / "test_new.py").unlink()
    assert fencecheck.check(render(), built) == ["T1 `tests/test_new.py`: file missing"]


def test_whole_file_with_an_extra_trailing_line_is_a_deviation(built):
    path = built / "src" / "whole.py"
    path.write_text(path.read_text() + "\n")
    assert fencecheck.check(render(), built) == ["I3 `src/whole.py`: file differs from the fence at line 3"]


def test_main_exits_nonzero_and_prints_each_deviation(built, capsys):
    (built / "src" / "append.py").write_text("x = 1\n")
    tasks = built / "tasks.md"
    tasks.write_text(render())
    assert fencecheck.main([str(tasks), str(built)]) == 1
    assert "I2 `src/append.py`: file does not end with the appended text" in capsys.readouterr().out


def test_main_exits_zero_and_counts_steps_when_clean(built, capsys):
    tasks = built / "tasks.md"
    tasks.write_text(render())
    assert fencecheck.main([str(tasks), str(built)]) == 0
    assert capsys.readouterr().out.strip() == "FENCES OK (8 steps)"


def test_a_markdown_heading_inside_a_fence_does_not_end_the_step(tmp_path):
    readme = {"kind": "append", "path": "README.md", "new": "\n## `data.json` — a new bundle\n\nSource: x.\n",
              "why": "document the bundle"}
    (tmp_path / "README.md").write_text("# Data\n")
    herdtool.apply_step(tmp_path, readme)
    text = "## 2. Implementation\n\n" + herdtool.render_steps([readme], 1, "I") + "\n\n## 3. Mutation drives\n"
    assert herdtool.parse_tasks(text)[0]["new"] == readme["new"]
    assert fencecheck.check(text, tmp_path) == []


def test_a_tasks_file_with_no_steps_is_an_error_not_a_pass(built, capsys):
    tasks = built / "tasks.md"
    tasks.write_text("# nothing here\n")
    assert fencecheck.main([str(tasks), str(built)]) == 2
    assert "no T/I steps found" in capsys.readouterr().out


@pytest.mark.parametrize("rendered, sources", [
    ("x = 1\n", ["x = 1\n", "x = 1"]),
    ("import os\n\n\n", ["import os\n\n\n"]),
    ("a\n\n", ["a\n\n"]),
])
def test_forms_lists_only_the_sources_fence_could_have_rendered(rendered, sources):
    assert fencecheck.forms(rendered) == sources


def test_projection_reports_each_anchor_and_final_parity_without_writing(built, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("projection must not apply steps or load plan code")

    monkeypatch.setattr(herdtool, "apply_step", forbidden)
    monkeypatch.setattr(herdtool, "load", forbidden)
    impl = [s for s in IMPL if not s.get("old_desc")]
    text = render(impl=impl)
    before = {str(p.relative_to(built)): p.read_bytes() for p in built.rglob("*") if p.is_file()}
    lines, failed = fencecheck.project(text, BASE, built)
    assert not failed
    assert "T1 `tests/test_new.py`: anchors=n/a (new_file)" in lines
    assert "I2 `src/append.py`: anchors=n/a (append)" in lines
    assert "I3 `src/whole.py`: anchors=n/a (whole_file)" in lines
    assert "T2 `src/replace.py`: anchors=1" in lines
    assert "I4 `src/inline.py`: anchors=1" in lines
    assert "I5 `src/anchor.py`: anchors=1" in lines
    assert "PARITY `src/inline.py`: OK" in lines
    assert len([line for line in lines if line.startswith("PARITY")]) == 7
    assert before == {str(p.relative_to(built)): p.read_bytes() for p in built.rglob("*") if p.is_file()}
    assert BASE["src/replace.py"] == "a = 1\nb = 2\nc = 3\n"


def test_projection_handles_sequential_inline_replacements(tmp_path):
    steps = [dict(kind="replace", path="x.py", old="one", new="two", why="first"),
             dict(kind="replace", path="x.py", old="two", new="three", why="second")]
    (tmp_path / "x.py").write_text("value = three + 1\n")
    lines, failed = fencecheck.project(render(tests=[], impl=steps), {"x.py": "value = one + 1\n"}, tmp_path)
    assert not failed
    assert "I1 `x.py`: anchors=1" in lines and "I2 `x.py`: anchors=1" in lines
    assert "PARITY `x.py`: OK" in lines


@pytest.mark.parametrize("base,reason", [("wrong\n", "anchors=0"), ("old\nold\n", "anchors=2")])
def test_projection_refuses_nonunique_anchors(tmp_path, base, reason):
    step = dict(kind="replace", path="x.py", old="old\n", new="new\n", why="replace")
    (tmp_path / "x.py").write_text(base.replace("old\n", "new\n", 1))
    lines, failed = fencecheck.project(render(tests=[], impl=[step]), {"x.py": base}, tmp_path)
    assert failed and any(reason in line for line in lines)


@pytest.mark.parametrize("kind,base,reason", [
    ("new_file", {"x.py": "old\n"}, "file already exists in base"),
    ("whole_file", {}, "file missing from base"),
    ("append", {"x.py": "old\n\n"}, "file end not a single newline"),
])
def test_projection_checks_file_preconditions(tmp_path, kind, base, reason):
    step = dict(kind=kind, path="x.py", new="new\n", why="change")
    (tmp_path / "x.py").write_text("new\n")
    lines, failed = fencecheck.project(render(tests=[], impl=[step]), base, tmp_path)
    assert failed and any(reason in line for line in lines)
    assert f"I1 `x.py`: anchors=n/a ({kind})" in lines


def test_projection_rejects_prose_only_replace(built):
    lines, failed = fencecheck.project(render(), BASE, built)
    assert failed and any("I4 `src/desc.py`: quoted old text required" == line for line in lines)


def test_projection_detects_final_drift_and_missing_reference(tmp_path):
    steps = [dict(kind="replace", path="x.py", old="old\n", new="new\n", why="replace"),
             dict(kind="new_file", path="missing.py", new="body\n", why="create")]
    (tmp_path / "x.py").write_text("new\nextra\n")
    lines, failed = fencecheck.project(render(tests=[], impl=steps), {"x.py": "old\n"}, tmp_path)
    assert failed
    assert "PARITY `x.py`: DIFFERS" in lines
    assert "PARITY `missing.py`: reference missing" in lines


def test_projection_preserves_required_blank_line_forms(tmp_path):
    step = dict(kind="insert_before", path="x.py", old="def f():\n", new="import os\n\n\n", why="insert")
    (tmp_path / "x.py").write_text("import os\n\ndef f():\n    pass\n")
    lines, failed = fencecheck.project(render(tests=[], impl=[step]), {"x.py": "def f():\n    pass\n"}, tmp_path)
    assert failed and "PARITY `x.py`: DIFFERS" in lines


def test_projection_cli_uses_pinned_git_blobs_without_writing(repo_with_worktree, capsys):
    import subprocess

    _, wt = repo_with_worktree
    (wt / "x.py").write_text("old\n")
    subprocess.run(["git", "add", "x.py"], cwd=wt, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"], cwd=wt, check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=wt, text=True).strip()
    (wt / "x.py").write_text("new\n")
    tasks = wt / "tasks.md"
    tasks.write_text(render(tests=[], impl=[dict(kind="replace", path="x.py", old="old\n", new="new\n", why="replace")]))
    before = {p: p.read_bytes() for p in (wt / "x.py", tasks)}
    assert fencecheck.main([str(tasks), str(wt), "--base", base]) == 0
    output = capsys.readouterr().out
    assert "I1 `x.py`: anchors=1" in output and "PARITY `x.py`: OK" in output
    assert output.rstrip().endswith("PROJECTION OK (1 steps)")
    assert before == {p: p.read_bytes() for p in before}
    for invalid in ("missing-ref", ""):
        assert fencecheck.main([str(tasks), str(wt), "--base", invalid]) == 2
        assert "invalid base" in capsys.readouterr().out
    tasks.write_text("# no steps\n")
    assert fencecheck.main([str(tasks), str(wt), "--base", base]) == 2
    assert "no T/I steps" in capsys.readouterr().out


def test_plan_review_names_the_read_only_projection_command():
    root = pathlib.Path(fencecheck.__file__).resolve().parent.parent
    card = (root / "skill/cards/plan-reviewer.md").read_text()
    assert "--base <pinned-base-sha>" in card
    assert "in memory" in card and "never writes files" in card
    assert "never imports or executes plan code" in card
    assert "projection command in `skill/cards/plan-reviewer.md`" in (root / "skill/SKILL.md").read_text()
