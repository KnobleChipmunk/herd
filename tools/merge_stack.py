"""Merge a run's PRs in order, pull main, and remove what the run created.

usage: merge_stack.py [--repo PATH] [--log RUN-LOG] [--apply]

The operator runs this after reviewing the PRs; without --apply it only says
what it would do. It reads the latest run in the run log and:

1. merges each PR the run opened, in the order it was opened, with a true
   merge (`--merge --delete-branch`), stopping at the first PR that does not
   target main, is closed, or fails to merge: later PRs are stacked on it;
2. pulls main in the main checkout; an untracked file in the way is removed
   only when it is byte-identical to origin/main, otherwise it stops;
3. for each issue whose PR merged, removes the worktrees and branches the log
   says the run created, never forcing a worktree with uncommitted work;
4. when all of that succeeded, starts the librarian (Hermes, herd-librarian)
   in the background, once per run, unless --no-librarian.

Every step skips what is already done, so a crash half-way is fixed by
running it again.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys

import runlog
from herdtool import main_checkout

GIT_AUTH = ["-c", "credential.helper=!gh auth git-credential"]


def env_without_gh_token() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k != "GH_TOKEN"}


def gh_runner(repo: pathlib.Path):
    def gh(args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(["gh", *args], cwd=repo, capture_output=True, text=True, env=env_without_gh_token())
    return gh


def git(repo: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *GIT_AUTH, "-C", str(repo), *args], capture_output=True, text=True,
                          env=env_without_gh_token())


def last_line(r: subprocess.CompletedProcess) -> str:
    lines = (r.stderr or r.stdout).strip().splitlines()
    return lines[-1] if lines else f"exit {r.returncode}"


def merge_prs(events: list[dict], gh, apply: bool) -> tuple[list[str], set[str], bool]:
    lines, merged, seen = [], set(), set()
    for e in events:
        if e["kind"] != "pr-opened" or e["pr"] in seen:
            continue
        seen.add(e["pr"])
        pr, issue = e["pr"], e.get("issue", "?")
        label = f"PR #{pr} (#{issue})"
        view = json.loads(gh(["pr", "view", pr, "--json", "state,baseRefName"]).stdout)
        if view["baseRefName"] != "main":
            lines.append(f"STOP {label}: targets {view['baseRefName']}, not main")
            return lines, merged, False
        if view["state"] == "MERGED":
            lines.append(f"already merged {label}")
        elif view["state"] != "OPEN":
            lines.append(f"STOP {label}: {view['state']}")
            return lines, merged, False
        elif not apply:
            lines.append(f"would merge {label}")
        else:
            r = gh(["pr", "merge", pr, "--merge", "--delete-branch"])
            state = json.loads(gh(["pr", "view", pr, "--json", "state,baseRefName"]).stdout)["state"]
            if r.returncode or state != "MERGED":
                lines.append(f"STOP {label}: {last_line(r)}; later PRs are stacked on it")
                return lines, merged, False
            lines.append(f"merged {label}")
        merged.add(issue)
    return lines, merged, True


def blocking_untracked(pull_error: str) -> list[str]:
    lines = pull_error.splitlines()
    marker = next((i for i, ln in enumerate(lines) if "untracked working tree files would be overwritten" in ln), None)
    if marker is None:
        return []
    return [ln.strip() for ln in lines[marker + 1:] if ln.startswith(("\t", "    ")) and ln.strip()]


def pull_main(main: pathlib.Path, apply: bool) -> tuple[list[str], bool]:
    branch = git(main, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if branch != "main":
        return [f"STOP the main checkout is on {branch}, not main"], False
    if not apply:
        return ["would pull main"], True
    lines = []
    git(main, "fetch", "-q", "origin")
    for _ in range(2):
        r = git(main, "pull", "-q", "--ff-only", "origin", "main")
        if r.returncode == 0:
            return lines + ["pulled main"], True
        blocking = blocking_untracked(r.stderr)
        if not blocking:
            return lines + [f"STOP pull failed: {last_line(r)}"], False
        for rel in blocking:
            merged = subprocess.run(["git", "-C", str(main), "show", f"origin/main:{rel}"], capture_output=True)
            if merged.returncode or (main / rel).read_bytes() != merged.stdout:
                return lines + [f"STOP untracked {rel} differs from origin/main; compare and move it first"], False
        for rel in blocking:
            (main / rel).unlink()
            lines.append(f"removed untracked {rel} (identical to origin/main)")
    return lines + ["STOP pull still blocked after removing identical copies"], False


def cleanup(main: pathlib.Path, events: list[dict], merged: set[str], apply: bool) -> list[str]:
    lines = []
    existing = set(git(main, "branch", "--format=%(refname:short)").stdout.split())
    for e in events:
        if e["kind"] not in ("worktree-created", "scratch-created"):
            continue
        path, branch, issue = pathlib.Path(e["worktree"]), e.get("branch"), e.get("issue", "?")
        scratch = e["kind"] == "scratch-created"
        if issue not in merged:
            lines.append(f"kept worktree {path} (#{issue} not merged)")
            continue
        if not path.exists():
            lines.append(f"already gone {path}")
        elif not apply:
            lines.append(f"would remove worktree {path}")
        else:
            r = git(main, "worktree", "remove", str(path))
            if r.returncode:
                lines.append(f"KEPT worktree {path}: {last_line(r)}")
                continue
            lines.append(f"removed worktree {path}")
        if not branch:
            continue
        kind = "scratch branch" if scratch else "branch"
        if branch not in existing:
            lines.append(f"already gone {branch}")
        elif not apply:
            lines.append(f"would delete {kind} {branch}")
        else:
            r = git(main, "branch", "-D" if scratch else "-d", branch)
            lines.append(f"deleted {kind} {branch}" if r.returncode == 0 else f"KEPT {kind} {branch}: {last_line(r)}")
    return lines


def librarian_command(main: pathlib.Path) -> list[str]:
    return ["hermes", "-s", "herd-librarian", "-z", f"Run the herd-librarian skill for the repo {main}."]


def launch(cmd: list[str], log: pathlib.Path) -> int:
    """Start `cmd` detached, output to `log`; it outlives this process. Returns its pid."""
    with log.open("w") as out:
        proc = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                start_new_session=True)
    return proc.pid


def start_librarian(main: pathlib.Path, events: list[dict], log_file: pathlib.Path, apply: bool) -> str:
    if not apply:
        return "would start the librarian (Hermes herd-librarian)"
    if any(e["kind"] == "note" and e.get("text", "").startswith(("librarian started", "librarian:"))
           for e in events):
        return "librarian already started for this run; not starting it again"
    cmd = librarian_command(main)
    if not shutil.which("hermes"):
        return "librarian NOT started: hermes is not on PATH; run: " + shlex.join(cmd)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    report = log_file.parent / f"librarian-{stamp}.log"
    pid = launch(cmd, report)
    runlog.append(main, "note", {"text": f"librarian started (log: {report})"}, path=log_file)
    return f"librarian started in the background (pid {pid}); its report: {report}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--log")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--no-librarian", action="store_true")
    a = ap.parse_args(argv)
    repo = pathlib.Path(a.repo)
    log_file = pathlib.Path(a.log) if a.log else runlog.log_path(repo)
    events = runlog.latest(runlog.read_file(log_file))
    main_dir = main_checkout(repo)
    out = [] if a.apply else ["DRY RUN (pass --apply to act)"]
    merge_lines, merged, merges_ok = merge_prs(events, gh_runner(main_dir), a.apply)
    out += merge_lines
    pull_lines, pulled = pull_main(main_dir, a.apply)
    out += pull_lines
    if pulled:
        out += cleanup(main_dir, events, merged, a.apply)
    out.append("next: archive the merged openspec changes on a chore/ branch (the lead's step)")
    if merges_ok and pulled and not a.no_librarian:
        out.append(start_librarian(main_dir, events, log_file, a.apply))
    for ln in out:
        print(ln)
    return 0 if merges_ok and pulled else 1


if __name__ == "__main__":
    sys.exit(main())
