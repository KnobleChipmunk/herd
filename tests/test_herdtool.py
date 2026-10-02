import pathlib
import sys

import pytest

import herdtool


def test_main_checkout_of_a_linked_worktree_is_the_primary_checkout(repo_with_worktree):
    main, wt = repo_with_worktree
    assert herdtool.main_checkout(wt) == main.resolve()


def test_main_checkout_of_the_primary_checkout_is_itself(repo_with_worktree):
    main, _ = repo_with_worktree
    assert herdtool.main_checkout(main) == main.resolve()


def test_find_python_prefers_herd_python_env(repo_with_worktree, monkeypatch):
    _, wt = repo_with_worktree
    monkeypatch.setenv("HERD_PYTHON", "/opt/custom/python")
    assert herdtool.find_python(wt) == "/opt/custom/python"


def test_find_python_uses_the_main_checkout_venv(repo_with_worktree, monkeypatch):
    main, wt = repo_with_worktree
    monkeypatch.delenv("HERD_PYTHON", raising=False)
    venv_py = main / ".venv" / "bin" / "python"
    venv_py.parent.mkdir(parents=True)
    venv_py.write_text("")
    assert herdtool.find_python(wt) == str(venv_py.resolve())


def test_find_python_falls_back_to_the_running_interpreter(repo_with_worktree, monkeypatch):
    _, wt = repo_with_worktree
    monkeypatch.delenv("HERD_PYTHON", raising=False)
    assert herdtool.find_python(wt) == sys.executable


def test_mutate_env_takes_home_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    env = herdtool.mutate_env()
    assert env["HOME"] == str(tmp_path)
    assert env["PYTHONPATH"] == "src"
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"


@pytest.mark.parametrize("name", ["herdtool.py", "mkbrief.py", "wait_file.sh", "watch_review.sh"])
def test_no_tool_carries_a_machine_path_or_a_run_specific_pane(name):
    text = (pathlib.Path(herdtool.__file__).parent / name).read_text()
    for banned in ("/home/tusk", "project-mera", "w1:p1S", "opus_review"):
        assert banned not in text, (name, banned)


def test_mutate_env_keeps_node_on_the_path(monkeypatch, tmp_path):
    """Node-driven killer tests skip when node is missing, and a skip is not
    a kill; node often lives outside /usr/bin (nvm)."""
    node = tmp_path / "nvm" / "bin" / "node"
    node.parent.mkdir(parents=True)
    node.write_text("#!/bin/sh\n")
    node.chmod(0o755)
    monkeypatch.setenv("PATH", f"{node.parent}:/usr/bin:/bin")
    assert str(node.parent) in herdtool.mutate_env()["PATH"].split(":")


PLAN = '''
TESTS = [
    {"kind": "new_file", "path": "tests/test_new.py", "new": "def test_x():\\n    pass\\n", "why": "new"},
]
IMPL = [
    {"kind": "insert_before", "path": "src/anchor.py", "old": "extra", "new": "2 * ", "why": "mid-line insert"},
    {"kind": "replace", "path": "src/inline.py", "old": "compute(a, b)", "new": "compute(a, b, c)",
     "why": "mid-line replace"},
    {"kind": "append", "path": "src/append.py", "new": "\\n\\ny = 2\\n", "why": "append"},
]
MUTATIONS = []
'''


def test_emit_steps_writes_exact_bytes_a_builder_can_apply_without_the_markdown(tmp_path, monkeypatch):
    """A fence always ends with a newline, so a mid-line fragment cannot be read back
    exactly from tasks.md; the JSON comes from the plan and keeps the exact bytes."""
    plan = tmp_path / "plan.py"
    plan.write_text(PLAN)
    out = tmp_path / "STEPS-42.json"
    monkeypatch.setattr(sys, "argv", ["herdtool.py", str(plan), "emit-steps", str(out)])
    herdtool.main()

    import json
    steps = json.loads(out.read_text())
    assert [(s["name"], s["kind"], s["path"]) for s in steps] == [
        ("T1", "new_file", "tests/test_new.py"),
        ("I1", "insert_before", "src/anchor.py"),
        ("I2", "replace", "src/inline.py"),
        ("I3", "append", "src/append.py"),
    ]
    assert steps[1]["old"] == "extra" and steps[1]["new"] == "2 * "
    assert steps[0]["old"] is None

    base = {"src/anchor.py": "total = base + extra\n", "src/inline.py": "value = compute(a, b) + 1\n",
            "src/append.py": "x = 1\n"}
    for tree in (tmp_path / "from_json", tmp_path / "from_plan"):
        for rel, body in base.items():
            (tree / rel).parent.mkdir(parents=True, exist_ok=True)
            (tree / rel).write_text(body)
    for s in steps:
        herdtool.apply_step(tmp_path / "from_json", s)
    mod = herdtool.load(str(plan))
    for s in mod.TESTS + mod.IMPL:
        herdtool.apply_step(tmp_path / "from_plan", s)
    for rel in [*base, "tests/test_new.py"]:
        assert (tmp_path / "from_json" / rel).read_text() == (tmp_path / "from_plan" / rel).read_text(), rel
    assert (tmp_path / "from_json" / "src/anchor.py").read_text() == "total = base + 2 * extra\n"


@pytest.mark.parametrize("name", ["librarian.py", "merge_stack.py"])
def test_no_librarian_tool_defaults_to_a_personal_path(name):
    text = (pathlib.Path(herdtool.__file__).parent / name).read_text()
    for banned in ("/home/", "~/projects", "Exocortex", "Obsidian"):
        assert banned not in text, (name, banned)


def _render(tmp_path, monkeypatch, capsys, plan_text):
    plan = tmp_path / "plan.py"
    plan.write_text(plan_text)
    monkeypatch.setattr(sys, "argv", ["herdtool.py", str(plan), "render", str(tmp_path)])
    herdtool.main()
    return capsys.readouterr().out


READBACK_PLAN = PLAN.replace(
    "MUTATIONS = []",
    "MUTATIONS = [('M1 sign', 'src/inline.py', 'compute(a, b)', 'compute(b, a)', 'tests/t.py::k')]",
)


def test_render_prints_a_tasks_md_that_reads_back_as_the_plan(tmp_path, monkeypatch, capsys):
    out = _render(tmp_path, monkeypatch, capsys, READBACK_PLAN)

    assert [s["name"] for s in herdtool.parse_tasks(out)] == ["T1", "I1", "I2", "I3"]
    assert [m["name"] for m in herdtool.parse_mutations(out)] == ["M1 sign"]


def test_render_refuses_a_tasks_md_the_builder_would_read_differently(tmp_path, monkeypatch, capsys):
    # Proposal mutation-name-parse-mismatch (project-mera #502): what the
    # builder parses from tasks.md is parsed back by the lead before dispatch.
    # Here a test file's body carries a line shaped like a mutation heading.
    plan = READBACK_PLAN.replace(
        '"new": "def test_x():\\n    pass\\n"',
        '"new": "- [ ] **M9** in `src/x.py`: replace\\n"',
    )
    assert plan != READBACK_PLAN

    with pytest.raises(SystemExit) as exc:
        _render(tmp_path, monkeypatch, capsys, plan)

    assert str(exc.value).startswith("render: the rendered tasks.md does not parse: AttributeError")
    assert capsys.readouterr().out == ""


def test_render_refuses_a_tasks_md_whose_drives_read_back_by_other_names(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(herdtool, "parse_mutations", lambda text: [{"name": "M1"}])

    with pytest.raises(SystemExit) as exc:
        _render(tmp_path, monkeypatch, capsys, READBACK_PLAN)

    assert str(exc.value) == (
        "render: the rendered tasks.md reads back with mutations ['M1'], the plan has ['M1 sign']"
    )
    assert capsys.readouterr().out == ""


def test_render_refuses_a_tasks_md_whose_steps_read_back_differently(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(herdtool, "parse_tasks", lambda text: [{"name": "T1"}])

    with pytest.raises(SystemExit) as exc:
        _render(tmp_path, monkeypatch, capsys, READBACK_PLAN)

    assert str(exc.value) == (
        "render: the rendered tasks.md reads back with steps ['T1'], the plan has ['T1', 'I1', 'I2', 'I3']"
    )
