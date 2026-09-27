"""Match gate output by its counts, and list what a build changed.

usage: gates.py match "<expected line>" [<output file>]   (default: stdin)
       gates.py manifest <worktree> <base ref> [--allowed <file>]
       gates.py count "<text>" <path>... [--include GLOB] [--regex]
       gates.py fold start|done --issue N [--repo PATH]
       gates.py suite-ok --issue N [--ruling] [--repo PATH]

match   compares the last non-blank line of the output with the expected
        line: pytest and mypy lines by their counts (pytest's warnings and
        wall time are ignored), anything else literally. Exit 0 on MATCH.
manifest lists every file the worktree changed against <base ref>,
        untracked files included, coordination and evidence files excluded;
        with --allowed, exits 1 when a file is outside the allowed list.
count   prints how many lines contain <text> (literal unless --regex) in
        the files named, a directory counting only its *.py files (or
        --include) outside __pycache__. Zero is an answer: always exits 0,
        and it counts the same in bash and zsh, which grep -c does not.
fold    marks a fold of the issue's spec as started or done.
suite-ok says whether the full suite may run now: refused (exit 2) while a
        fold is pending, warned (exit 1) when it already ran for this
        build-state, allowed (exit 0, and recorded) otherwise. --ruling
        reopens it once for a ruling's reference mutation (accepted proposal
        2026-09-25-full-suite-rerun-after-fold).
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import pathlib
import re
import subprocess
import sys

PYTEST_COUNT = re.compile(r"(\d+) (passed|failed|skipped|deselected|errors?|xfailed|xpassed)\b")
MYPY_OK = re.compile(r"Success: no issues found in (\d+) source files?")
MYPY_FOUND = re.compile(r"Found (\d+) errors? in (\d+) files? \(checked (\d+) source files?\)")

# Root-level files the herd writes into a build worktree; never part of the change.
COORDINATION = ("BUILD-BRIEFING-*", "HANDOFF-*", "REVIEW-*", "CODEX-*", "ALLOWED-*", "RED-*", "GREEN-*",
                "FULLSUITE*", "MUTATION-LOG*", "SCRATCH-*", "RULING-*")


def parse(line: str) -> tuple[str, object]:
    line = line.strip()
    if m := MYPY_OK.search(line):
        return "mypy", {"errors": 0, "files": 0, "checked": int(m.group(1))}
    if m := MYPY_FOUND.search(line):
        return "mypy", {"errors": int(m.group(1)), "files": int(m.group(2)), "checked": int(m.group(3))}
    if line.startswith("Found "):  # ruff's "Found 1 error." is not a pytest count
        return "literal", line
    counts = {("error" if k.startswith("error") else k): int(n) for n, k in PYTEST_COUNT.findall(line)}
    if counts or "no tests ran" in line:
        return "pytest", counts
    return "literal", line


def compare(expected: str, actual: str) -> list[str]:
    (ek, ev), (ak, av) = parse(expected), parse(actual)
    if ek != ak:
        return [f"expected a {ek} line, got a {ak} line"]
    if ek == "literal":
        return [] if ev == av else [f"expected {ev!r}, got {av!r}"]
    keys = list(ev) + [k for k in av if k not in ev]
    return [f"{k}: expected {ev.get(k, 0)}, got {av.get(k, 0)}" for k in keys if ev.get(k, 0) != av.get(k, 0)]


def last_line(text: str) -> str:
    return next((ln for ln in reversed(text.splitlines()) if ln.strip()), "")


def git_lines(w: pathlib.Path, *args: str) -> list[str]:
    out = subprocess.run(["git", "-C", str(w), *args], capture_output=True, text=True, check=True).stdout
    return [ln for ln in out.splitlines() if ln]


def is_coordination(path: str) -> bool:
    return "/" not in path and any(fnmatch.fnmatch(path, p) for p in COORDINATION)


def manifest(w: pathlib.Path, base: str) -> list[tuple[str, str]]:
    tracked = [tuple(ln.split("\t", 1)) for ln in git_lines(w, "diff", "--name-status", "--no-renames", base)]
    untracked = [("A", p) for p in git_lines(w, "ls-files", "--others", "--exclude-standard")]
    return [(s, p) for s, p in tracked + untracked if not is_coordination(p)]


def allowed_entry(line: str) -> str:
    """The path an allowed-list line names: its first `backticked` token, else the bare line."""
    if m := re.search(r"`([^`]+)`", line):
        return m.group(1)
    return line.strip().lstrip("-").strip()


def outside_allowed(changed: list[tuple[str, str]], allowed_text: str) -> list[str]:
    """Changed paths the list does not allow; an entry ending in `/` allows everything under it."""
    allowed = [allowed_entry(ln) for ln in allowed_text.splitlines() if ln.strip()]
    return [p for _, p in changed if not any(p == a or (a.endswith("/") and p.startswith(a)) for a in allowed)]


def count(text: str, paths: list[pathlib.Path], include: str = "*.py", regex: bool = False) -> int:
    """Lines matching `text` across `paths`; a directory contributes its `include` files outside __pycache__."""
    files: list[pathlib.Path] = []
    for p in paths:
        if p.is_dir():
            files += sorted(f for f in p.rglob(include) if f.is_file() and "__pycache__" not in f.parts)
        else:
            files.append(p)
    pattern = re.compile(text) if regex else None
    total = 0
    for f in files:
        for line in f.read_text(errors="replace").splitlines():
            total += bool(pattern.search(line)) if pattern else text in line
    return total


def folds_path(repo: pathlib.Path) -> pathlib.Path:
    from herdtool import git_common_dir
    return git_common_dir(repo) / "herd" / "folds.json"


def fold_state(repo: pathlib.Path) -> dict:
    p = folds_path(repo)
    return json.loads(p.read_text()) if p.exists() else {}


def save_fold_state(repo: pathlib.Path, state: dict) -> None:
    p = folds_path(repo)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2))


def fold(repo: pathlib.Path, issue: str, what: str) -> None:
    state = fold_state(repo)
    entry = state.setdefault(issue, {"pending": False, "suite_runs": 0})
    entry["pending"] = what == "start"
    if what == "done":
        entry["suite_runs"] = 0  # a new build-state
    save_fold_state(repo, state)


def suite_ok(repo: pathlib.Path, issue: str, ruling: bool) -> tuple[int, str]:
    state = fold_state(repo)
    entry = state.setdefault(issue, {"pending": False, "suite_runs": 0})
    if entry["pending"]:
        return 2, f"a fold of #{issue} is pending: finish it (gates.py fold done) before the full suite"
    if entry["suite_runs"] >= 1 + int(ruling):
        return 1, (f"the full suite already ran for this build-state of #{issue}; run it again only after a fold "
                   f"or, once, for a ruling's reference mutation (--ruling)")
    entry["suite_runs"] += 1
    save_fold_state(repo, state)
    return 0, f"ok: full suite run {entry['suite_runs']} for this build-state of #{issue}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("match")
    m.add_argument("expected")
    m.add_argument("output", nargs="?")
    f = sub.add_parser("manifest")
    f.add_argument("worktree")
    f.add_argument("base")
    f.add_argument("--allowed")
    c = sub.add_parser("count")
    c.add_argument("text")
    c.add_argument("paths", nargs="+", type=pathlib.Path)
    c.add_argument("--include", default="*.py")
    c.add_argument("--regex", action="store_true")
    fo = sub.add_parser("fold")
    fo.add_argument("what", choices=("start", "done"))
    fo.add_argument("--issue", required=True)
    fo.add_argument("--repo", default=".")
    so = sub.add_parser("suite-ok")
    so.add_argument("--issue", required=True)
    so.add_argument("--ruling", action="store_true")
    so.add_argument("--repo", default=".")
    a = ap.parse_args(argv)
    if a.cmd == "fold":
        fold(pathlib.Path(a.repo), a.issue, a.what)
        print(f"fold of #{a.issue}: {a.what}")
        return 0
    if a.cmd == "suite-ok":
        rc, message = suite_ok(pathlib.Path(a.repo), a.issue, a.ruling)
        print(message)
        return rc
    if a.cmd == "count":
        print(count(a.text, a.paths, a.include, a.regex))
        return 0
    if a.cmd == "match":
        text = pathlib.Path(a.output).read_text() if a.output else sys.stdin.read()
        problems = compare(a.expected, last_line(text))
        print(("MISMATCH " if problems else "MATCH ") + a.expected)
        for p in problems:
            print("  " + p)
        return 1 if problems else 0
    changed = manifest(pathlib.Path(a.worktree), a.base)
    for status, path in changed:
        print(f"{status} {path}")
    outside = outside_allowed(changed, pathlib.Path(a.allowed).read_text()) if a.allowed else []
    for p in outside:
        print(f"OUTSIDE ALLOWED: {p}")
    return 1 if outside else 0


if __name__ == "__main__":
    sys.exit(main())
