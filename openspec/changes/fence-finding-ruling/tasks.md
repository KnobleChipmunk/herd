# Tasks: findings in byte-exact fences

## 0. Gates

Baseline: main at 1a9ac3f, measured in /tmp/herd-proposal-fence-reference before edits.
Full suite baseline: 509 passed in 11.38s. Expected build: baseline + one test, 510 passed. Observed GREEN: 510 passed in 10.92s.
Touched tests baseline: 25 passed; expected build: 26 passed.
Run `python3 -m pytest tests/test_mkbrief.py -q --no-header` after tests first: expect 1 failed, 25 passed. Then apply implementation.
After implementation run `python3 -m pytest -q` once and `ruff check tools tests` (baseline: All checks passed!).
Type checking is not checked: no configured project command and python3 -m mypy --version reports No module named mypy. pytest-xdist is absent; run serially.
Run `python3 tools/gates.py count 'FINDINGS: <n> (spec)' tools/mkbrief.py` (baseline 0; build 3).
Run `python3 /home/tusk/projects/herd/tools/fencecheck.py openspec/changes/fence-finding-ruling/tasks.md .`: expected FENCES OK (11 steps), the 10 steps below.
Run all section 3 mutations after GREEN; all five must be KILLED. Pre-execution observed M1 KILLED, M2 KILLED, M3 KILLED, M4 KILLED and M5 KILLED, each with FAILED tests/test_mkbrief.py::test_fence_owned_findings_block_in_the_same_review_round. Ruff: All checks passed! Fence parity: FENCES OK (11 steps). Touched GREEN: 26 passed in 0.54s. RED: 1 failed, 25 passed in 0.57s.

## 1. Tests first

- [ ] **T1** `tests/test_mkbrief.py` — Append the regression with two blank lines before its def.

Append exactly this text at the END of the file. The fence below BEGINS with the blank lines that separate it from the existing last line — keep them. The file must end with one newline:

```python


def test_fence_owned_findings_block_in_the_same_review_round(repo_with_worktree):
    _, _, briefing, prompt = brief(repo_with_worktree)
    assert "FINDINGS: <n> (spec)" in prompt
    assert 'tag it "in the fence"' in prompt
    assert "never mark it FOLDED" in prompt
    assert "unresolved findings prevent REVIEW CLEAN" in prompt
    assert "FINDINGS: <n> (spec)" in briefing
    assert "send BLOCKED to the lead in the same round" in briefing
    assert "Do not edit the fence or the spec" in briefing
    recovery = briefing.split("Wait for the lead", 1)[1].split("Otherwise", 1)[0]
    assert "re-run ALL gates" in recovery
    assert "update the handoff" in recovery
    assert "send the next round" in recovery
    assert "once per build-state" in briefing
    assert "If the lead accepts a fence change" in recovery
    assert "If the lead rejects the finding" in recovery
    assert "without waiting for a fold" in recovery
    assert "the lead installs any regenerated test fences" in recovery
    assert "re-apply the affected implementation files" in recovery
```

## 2. Implementation

- [ ] **I1** `tools/mkbrief.py` — Replace this unique quoted block; retain exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python

1. Self-review, 10 lines or fewer: what changed, biggest risk, where to look first.
2. RED tail and GREEN tail (literal).
3. Full-suite tail, VERBATIM (you run the full suite exactly once).
4. ruff and mypy last lines; every grep gate's output; the fence check's output —
   `python3 {FENCECHECK} openspec/changes/{change}/tasks.md .` must print
   `FENCES OK (<n> steps)`; any other line is a deviation to fix before review.
```

Replace it with exactly:

```python

1. Self-review, 10 lines or fewer: what changed, biggest risk, where to look first.
2. RED tail and GREEN tail (literal).
3. Full-suite tail, VERBATIM (you run the full suite once per build-state).
4. ruff and mypy last lines; every grep gate's output; the fence check's output —
   `python3 {FENCECHECK} openspec/changes/{change}/tasks.md .` must print
   `FENCES OK (<n> steps)`; any other line is a deviation to fix before review.
```

- [ ] **I2** `tools/mkbrief.py` — Replace this unique quoted block; retain exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
(Replace the N in the sed and the file names with the round number. If the
lead gave you a ruling, put its sentence in place of `none`.) The command
returns only when the reviewer has settled; a Herdr wait timeout is treated
as "still working" and waited out. Then read `REVIEW-{id}-round-N.md`. Fix every CONFIRMED finding,
re-run ALL gates, update the handoff, send the next round. Cap: 2 rounds.

When the review file ends with `REVIEW CLEAN`:
```

Replace it with exactly:

```python
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
```

- [ ] **I3** `tools/mkbrief.py` — Replace this unique quoted block; retain exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
2. Run the TOUCHED test files yourself from the worktree root: `cd {w} && PYTHONPATH=src {python} -m pytest <touched test files> -q --no-header`, plus the ruff, mypy and grep gates in tasks.md. Record the commands and their last lines.
3. Check the build against tasks.md: the fences are byte-exact reference text, so run `python3 {FENCECHECK} {w}/openspec/changes/{change}/tasks.md {w}` — a line starting `{fencecheck.OK}` (it prints `{fencecheck.OK} (<n> steps)`) is success, and every other line it prints is a finding (step, file, why); do not re-check fences by eye. Any edit to a file outside the allowed list is a finding; root files matching {", ".join(f"`{p}`" for p in gates.COORDINATION)} are coordination files, and `openspec/changes/{change}/` is the change's own spec copy, allowed by the ALLOWED file: neither is a finding.
4. Re-drive two mutations of your choice on a scratch copy, which never touches the build: `python3 {MUTATE} {w}/openspec/changes/{change}/tasks.md {w} --scratch --only <name>,<name>`. A result that differs from the handoff's mutation log is a finding.
5. Report ONLY CONFIRMED defects — ones you reproduced or can show at file:line — each with an exact fix. Do not propose work the proposal's Non-goals exclude, new subsystems, persistence, or refactors.

Write {w}/REVIEW-{id}-round-ROUND_N.md: what you ran (commands + last lines), what you checked, then numbered findings. End the file with exactly one sentinel line: `FINDINGS: <n>` or `REVIEW CLEAN`. A clean review still lists what it ran.
Reply in chat with only the path and the sentinel. If and only if the sentinel is REVIEW CLEAN, also run: herdr agent prompt {lead_pane} "REVIEW CLEAN for {id} after ROUND_N rounds"
If something in this prompt or the environment cost you time, record one line (not a message to anyone): python3 {RUNLOG} add friction --repo {w} --issue {id} --agent {reviewer} --text "<what cost you time, and how long>"
"""  # noqa: E501
```

Replace it with exactly:

```python
2. Run the TOUCHED test files yourself from the worktree root: `cd {w} && PYTHONPATH=src {python} -m pytest <touched test files> -q --no-header`, plus the ruff, mypy and grep gates in tasks.md. Record the commands and their last lines.
3. Check the build against tasks.md: the fences are byte-exact reference text, so run `python3 {FENCECHECK} {w}/openspec/changes/{change}/tasks.md {w}` — a line starting `{fencecheck.OK}` (it prints `{fencecheck.OK} (<n> steps)`) is success, and every other line it prints is a finding (step, file, why); do not re-check fences by eye. Any edit to a file outside the allowed list is a finding; root files matching {", ".join(f"`{p}`" for p in gates.COORDINATION)} are coordination files, and `openspec/changes/{change}/` is the change's own spec copy, allowed by the ALLOWED file: neither is a finding.
4. Re-drive two mutations of your choice on a scratch copy, which never touches the build: `python3 {MUTATE} {w}/openspec/changes/{change}/tasks.md {w} --scratch --only <name>,<name>`. A result that differs from the handoff's mutation log is a finding.
5. If a CONFIRMED finding requires changing a byte-exact fence, tag it "in the fence"; never mark it FOLDED while unresolved. These unresolved findings prevent REVIEW CLEAN. Count all unresolved confirmed findings and end with `FINDINGS: <n> (spec)` when any are in the fence.
6. Report ONLY CONFIRMED defects — ones you reproduced or can show at file:line — each with an exact fix. Do not propose work the proposal's Non-goals exclude, new subsystems, persistence, or refactors.

Write {w}/REVIEW-{id}-round-ROUND_N.md: what you ran (commands + last lines), what you checked, then numbered findings. End the file with exactly one sentinel line: `FINDINGS: <n>`, `FINDINGS: <n> (spec)`, or `REVIEW CLEAN`. A clean review still lists what it ran.
Reply in chat with only the path and the sentinel. If and only if the sentinel is REVIEW CLEAN, also run: herdr agent prompt {lead_pane} "REVIEW CLEAN for {id} after ROUND_N rounds"
If something in this prompt or the environment cost you time, record one line (not a message to anyone): python3 {RUNLOG} add friction --repo {w} --issue {id} --agent {reviewer} --text "<what cost you time, and how long>"
"""  # noqa: E501
```

- [ ] **I4** `skill/cards/builder.md` — Replace this unique quoted block; retain exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python

## Scope

Only the worktree and the briefing's allowed files. Tests first (apply the T steps, observe RED), then the I steps, then every gate, then the mutation drives. The full suite runs once, after all edits.

## Evidence

```

Replace it with exactly:

```python

## Scope

Only the worktree and the briefing's allowed files. Tests first (apply the T steps, observe RED), then the I steps, then every gate, then the mutation drives. The full suite runs once per build-state after that state's edits, including after an accepted reference fold.

## Evidence

```

- [ ] **I5** `skill/cards/builder.md` — Replace this unique quoted block; retain exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python

## Authority

Sends review rounds to the build reviewer; fixes every CONFIRMED finding and re-runs all gates; cap 2 rounds, +1 on a lead ruling. At the cap: `BLOCKED:` to the lead with the open findings. On `REVIEW CLEAN`: `DONE: build for <id> — reviewer clean after N rounds — handoff at <path>`.

## Exclusions

Never commits, pushes, or leaves the worktree; never edits a test after the tests-first step or loosens an assertion; contacts the lead only with BLOCKED or DONE.
```

Replace it with exactly:

```python

## Authority

Sends review rounds to the build reviewer; fixes every CONFIRMED finding and re-runs all gates; cap 2 rounds, +1 on a lead ruling. A CONFIRMED finding that requires deviating from a byte-exact fence is not builder-fixable; record friction and report it for a lead ruling in the same round. Do not edit the fence or the spec. At the cap: `BLOCKED:` to the lead with the open findings. On `REVIEW CLEAN`: `DONE: build for <id> — reviewer clean after N rounds — handoff at <path>`.

## Exclusions

Never commits, pushes, or leaves the worktree; never edits a test after the tests-first step or loosens an assertion (the lead installs verified regenerated test fences after a ruling); contacts the lead only with BLOCKED or DONE.
```

- [ ] **I6** `skill/SKILL.md` — Replace this unique quoted block; retain exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
1. Prompts `codex_review` with the worktree path, spec path, handoff path,
   round number, and the sentinel contract (via the sed'd per-round
   prompt file). `--wait --timeout 540000`, re-waiting on timeout.
2. Reads the review file; fixes every CONFIRMED finding; re-runs ALL
   gates; updates the handoff; sends the next round.
3. Repeats until the reviewer writes `REVIEW CLEAN`. Cap **2 rounds**
   (+1 on a ruling); at the cap it sends the lead `BLOCKED:` with the open
```

Replace it with exactly:

```python
1. Prompts `codex_review` with the worktree path, spec path, handoff path,
   round number, and the sentinel contract (via the sed'd per-round
   prompt file). `--wait --timeout 540000`, re-waiting on timeout.
2. Reads the review file; on `FINDINGS: <n> (spec)` records friction and
   sends BLOCKED in that round (see Rulings); otherwise fixes every
   CONFIRMED finding; re-runs ALL
   gates; updates the handoff; sends the next round.
3. Repeats until the reviewer writes `REVIEW CLEAN`. Cap **2 rounds**
   (+1 on a ruling); at the cap it sends the lead `BLOCKED:` with the open
```

- [ ] **I7** `skill/SKILL.md` — Replace this unique quoted block; retain exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
runs the **touched** test
files itself (not the full suite — the handoff carries that tail
verbatim), reports only CONFIRMED defects with file:line and an exact
fix, writes `REVIEW-<id>-round-N.md`, ends with `FINDINGS: <n>` or
`REVIEW CLEAN`. A clean round still lists what it ran and what it checked
(commands + last lines) — a file that is only the sentinel is not
evidence (#330). It talks only to the builder, and contacts the lead only to
sign off: `REVIEW CLEAN for <id> after N rounds`.
```

Replace it with exactly:

```python
runs the **touched** test
files itself (not the full suite — the handoff carries that tail
verbatim), reports only CONFIRMED defects with file:line and an exact
fix, writes `REVIEW-<id>-round-N.md`, ends with `FINDINGS: <n>`,
`FINDINGS: <n> (spec)` when any unresolved confirmed finding is in a byte-exact
fence (see Rulings), or `REVIEW CLEAN`. A clean round still lists what it ran and what it checked
(commands + last lines) — a file that is only the sentinel is not
evidence (#330). It talks only to the builder, and contacts the lead only to
sign off: `REVIEW CLEAN for <id> after N rounds`.
```

- [ ] **I8** `skill/SKILL.md` — Replace this unique quoted block; retain exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
     → post the spec summary AND dispatch, same turn: worktree + briefing → prompt pi_build
       (prerequisite found mid-review? carve it out, loop it first, stack the branch)
pi_build:  tests red → impl → gates → mutations → HANDOFF → review round 1
codex_review: REVIEW-round-1 (FINDINGS: n)   ┐
pi_build:  fix → gates → HANDOFF → round 2   ┘ … until REVIEW CLEAN (cap 2, +1 on ruling)
codex_review: "REVIEW CLEAN" → lead;  pi_build: "DONE: …" → lead
lead:  diff build vs pre-executed reference → /reviewer (direct, audience: ai)
```

Replace it with exactly:

```python
     → post the spec summary AND dispatch, same turn: worktree + briefing → prompt pi_build
       (prerequisite found mid-review? carve it out, loop it first, stack the branch)
pi_build:  tests red → impl → gates → mutations → HANDOFF → review round 1
codex_review: REVIEW-round-1 (FINDINGS: n; spec finding → builder BLOCKED → lead ruling)   ┐
pi_build:  fix → gates → HANDOFF → round 2   ┘ … until REVIEW CLEAN (cap 2, +1 on ruling)
codex_review: "REVIEW CLEAN" → lead;  pi_build: "DONE: …" → lead
lead:  diff build vs pre-executed reference → /reviewer (direct, audience: ai)
```

- [ ] **I9** `skill/SKILL.md` — Replace this unique quoted block; retain exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
re-prompt.

## Rulings

The lead rules when: the reviewer proposes work outside the spec's Non-goals;
the builder is at the cap; the builder asks. A ruling names the finding,
```

Replace it with exactly:

```python
re-prompt.

## Rulings

**Finding in a byte-exact fence.** The build reviewer tags each such confirmed
finding "in the fence", keeps it unresolved (never FOLDED), and ends the round
with `FINDINGS: <n> (spec)`, counting all unresolved confirmed findings.
The builder records friction and sends BLOCKED in that same round, without
editing the fence or spec. If the lead rejects the finding, the builder passes
the ruling to the next review without waiting for a fold, preserves the
unchanged build-state evidence, and records the ruling in the handoff.
For an accepted fence change, the lead marks `gates.py fold start --issue <id>`,
folds the accepted fix into the reference,
re-runs the affected tests and mutations, regenerates the fences, verifies
byte parity, installs any regenerated test fences in the build worktree,
then marks `gates.py fold done --issue <id>`. The builder
re-applies the affected implementation files, re-runs all gates (including the full suite once
for the new build-state after `gates.py suite-ok --issue <id>`), updates the
handoff and resumes review within the cap authorized by the lead ruling. A pending reference fold prevents REVIEW CLEAN and DONE.

The lead rules when: the reviewer proposes work outside the spec's Non-goals;
the builder is at the cap; the builder asks. A ruling names the finding,
```

- [ ] **I10** `skill/cards/build-reviewer.md` — Replace this unique quoted block; retain exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
## Outputs

`REVIEW-<id>-round-N.md`, opening with a `Candidate: <commit or tree>` line
(`team.py gate review-file` checks it) and ending `FINDINGS: <n>` or `REVIEW CLEAN`.

## Activation

```

Replace it with exactly:

```python
## Outputs

`REVIEW-<id>-round-N.md`, opening with a `Candidate: <commit or tree>` line
(`team.py gate review-file` checks it) and ending `FINDINGS: <n>`, `FINDINGS: <n> (spec)` when any
unresolved confirmed finding is in a byte-exact fence, or `REVIEW CLEAN`.

## Activation

```

## 3. Mutation drives

- [ ] **M5** in `tools/mkbrief.py`: replace

```python
the lead installs any regenerated test fences
```

with

```python
the builder edits regenerated tests
```

Killer: `tests/test_mkbrief.py::test_fence_owned_findings_block_in_the_same_review_round`

- [ ] **M4** in `tools/mkbrief.py`: replace

```python
without waiting for a fold
```

with

```python
after a required fold
```

Killer: `tests/test_mkbrief.py::test_fence_owned_findings_block_in_the_same_review_round`

- [ ] **M1** in `tools/mkbrief.py`: replace

```python
tag it "in the fence"
```

with

```python
tag it "ordinary"
```

Killer: `tests/test_mkbrief.py::test_fence_owned_findings_block_in_the_same_review_round`

- [ ] **M2** in `tools/mkbrief.py`: replace

```python
send BLOCKED to the lead in the same round
```

with

```python
continue to another review round
```

Killer: `tests/test_mkbrief.py::test_fence_owned_findings_block_in_the_same_review_round`

- [ ] **M3** in `tools/mkbrief.py`: replace

```python
re-run ALL gates (including the full suite once for the new build-state)
```

with

```python
skip the gates for the new build-state
```

Killer: `tests/test_mkbrief.py::test_fence_owned_findings_block_in_the_same_review_round`
