"""Write BUILD-BRIEFING-<id>.md and CODEX-PROMPT-<id>.md into a build worktree.

usage: mkbrief.py <id> <worktree> <branch> <base-desc> <change-name> <gates-file> <allowed-files-file>
"""
import pathlib
import sys

ID, W, BRANCH, BASE, CHANGE, GATES, ALLOWED = sys.argv[1:8]
w = pathlib.Path(W)
gates = pathlib.Path(GATES).read_text()
allowed = pathlib.Path(ALLOWED).read_text().strip()
PY = "/home/tusk/projects/project-mera/.venv/bin/python"

briefing = f"""# BUILD BRIEFING — #{ID} ({CHANGE})

You are the BUILDER. Work ONLY in this worktree:

    {W}

Branch `{BRANCH}`, cut from {BASE}. Do NOT touch `/home/tusk/projects/project-mera`
(the main checkout) or any other worktree. Never `git commit`, `git push`,
`git checkout <file>`, `git stash`, or `git reset`. To undo an edit, re-edit the file.

## Environment

- Python: `{PY}` — every python/pytest/mypy command is run from the worktree
  root and prefixed `PYTHONPATH=src`, e.g.
  `PYTHONPATH=src {PY} -m pytest tests/mera/check/test_schema.py -q --no-header`
- ruff is on PATH: `ruff check <paths>`.
- `pytest-xdist` is NOT installed. Do not install anything.
- Write temporary files into the worktree root, never `/tmp`.

## Measured gates (literal last lines; your run must match)

{gates}
## The spec — read in this order

1. `openspec/changes/{CHANGE}/proposal.md`
2. `openspec/changes/{CHANGE}/design.md` (if present)
3. `openspec/changes/{CHANGE}/specs/` (the delta)
4. `openspec/changes/{CHANGE}/tasks.md` — THIS IS YOUR CHECKLIST.

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

## Handoff — write `HANDOFF-{ID}.md` in the worktree root

1. Self-review, 10 lines or fewer: what changed, biggest risk, where to look first.
2. RED tail and GREEN tail (literal).
3. Full-suite tail, VERBATIM (you run the full suite exactly once).
4. ruff and mypy last lines; every grep gate's output.
5. `git diff --stat`.
6. Sibling sweep result, if tasks.md asks for one.
7. Mutation log: name, KILLED/SURVIVED, the observed FAILED line.
8. Every assertion in this handoff NOT backed by a tool result you ran.
9. Round log: one line per review round (findings, what you changed).

## Coordination (run these literally, from the worktree root)

Review round N (N = 1, 2): make the per-round prompt, then send it.

    sed -e "s/ROUND_N/N/g" -e "s/RULINGS_PLACEHOLDER/none/" CODEX-PROMPT-{ID}.md > CODEX-PROMPT-{ID}-round-N.md
    herdr agent prompt opus_review "$(cat CODEX-PROMPT-{ID}-round-N.md)" --wait --timeout 540000

(Replace the N in the sed and the file names with the round number. If the
lead gave you a ruling, put its sentence in place of `none`.) If the command
exits with "timed out waiting for agent status", the reviewer is STILL
WORKING: run `herdr agent wait opus_review --timeout 540000` and repeat until
it returns. Then read `REVIEW-{ID}-round-N.md`. Fix every CONFIRMED finding,
re-run ALL gates, update the handoff, send the next round. Cap: 2 rounds.

When the review file ends with `REVIEW CLEAN`:

    herdr agent prompt w1:p1S "DONE: build for {ID} — reviewer clean after N rounds — handoff at {W}/HANDOFF-{ID}.md"

If you are stuck, an anchor does not match, a mutation survives, or you hit
the round cap with open findings:

    herdr agent prompt w1:p1S "BLOCKED: {ID} — <one line: what and where>"

Contact the lead for nothing else.
"""

codex = f"""You are the REVIEWER for herd build #{ID}, review round ROUND_N. Do NOT edit any file except your review file. Do NOT commit.

Worktree (the build under review): {W}
Branch {BRANCH}; review the diff against its base: run `git -C {W} diff` plus `git -C {W} status --short` (the build is uncommitted; base is {BASE}).
Spec: {W}/openspec/changes/{CHANGE}/ (proposal.md, design.md if present, specs/, tasks.md). The spec directory itself is part of the change, not a finding.
Handoff: {W}/HANDOFF-{ID}.md — it carries the full-suite tail verbatim; do NOT re-run the full suite unless that tail is missing or contradicts the gate in tasks.md section 0.
Lead rulings in force: RULINGS_PLACEHOLDER

Do this:
1. Read the spec, then the handoff, then the diff.
2. Run the TOUCHED test files yourself from the worktree root: `cd {W} && PYTHONPATH=src {PY} -m pytest <touched test files> -q --no-header`, plus the ruff, mypy and grep gates in tasks.md. Record the commands and their last lines.
3. Check the build against tasks.md: the fences are byte-exact reference text, so any deviation from a fence is a finding; any edit to a file outside the allowed list is a finding; BUILD-BRIEFING/HANDOFF/REVIEW/CODEX files are coordination files, not findings.
4. Report ONLY CONFIRMED defects — ones you reproduced or can show at file:line — each with an exact fix. Do not propose work the proposal's Non-goals exclude, new subsystems, persistence, or refactors.

Write {W}/REVIEW-{ID}-round-ROUND_N.md: what you ran (commands + last lines), what you checked, then numbered findings. End the file with exactly one sentinel line: `FINDINGS: <n>` or `REVIEW CLEAN`. A clean review still lists what it ran.
Reply in chat with only the path and the sentinel. If and only if the sentinel is REVIEW CLEAN, also run: herdr agent prompt w1:p1S "REVIEW CLEAN for {ID} after ROUND_N rounds"
"""

(w / f"BUILD-BRIEFING-{ID}.md").write_text(briefing)
(w / f"CODEX-PROMPT-{ID}.md").write_text(codex)
print("wrote briefing + codex prompt in", W)
