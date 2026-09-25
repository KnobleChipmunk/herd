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
import shutil
import sys

TOOLS = ("git", "gh", "herdr", "pi", "codex", "claude", "openspec")


def need(spec: str) -> tuple[str, str]:
    issue, sep, var = spec.partition(":")
    if not sep or not issue or not var:
        raise SystemExit(f"--need takes ISSUE:VARIABLE, got {spec!r}")
    return issue, var


def checks(needs: list[tuple[str, str]]) -> list[tuple[bool, str]]:
    out = [(os.environ.get("HERDR_ENV") == "1", "inside Herdr (HERDR_ENV=1)")]
    out += [(shutil.which(t) is not None, f"{t} on PATH") for t in TOOLS]
    out += [(bool(os.environ.get(var)), f"{var} for #{issue}") for issue, var in needs]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--need", action="append", default=[])
    a = ap.parse_args(argv)
    results = checks([need(s) for s in a.need])
    for ok, label in results:
        print(f"{'ok  ' if ok else 'MISSING'} {label}")
    return 0 if all(ok for ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
