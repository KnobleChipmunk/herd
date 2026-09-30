"""Apply a build's STEPS-<id>.json to a worktree: the one step applier.

usage: apply_steps.py <steps.json> <worktree> [<name>|T|I ...] [--path <file>]

With no selector every step is applied, in file order. A step name (T3, I12)
selects that step; a bare T or I selects its section; --path keeps only the
steps for one file (re-applying an implementation file after a lead fold).
Each step is checked before it writes: a `replace` or `insert_before` anchor
must occur exactly once, and a `new_file` must not exist. The first failing
step stops the run with its name and the reason; the steps before it stay
applied and are listed on stdout. Exit 0 applied, 1 a step failed, 2 bad
arguments.

The kinds are herdtool's (`herdtool.apply_step` does the writing), so the
lead's pre-execution and the builder apply the same bytes the same way
(proposal manual-reference-mutation-recovery).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from herdtool import apply_step


def problem(w: pathlib.Path, step: dict) -> str | None:
    """Why this step cannot be applied to the tree as it stands, or None."""
    path = w / step["path"]
    kind = step["kind"]
    if kind == "new_file":
        return "file already exists" if path.exists() else None
    if not path.exists():
        return "file does not exist"
    if kind in ("replace", "insert_before"):
        count = path.read_text(encoding="utf-8").count(step["old"])
        return None if count == 1 else f"anchor occurs {count} times, expected 1"
    if kind == "append":
        text = path.read_text(encoding="utf-8")
        return None if text.endswith("\n") and not text.endswith("\n\n") else "file end is not a single newline"
    if kind == "whole_file":
        return None
    return f"unknown kind {kind!r}"


def select(steps: list[dict], names: list[str], path: str | None) -> list[dict]:
    known = {s["name"] for s in steps}
    for name in names:
        if name not in ("T", "I") and name not in known:
            raise SystemExit(f"unknown step {name}")
    chosen = [s for s in steps
              if not names or s["name"] in names or s["name"][:1] in names]
    return [s for s in chosen if path is None or s["path"] == path]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("steps")
    ap.add_argument("worktree")
    ap.add_argument("names", nargs="*")
    ap.add_argument("--path")
    a = ap.parse_args(argv)
    w = pathlib.Path(a.worktree)
    steps = json.loads(pathlib.Path(a.steps).read_text(encoding="utf-8"))
    try:
        chosen = select(steps, a.names, a.path)
    except SystemExit as e:
        print(e, file=sys.stderr)
        return 2
    for done, step in enumerate(chosen):
        why = problem(w, step)
        if why is not None:
            print(f"{step['name']} {step['kind']} {step['path']}: {why}", file=sys.stderr)
            print(f"stopped after {done} of {len(chosen)} steps", file=sys.stderr)
            return 1
        apply_step(w, step)
        print(f"applied {step['name']} {step['kind']} {step['path']}")
    print(f"applied {len(chosen)} steps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
