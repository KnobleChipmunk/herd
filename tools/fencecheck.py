"""Check a build worktree against the byte-exact fences of its tasks.md.

usage: python3 -B fencecheck.py <tasks.md> <worktree> [--base <pinned-base-sha>]

With --base, read git blobs and project fences in memory without writing or
executing plan code. Report anchor counts and final reference parity. Prose-only
replacement instructions need quoted old text for projection.

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

import argparse
import pathlib
import subprocess
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


def project(tasks_text: str, base_files: dict[str, str], w: pathlib.Path) -> tuple[list[str], bool]:
    """Project parsed fences onto base text in memory and compare the reference.

    The reference selects rendered forms as in check(); if a later step has
    replaced an inline result, the unique base anchor selects its paired form.
    Whole-file and append bodies retain their exact rendered bytes.
    """
    files = dict(base_files)
    lines, failed = [], False
    steps = parse_tasks(tasks_text)
    for original in steps:
        path, kind = original["path"], original["kind"]
        label = f"{original['name']} `{path}`"
        current = files.get(path)
        step = resolve(w, original)
        reason = None
        if kind == "new_file":
            if current is not None:
                reason = "file already exists in base"
            else:
                files[path] = step["new"]
        elif current is None:
            reason = "file missing from base"
        elif kind == "whole_file":
            files[path] = step["new"]
        elif kind == "append":
            if not current.endswith("\n") or current.endswith("\n\n"):
                reason = "file end not a single newline"
            else:
                files[path] = current + step["new"]
        elif step["old"] is None:
            reason = "quoted old text required"
        else:
            old, new = step["old"], step["new"]
            count = current.count(old)
            if count == 0:
                # A later step may remove the reference occurrence used by resolve.
                for index, form in enumerate(forms(original["old"])):
                    if current.count(form):
                        old = form
                        if kind == "replace":
                            new_forms = forms(original["new"])
                            new = new_forms[min(index, len(new_forms) - 1)]
                        count = current.count(old)
                        break
            lines.append(f"{label}: anchors={count}")
            if count != 1:
                reason = "anchor must occur exactly once"
            else:
                files[path] = current.replace(old, new + old if kind == "insert_before" else new, 1)
        if kind in ("new_file", "whole_file", "append"):
            lines.append(f"{label}: anchors=n/a ({kind})")
        if reason:
            lines.append(f"{label}: {reason}")
            failed = True
    for path in sorted({step["path"] for step in steps}):
        reference = w / path
        if not reference.is_file():
            status = "reference missing"
        else:
            status = "OK" if files.get(path) == reference.read_text(encoding="utf-8") else "DIFFERS"
        lines.append(f"PARITY `{path}`: {status}")
        failed |= status != "OK"
    return lines, failed


def project_base(tasks_text: str, w: pathlib.Path, base: str) -> int:
    ref = subprocess.run(["git", "-C", str(w), "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"],
                         capture_output=True, text=True)
    if ref.returncode:
        print(f"invalid base: {base}")
        return 2
    files = {}
    for path in {step["path"] for step in parse_tasks(tasks_text)}:
        blob = subprocess.run(["git", "-C", str(w), "show", f"{ref.stdout.strip()}:{path}"],
                              capture_output=True, text=True, encoding="utf-8")
        if blob.returncode == 0:
            files[path] = blob.stdout
    lines, failed = project(tasks_text, files, w)
    for line in lines:
        print(line)
    if not failed:
        print(f"PROJECTION OK ({len(parse_tasks(tasks_text))} steps)")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tasks_path")
    parser.add_argument("worktree")
    parser.add_argument("--base")
    args = parser.parse_args(argv)
    tasks_path, worktree = args.tasks_path, args.worktree
    text = pathlib.Path(tasks_path).read_text(encoding="utf-8")
    steps = parse_tasks(text)
    if not steps:
        print(f"no T/I steps found in {tasks_path}")
        return 2
    if args.base is not None:
        return project_base(text, pathlib.Path(worktree), args.base)
    problems = check(text, pathlib.Path(worktree))
    for p in problems:
        print(p)
    if not problems:
        print(f"{OK} ({len(steps)} steps)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
