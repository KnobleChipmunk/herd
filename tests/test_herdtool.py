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
