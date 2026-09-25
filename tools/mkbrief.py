"""Write BUILD-BRIEFING-<id>.md and CODEX-PROMPT-<id>.md into a build worktree.

usage: mkbrief.py <id> <worktree> <branch> <base-desc> <change-name> <gates-file> <allowed-files-file>
                  [--lead-pane <pane>] [--reviewer <agent name>]

The lead pane defaults to $HERDR_PANE_ID (run this from the lead's pane); the
reviewer defaults to the roster's build reviewer, codex_review.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess

from herdtool import find_python, main_checkout

FENCECHECK = pathlib.Path(__file__).resolve().parent / "fencecheck.py"
GATES = pathlib.Path(__file__).resolve().parent / "gates.py"


def resolve_lead_pane(explicit: str | None) -> str:
    pane = explicit or os.environ.get("HERDR_PANE_ID")
    if not pane:
        raise SystemExit("no lead pane: pass --lead-pane or run from the lead's pane so HERDR_PANE_ID is set")
    return pane


def base_sha(worktree: pathlib.Path, base: str) -> str:
    r = subprocess.run(["git", "-C", str(worktree), "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"base is not a git ref in {worktree}: {base}")
    return r.stdout.strip()


def has_xdist(python: str) -> bool:
    return subprocess.run([python, "-c", "import xdist"], capture_output=True).returncode == 0


def build_briefing(*, id: str, worktree: pathlib.Path, branch: str, base: str, change: str, gates: str,
                   allowed: str, python: str, lead_pane: str, reviewer: str, has_xdist: bool) -> str:
    main = main_checkout(worktree)
    sha = base_sha(worktree, base)
    xdist = ("`pytest-xdist` is installed; the gates in tasks.md say whether to use it."
             if has_xdist else "`pytest-xdist` is NOT installed. Do not install anything.")
    return f"""# BUILD BRIEFING — #{id} ({change})

You are the BUILDER. Work ONLY in this worktree:

    {worktree}

Branch `{branch}`, cut from {base} ({sha}). Do NOT touch `{main}`
(the main checkout) or any other worktree. Never `git commit`, `git push`,
`git checkout <file>`, `git stash`, or `git reset`. To undo an edit, re-edit the file.

## Environment

- Python: `{python}` — every python/pytest/mypy command is run from the worktree
  root and prefixed `PYTHONPATH=src`, e.g.
  `PYTHONPATH=src {python} -m pytest <touched test file> -q --no-header`
- ruff is on PATH: `ruff check <paths>`.
- {xdist}
- Write temporary files into the worktree root, never `/tmp`, and name them `SCRATCH-<anything>`;
  the reviewer's change list ignores those and flags any other stray file.

## Measured gates (your run's COUNTS must match)

Check each with `python3 {GATES} match "<expected line>" <output file>`: it prints
MATCH, or the counts that differ. pytest's warnings and wall time do not count.

{gates}
## The spec — read in this order

1. `openspec/changes/{change}/proposal.md`
2. `openspec/changes/{change}/design.md` (if present)
3. `openspec/changes/{change}/specs/` (the delta)
4. `openspec/changes/{change}/tasks.md` — THIS IS YOUR CHECKLIST.

The fences in tasks.md are BYTE-EXACT text taken from a verified reference
build. Write them verbatim: do not re-wrap, rename, re-order, add comments,
or "improve" anything. The lead will diff your build against the reference
byte for byte.

## Rules

- Tests first. Do section 1, run the touched tests, SEE THEM FAIL (RED), and
  save the tail. Only then do section 2 and reach GREEN.
- Anchors are quoted text. If an anchor does not match exactly once, STOP and
  send BLOCKED — do not guess.
- Never loosen, delete, or skip an assertion to make a test pass.
- Allowed files (edit nothing else):
{allowed}
- Mutation drives (section 3): one at a time; make the edit, run the named
  killer test, record the FAILED line, RESTORE the file, confirm the killer
  test passes again. A mutation that SURVIVES is a BLOCKED, not a skip.

## Handoff — write `HANDOFF-{id}.md` in the worktree root

1. Self-review, 10 lines or fewer: what changed, biggest risk, where to look first.
2. RED tail and GREEN tail (literal).
3. Full-suite tail, VERBATIM (you run the full suite exactly once).
4. ruff and mypy last lines; every grep gate's output; the fence check's output —
   `python3 {FENCECHECK} openspec/changes/{change}/tasks.md .` must print
   `FENCES OK (<n> steps)`; any other line is a deviation to fix before review.
5. `git diff --stat`.
6. Sibling sweep result, if tasks.md asks for one.
7. Mutation log: name, KILLED/SURVIVED, the observed FAILED line.
8. Every assertion in this handoff NOT backed by a tool result you ran.
9. Round log: one line per review round (findings, what you changed).

## Coordination (run these literally, from the worktree root)

Review round N (N = 1, 2): make the per-round prompt, then send it.

    sed -e "s/ROUND_N/N/g" -e "s/RULINGS_PLACEHOLDER/none/" CODEX-PROMPT-{id}.md > CODEX-PROMPT-{id}-round-N.md
    herdr agent prompt {reviewer} "$(cat CODEX-PROMPT-{id}-round-N.md)" --wait --timeout 540000

(Replace the N in the sed and the file names with the round number. If the
lead gave you a ruling, put its sentence in place of `none`.) If the command
exits with "timed out waiting for agent status", the reviewer is STILL
WORKING: run `herdr agent wait {reviewer} --timeout 540000` and repeat until
it returns. Then read `REVIEW-{id}-round-N.md`. Fix every CONFIRMED finding,
re-run ALL gates, update the handoff, send the next round. Cap: 2 rounds.

When the review file ends with `REVIEW CLEAN`:

    herdr agent prompt {lead_pane} "DONE: build for {id} — reviewer clean after N rounds — handoff at {worktree}/HANDOFF-{id}.md"

If you are stuck, an anchor does not match, a mutation survives, or you hit
the round cap with open findings:

    herdr agent prompt {lead_pane} "BLOCKED: {id} — <one line: what and where>"

Contact the lead for nothing else.
"""


def build_reviewer_prompt(*, id: str, worktree: pathlib.Path, branch: str, base: str, change: str, python: str,
                          lead_pane: str, **_: object) -> str:
    w = worktree
    sha = base_sha(worktree, base)
    return f"""You are the REVIEWER for herd build #{id}, review round ROUND_N. Do NOT edit any file except your review file. Do NOT commit.

Worktree (the build under review): {w}
Branch {branch}, base {base} at {sha} (the build is uncommitted). List what changed with `python3 {GATES} manifest {w} {sha} --allowed {w}/ALLOWED-{id}.txt` — it includes untracked files, and every OUTSIDE ALLOWED line is a finding. Read the changes with `git -C {w} diff {sha}` plus each untracked file the manifest lists.
Spec: {w}/openspec/changes/{change}/ (proposal.md, design.md if present, specs/, tasks.md). The spec directory itself is part of the change, not a finding.
Handoff: {w}/HANDOFF-{id}.md — it carries the full-suite tail verbatim; do NOT re-run the full suite unless that tail is missing or contradicts the gate in tasks.md section 0.
Lead rulings in force: RULINGS_PLACEHOLDER

Do this:
1. Read the spec, then the handoff, then the diff.
2. Run the TOUCHED test files yourself from the worktree root: `cd {w} && PYTHONPATH=src {python} -m pytest <touched test files> -q --no-header`, plus the ruff, mypy and grep gates in tasks.md. Record the commands and their last lines.
3. Check the build against tasks.md: the fences are byte-exact reference text, so run `python3 {FENCECHECK} {w}/openspec/changes/{change}/tasks.md {w}` — every line it prints other than `FENCES OK` is a finding (step, file, why); do not re-check fences by eye. Any edit to a file outside the allowed list is a finding; BUILD-BRIEFING/HANDOFF/REVIEW/CODEX files are coordination files, not findings.
4. Report ONLY CONFIRMED defects — ones you reproduced or can show at file:line — each with an exact fix. Do not propose work the proposal's Non-goals exclude, new subsystems, persistence, or refactors.

Write {w}/REVIEW-{id}-round-ROUND_N.md: what you ran (commands + last lines), what you checked, then numbered findings. End the file with exactly one sentinel line: `FINDINGS: <n>` or `REVIEW CLEAN`. A clean review still lists what it ran.
Reply in chat with only the path and the sentinel. If and only if the sentinel is REVIEW CLEAN, also run: herdr agent prompt {lead_pane} "REVIEW CLEAN for {id} after ROUND_N rounds"
"""  # noqa: E501


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("id", "worktree", "branch", "base", "change", "gates_file", "allowed_file"):
        ap.add_argument(name)
    ap.add_argument("--lead-pane")
    ap.add_argument("--reviewer", default="codex_review")
    a = ap.parse_args(argv)
    w = pathlib.Path(a.worktree)
    python = find_python(w)
    args = dict(id=a.id, worktree=w, branch=a.branch, base=a.base, change=a.change,
                gates=pathlib.Path(a.gates_file).read_text(),
                allowed=pathlib.Path(a.allowed_file).read_text().rstrip(),
                python=python, lead_pane=resolve_lead_pane(a.lead_pane), reviewer=a.reviewer,
                has_xdist=has_xdist(python))
    (w / f"ALLOWED-{a.id}.txt").write_text(args["allowed"] + f"\n  - `openspec/changes/{a.change}/`\n")
    (w / f"BUILD-BRIEFING-{a.id}.md").write_text(build_briefing(**args))
    (w / f"CODEX-PROMPT-{a.id}.md").write_text(build_reviewer_prompt(**args))
    print("wrote briefing + codex prompt in", w)


if __name__ == "__main__":
    main()
