import pathlib
import subprocess

import pytest


def git(*args: str, cwd: pathlib.Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


@pytest.fixture
def repo_with_worktree(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    """A main checkout with one commit, plus a linked worktree of it."""
    main = tmp_path / "main"
    main.mkdir()
    git("init", "-q", "-b", "main", cwd=main)
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init", cwd=main)
    wt = tmp_path / "wt"
    git("worktree", "add", "-q", "-b", "build", str(wt), cwd=main)
    return main, wt
