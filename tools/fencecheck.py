"""Check a build worktree against the byte-exact fences of its tasks.md.

usage: fencecheck.py <tasks.md> <worktree>

Prints one line per step that deviates (step, file, why) and exits 1, or
prints `FENCES OK (<n> steps)` and exits 0. Exits 2 when tasks.md has no steps.
Needs only tasks.md, not the lead's plan module, so any reviewer can run it.

A rendered fence always ends with a newline, even when the text it carries
did not. forms() lists the only sources a body can have, exact first; a
body whose last line is blank has one source, so a missing blank line is
always a deviation. For a replace, the form the replacement is found in
decides the form of the replaced text too.
"""
from __future__ import annotations

import pathlib
import sys

from herdtool import forms, parse_tasks, step_problem

OK = "FENCES OK"  # the start of the one success line; the reviewer prompt reads it from here


def resolve(w: pathlib.Path, step: dict) -> dict:
    """The step with each fence body replaced by the source form found in the file."""
    if step["kind"] not in ("replace", "insert_before"):
        return step
    path = w / step["path"]
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    old, new = step["old"], step["new"]
    if step["kind"] == "insert_before":
        pairs = [(n, o) for n in forms(new) for o in forms(old)]
        n, o = next(((n, o) for n, o in pairs if text.count(n + o) == 1), pairs[0])
        return {**step, "new": n, "old": o}
    n = next((n for n in forms(new) if n in text), new)
    if n == new or old is None:
        return {**step, "new": n}
    return {**step, "new": n, "old": forms(old)[-1]}


def check(tasks_text: str, w: pathlib.Path) -> list[str]:
    problems = []
    for step in parse_tasks(tasks_text):
        why = step_problem(w, resolve(w, step))
        if why:
            problems.append(f"{step['name']} `{step['path']}`: {why}")
    return problems


def main(argv: list[str] | None = None) -> int:
    tasks_path, worktree = argv if argv is not None else sys.argv[1:3]
    text = pathlib.Path(tasks_path).read_text(encoding="utf-8")
    steps = parse_tasks(text)
    if not steps:
        print(f"no T/I steps found in {tasks_path}")
        return 2
    problems = check(text, pathlib.Path(worktree))
    for p in problems:
        print(p)
    if not problems:
        print(f"{OK} ({len(steps)} steps)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
