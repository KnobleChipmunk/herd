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
