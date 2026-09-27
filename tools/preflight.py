"""Check a machine is ready for an unattended run, before the operator goes to bed.

usage: preflight.py [--need ISSUE:VARIABLE ...]

Checks that the run is inside Herdr, that every tool the herd calls is on
PATH, and that each environment variable an issue needs is set and not
empty. Variables are reported as set or missing, never by value. Exits 1
when anything is missing, so the question goes to the operator now rather
than at 3 a.m.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import sys

import bindings

TOOLS = ("git", "gh", "herdr", "pi", "codex", "claude", "openspec")


def need(spec: str) -> tuple[str, str]:
    issue, sep, var = spec.partition(":")
    if not sep or not issue or not var:
        raise SystemExit(f"--need takes ISSUE:VARIABLE, got {spec!r}")
    return issue, var


def tools_for(path: pathlib.Path | None, roles: tuple = bindings.LOOP_ROLES) -> tuple[str, ...]:
    """The tools the selected roles' bindings need (#38); the fixed list when the user has no bindings file.
    An explicitly named file that does not exist is an error, not a fallback."""
    if path is not None and not path.exists():
        raise bindings.BindingsError(f"no bindings file at {path}")
    path = path or bindings.user_path()
    return tuple(bindings.required_tools(bindings.load(path), roles)) if path.exists() else TOOLS


def checks(needs: list[tuple[str, str]], tools: tuple[str, ...] = TOOLS) -> list[tuple[bool, str]]:
    out = [(os.environ.get("HERDR_ENV") == "1", "inside Herdr (HERDR_ENV=1)")]
    out += [(shutil.which(t) is not None, f"{t} on PATH") for t in tools]
    out += [(bool(os.environ.get(var)), f"{var} for #{issue}") for issue, var in needs]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--need", action="append", default=[])
    ap.add_argument("--bindings", help="bindings file (default: the user's, when it exists)")
    ap.add_argument("--roles", default=",".join(bindings.LOOP_ROLES), help="the roles this run uses")
    a = ap.parse_args(argv)
    try:
        tools = tools_for(pathlib.Path(a.bindings) if a.bindings else None, tuple(a.roles.split(",")))
    except bindings.BindingsError as exc:
        print(f"MISSING valid bindings: {exc}")
        return 1
    results = checks([need(s) for s in a.need], tools)
    for ok, label in results:
        print(f"{'ok  ' if ok else 'MISSING'} {label}")
    return 0 if all(ok for ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
