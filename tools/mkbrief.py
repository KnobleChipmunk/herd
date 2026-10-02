"""Write BUILD-BRIEFING-<id>.md and CODEX-PROMPT-<id>.md into a build worktree.

usage: mkbrief.py <id> <worktree> <branch> <base-desc> <change-name> <allowed-files-file>
                  [--lead-pane <pane>] [--reviewer <agent name>] [--builder <agent name>]

The lead pane defaults to $HERDR_PANE_ID (run this from the lead's pane); the
reviewer defaults to the roster's build reviewer, codex_review, and the builder
to its builder, codex_build (pass --builder pi_build for the pi fallback).
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess

import fencecheck
import gates
from herdtool import find_python, main_checkout

FENCECHECK = pathlib.Path(__file__).resolve().parent / "fencecheck.py"
APPLY_STEPS = pathlib.Path(__file__).resolve().parent / "apply_steps.py"
GATES = pathlib.Path(__file__).resolve().parent / "gates.py"
MUTATE = pathlib.Path(__file__).resolve().parent / "mutate.py"
RUNLOG = pathlib.Path(__file__).resolve().parent / "runlog.py"
DISPATCH = pathlib.Path(__file__).resolve().parent / "dispatch.py"


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


def task_gates(worktree: pathlib.Path, change: str) -> str:
    path = worktree / "openspec" / "changes" / change / "tasks.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"cannot read {path}: {exc}") from exc
    blocks: list[list[str]] = []
    current: list[str] | None = None
    fence = ""
    for line in text.splitlines(keepends=True):
        if fence:
            if current is not None:
                current.append(line)
            if re.fullmatch(r" {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t]*\n?", line):
                fence = ""
            continue
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            fence = marker.group(1)
            if current is not None:
                current.append(line)
        elif re.fullmatch(r" {0,3}## 0\. Gates[ \t]*\n?", line):
            current = []
            blocks.append(current)
        elif re.match(r"^ {0,3}##(?:\s|$)", line):
            current = None
        elif current is not None:
            current.append(line)
    if len(blocks) != 1 or not "".join(blocks[0]).strip():
        raise SystemExit(f"{path} must contain exactly one nonempty '## 0. Gates' section")
    lines = blocks[0]
    while not lines[0].strip():
        lines.pop(0)
    while not lines[-1].strip():
        lines.pop()
    gates = "".join(lines).rstrip("\n") + "\n"
    # A baseline derived from the after count (less the new tests) reads like
    # a run and is not one (#482); the builder compares against it.
    if re.search(r"\(derived\b", gates, re.I) or not re.search(r"full[- ]suite(?:[^\n]*\n[ \t]+)*?[^\n]*\(measured\b", gates, re.I):
        raise SystemExit(
            f"{path}: the full-suite baseline in '## 0. Gates' must be run at the base and "
            "marked in its bullet as '(measured, <seconds> s)', never derived from the after count"
        )
    return gates


def cache_env(id: str) -> str:
    """The cache locations for one build's ruff and mypy: the build worktree
    rejects cache writes, so every generated command carries them (proposal
    readonly-worktree-cache-dir)."""
    return f"RUFF_CACHE_DIR=/tmp/herd-{id}-ruff MYPY_CACHE_DIR=/tmp/herd-{id}-mypy"


def build_briefing(*, id: str, worktree: pathlib.Path, branch: str, base: str, change: str,
                   allowed: str, python: str, lead_pane: str, reviewer: str, has_xdist: bool,
                   builder: str = "codex_build") -> str:
    gate_text = task_gates(worktree, change)
    main = main_checkout(worktree)
    sha = base_sha(worktree, base)
    xdist = ("`pytest-xdist` is installed; the gates in tasks.md say whether to use it."
             if has_xdist else "`pytest-xdist` is NOT installed. Do not install anything.")
    sandbox = f"\n{CODEX_BUILDER_SANDBOX}" if builder.startswith("codex") else ""
    steps_file = f"STEPS-{id}.json"
    steps_rule = (f"""- Apply sections 1 and 2 from `{steps_file}` in the worktree root, which holds the exact
  bytes of the verified reference; never copy fence text out of tasks.md, which is for
  reading. Apply with the shared applier from the worktree root:
  `python3 {APPLY_STEPS} {steps_file} . T` for the tests (then observe RED), then
  `python3 {APPLY_STEPS} {steps_file} . I`. It checks every anchor occurs exactly once
  before writing and stops at the first step that does not fit, naming it. After a lead
  fold, restore the named file as the ruling says and re-apply only its steps with
  `python3 {APPLY_STEPS} {steps_file} . --path <file>`. Do not write your own applier.
""" if (worktree / steps_file).exists() else "")
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
- ruff is on PATH. Linter caches cannot be written inside the worktree, so prefix
  every ruff and mypy command with the cache locations:
  `{cache_env(id)} ruff check <paths>` and
  `{cache_env(id)} PYTHONPATH=src {python} -m mypy`.
- {xdist}
- Write temporary files into the worktree root, never `/tmp` (the linter caches above are
  the one exception), and name them `SCRATCH-<anything>`;
  the reviewer's change list ignores those and flags any other stray file.
{sandbox}
## Measured gates (your run's COUNTS must match)

Check each with `python3 {GATES} match "<expected line>" <output file>`: it prints
MATCH, or the counts that differ. pytest's warnings and wall time do not count.

{gate_text}
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
{steps_rule}- Never loosen, delete, or skip an assertion to make a test pass.
- Allowed files (edit nothing else):
{allowed}
- Mutation drives (section 3): run `python3 {MUTATE} openspec/changes/{change}/tasks.md .`
  after GREEN, with no test run going in this worktree. It drives each one
  in turn, restores every file, and checks the tree is unchanged; paste its
  output into the handoff. Do not hand-edit mutations. A SURVIVED, VOID or
  TREE CHANGED line is a BLOCKED, not a skip.

## Handoff — write `HANDOFF-{id}.md` in the worktree root

1. Self-review, 10 lines or fewer: what changed, biggest risk, where to look first.
2. RED tail and GREEN tail (literal). After a lead fold, keep the pre-fold RED tails and add one
   line saying they were not re-observed after the fold; the lead re-observes RED in scratch.
3. Full-suite tail, VERBATIM (you run the full suite once per build-state).
4. The `python3 {GATES} match` MATCH line for every pytest count gate (RED, GREEN,
   each touched file, the full suite) — not the raw tail; ruff and mypy last
   lines; every grep gate's output; the fence check's output —
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
    python3 {DISPATCH} {reviewer} --file CODEX-PROMPT-{id}-round-N.md

(Replace the N in the sed and the file names with the round number. If the
lead gave you a ruling, put its sentence in place of `none`.) The command
returns only when the reviewer has settled; a Herdr wait timeout is treated
as "still working" and waited out. Then read `REVIEW-{id}-round-N.md`. If it ends with `FINDINGS: <n> (spec)`,
record friction and send BLOCKED to the lead in the same round. Do not edit the fence or the spec.
Wait for the lead ruling. If the lead accepts a fence change, wait for the verified reference fold
and regenerated fences. After the lead installs any regenerated test fences,
re-apply the affected implementation files,
re-run ALL gates (including the full suite once for the new build-state), update the handoff, and
send the next round within the cap authorized by the lead ruling.
If the lead rejects the finding, pass the ruling to the next review without waiting for a fold;
keep the unchanged build-state evidence and update the handoff with the ruling.
Otherwise fix every CONFIRMED finding,
re-run ALL gates, update the handoff, send the next round. Cap: 2 rounds.

When the review file ends with `REVIEW CLEAN`:

    herdr agent prompt {lead_pane} "DONE: build for {id} — reviewer clean after N rounds — handoff at {worktree}/HANDOFF-{id}.md"

If you are stuck, an anchor does not match, a mutation survives, or you hit
the round cap with open findings:

    herdr agent prompt {lead_pane} "BLOCKED: {id} — <one line: what and where>"

Contact the lead for nothing else.

When something costs you time — a wrong instruction, a wait, a command that
failed for a reason the briefing could have prevented — record one line and
carry on (it feeds the post-run review; it is not a message to the lead):

    python3 {RUNLOG} add friction --repo {worktree} --issue {id} --agent {builder} --text "<what cost you time, and how long>"
"""


# Codex's sandbox hangs Starlette's TestClient and denies the herdr socket; both
# were retried out of it in every #459 review (sandboxed-testclient-hang,
# sandbox-socket-denied). A Claude fallback reviewer has no such sandbox.
CODEX_SANDBOX = (
    "Sandbox: run every pytest command, every mutate.py drive, and every `herdr agent prompt` "
    "outside the sandbox (request escalated permissions) on the FIRST attempt. In the sandbox the "
    "test client hangs and the herdr socket is denied; neither is a finding, and diagnosing it costs "
    "the round. Give each pytest run a 600-second timeout (`timeout 600` in front of the command), so a "
    "hang ends as an answer."
)


# A Codex builder runs in the same sandbox, and in #482 read one sentence naming
# every command class as a hint: it ran the full suite in the sandbox, which timed
# out at 24% (~15 min). One class per line, each saying OUTSIDE the sandbox.
CODEX_BUILDER_SANDBOX = """- Sandbox (Codex): request escalated permissions on the FIRST attempt for each of these.
  In the sandbox the network and the herdr socket are denied and the test client hangs;
  none of that is a defect to diagnose.
  - Every pytest command on a touched test file: OUTSIDE the sandbox, with `timeout 600` in front.
  - The full suite: OUTSIDE the sandbox, with `timeout 900` in front and `python -u` so the output file shows progress.
  - Any command in tasks.md that fetches from the network: OUTSIDE the sandbox.
  - Every mutate.py drive: OUTSIDE the sandbox.
  - Every dispatch.py call to the reviewer: OUTSIDE the sandbox.
  - Every `herdr agent prompt` to the lead: OUTSIDE the sandbox.
"""


def build_reviewer_prompt(*, id: str, worktree: pathlib.Path, branch: str, base: str, change: str, python: str,
                          lead_pane: str, reviewer: str, **_: object) -> str:
    w = worktree
    sha = base_sha(worktree, base)
    sandbox = f"\n{CODEX_SANDBOX}\n" if reviewer.startswith("codex") else ""
    return f"""You are the REVIEWER for herd build #{id}, review round ROUND_N. Do NOT edit any file except your review file. Do NOT commit.

Worktree (the build under review): {w}
Branch {branch}, base {base} at {sha} (the build is uncommitted). List what changed with `python3 {GATES} manifest {w} {sha} --allowed {w}/ALLOWED-{id}.txt` — it includes untracked files, and every OUTSIDE ALLOWED line is a finding. Read the changes with `git -C {w} diff {sha}` plus each untracked file the manifest lists.
Spec: {w}/openspec/changes/{change}/ (proposal.md, design.md if present, specs/, tasks.md). The spec directory itself is part of the change, not a finding.
Handoff: {w}/HANDOFF-{id}.md — it carries the full-suite tail verbatim; do NOT re-run the full suite unless that tail is missing or contradicts the gate in tasks.md section 0.
Lead rulings in force: RULINGS_PLACEHOLDER
{sandbox}
Do this:
1. Read the spec, then the handoff, then the diff.
2. Run the TOUCHED test files yourself from the worktree root: `cd {w} && PYTHONPATH=src {python} -m pytest <touched test files> -q --no-header`, plus the ruff, mypy and grep gates in tasks.md, each ruff and mypy command prefixed `{cache_env(id)}`. Record the commands and their last lines.
3. Check the build against tasks.md: the fences are byte-exact reference text, so run `python3 {FENCECHECK} {w}/openspec/changes/{change}/tasks.md {w}` — a line starting `{fencecheck.OK}` (it prints `{fencecheck.OK} (<n> steps)`) is success, and every other line it prints is a finding (step, file, why); do not re-check fences by eye. Any edit to a file outside the allowed list is a finding; root files matching {", ".join(f"`{p}`" for p in gates.COORDINATION)} are coordination files, and `openspec/changes/{change}/` is the change's own spec copy, allowed by the ALLOWED file: neither is a finding.
4. Re-drive two mutations of your choice on a scratch copy, which never touches the build: `python3 {MUTATE} {w}/openspec/changes/{change}/tasks.md {w} --scratch --only "<full name>,<full name>"` (the full section-3 labels, quoted). A result that differs from the handoff's mutation log is a finding.
5. If a CONFIRMED finding requires changing a byte-exact fence, tag it "in the fence"; never mark it FOLDED while unresolved. These unresolved findings prevent REVIEW CLEAN. Count all unresolved confirmed findings and end with `FINDINGS: <n> (spec)` when any are in the fence.
6. Report ONLY CONFIRMED defects — ones you reproduced or can show at file:line — each with an exact fix. Do not propose work the proposal's Non-goals exclude, new subsystems, persistence, or refactors.

Write {w}/REVIEW-{id}-round-ROUND_N.md: what you ran (commands + last lines), what you checked, then numbered findings. End the file with exactly one sentinel line: `FINDINGS: <n>`, `FINDINGS: <n> (spec)`, or `REVIEW CLEAN`. A clean review still lists what it ran.
Reply in chat with only the path and the sentinel. If and only if the sentinel is REVIEW CLEAN, also run: herdr agent prompt {lead_pane} "REVIEW CLEAN for {id} after ROUND_N rounds"
If something in this prompt or the environment cost you time, record one line (not a message to anyone): python3 {RUNLOG} add friction --repo {w} --issue {id} --agent {reviewer} --text "<what cost you time, and how long>"
"""  # noqa: E501


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("id", "worktree", "branch", "base", "change", "allowed_file"):
        ap.add_argument(name)
    ap.add_argument("--lead-pane")
    ap.add_argument("--reviewer", default="codex_review")
    ap.add_argument("--builder", default="codex_build")
    a = ap.parse_args(argv)
    w = pathlib.Path(a.worktree)
    python = find_python(w)
    args = dict(id=a.id, worktree=w, branch=a.branch, base=a.base, change=a.change,
                allowed=pathlib.Path(a.allowed_file).read_text().rstrip(),
                python=python, lead_pane=resolve_lead_pane(a.lead_pane), reviewer=a.reviewer, builder=a.builder,
                has_xdist=has_xdist(python))
    briefing = build_briefing(**args)
    reviewer_prompt = build_reviewer_prompt(**args)
    (w / f"ALLOWED-{a.id}.txt").write_text(args["allowed"] + f"\n  - `openspec/changes/{a.change}/`\n")
    (w / f"BUILD-BRIEFING-{a.id}.md").write_text(briefing)
    (w / f"CODEX-PROMPT-{a.id}.md").write_text(reviewer_prompt)
    print("wrote briefing + codex prompt in", w)


if __name__ == "__main__":
    main()
