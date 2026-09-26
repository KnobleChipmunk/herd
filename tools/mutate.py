"""Drive the mutations in a tasks.md against a build worktree.

usage: mutate.py <tasks.md> <worktree> [--only M1,M3] [--scratch]

Prints one line per mutation (KILLED with the failing test, SURVIVED, or
VOID when its anchor does not occur exactly once) and a TREE CHANGED line if
the worktree's git status differs after the drives. Exits 1 on any of those,
2 when tasks.md has no mutations. --scratch drives a copy of the worktree, so
a reviewer can re-drive mutations without touching the build. Refuses to run
while a pytest process is working in the worktree.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import sys
import tempfile

from herdtool import find_python, forms, parse_mutations, run_mutations


def is_pytest(argv: list[str]) -> bool:
    """Whether a command line runs pytest: `pytest ...`, `.../pytest ...`, or
    `python -m pytest ...`. An argument that only mentions pytest, such as a
    reviewer prompt passed to `herdr agent prompt`, is not pytest."""
    names = [pathlib.PurePath(arg).name for arg in argv]
    if any(name in ("pytest", "py.test") for name in names):
        return True
    return any(a == "-m" and b == "pytest" for a, b in zip(argv, argv[1:]))


def pytest_running_in(w: pathlib.Path) -> bool:
    w = w.resolve()
    for proc in pathlib.Path("/proc").glob("[0-9]*"):
        if proc.name == str(os.getpid()):
            continue
        try:
            cwd = pathlib.Path(os.readlink(proc / "cwd")).resolve()
            argv = (proc / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        args = [arg.decode(errors="replace") for arg in argv if arg]
        if (cwd == w or w in cwd.parents) and is_pytest(args):
            return True
    return False


def resolve(w: pathlib.Path, mut: dict) -> tuple[str, str, str, str, str]:
    """The mutation with old/new in the newline form whose anchor occurs exactly once."""
    text = (w / mut["path"]).read_text(encoding="utf-8")
    olds = forms(mut["old"])
    old = next((o for o in olds if text.count(o) == 1), olds[-1])
    new = mut["new"] if old == mut["old"] else forms(mut["new"])[-1]
    return mut["name"], mut["path"], old, new, mut["test"]


def drive(tasks_text: str, w: pathlib.Path, only: set[str] | None = None,
          scratch: bool = False) -> tuple[list[str], int]:
    if pytest_running_in(w):
        raise SystemExit(f"pytest is running in {w}; wait for it before driving mutations")
    muts = [m for m in parse_mutations(tasks_text) if not only or m["name"] in only]
    py = find_python(w)
    if not scratch:
        return run_mutations(w, [resolve(w, m) for m in muts], py)
    with tempfile.TemporaryDirectory(prefix="herd-mutate-") as tmp:
        copy = pathlib.Path(tmp) / w.name
        shutil.copytree(w, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        return run_mutations(copy, [resolve(copy, m) for m in muts], py)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("tasks")
    ap.add_argument("worktree")
    ap.add_argument("--only", help="comma-separated mutation names")
    ap.add_argument("--scratch", action="store_true")
    a = ap.parse_args(argv)
    text = pathlib.Path(a.tasks).read_text(encoding="utf-8")
    if not parse_mutations(text):
        print(f"no mutations found in {a.tasks}")
        return 2
    only = set(a.only.split(",")) if a.only else None
    lines, failures = drive(text, pathlib.Path(a.worktree), only=only, scratch=a.scratch)
    for ln in lines:
        print(ln)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
