---
name: herd
description: Run the Herdr three-agent build loop — Fable (this session) orchestrates, pre-executes, and writes the openspec change, a local qwen (via pi) builds it in a worktree, a pi reviewer (gpt-5.6-sol) reviews round-robin until clean, and Fable runs the `reviewer` skill (audience: ai) as the final pass, then collects a skill retrospective from every agent. Use when the user says "/herd", "herd #N", "run the herd on <issue|goal>", or asks to build an issue with qwen via Herdr. Requires HERDR_ENV=1. Subagents are replaced by a pane below this one — pi (gpt-5.6-sol, high) for plan review, opus for every other role.
---

# Herd — Fable orchestrates, qwen builds, pi reviews

One session — **Fable, this one** — talks to the user, writes the spec,
pre-executes it, rules on disputes, and does the final review. Everything
else runs in Herdr panes beside it and reports inward. Proven shape:
project-mera #280 → PR #325 (2026-08-19): 4 plan-review rounds, 5 review
rounds to clean. #310 → PR #330 (same day): post-mortem found 8 of 11 plan
findings avoidable upstream; rules marked **(#330)** come from it. #321 →
PRs #377/#378 (2026-08-25): lead pre-execution + byte-synced fences made
both builds byte-identical to the reference and both reviews clean in ONE
round; a mid-review shared-infra defect forced a prerequisite carve-out.
Rules marked **(#321)** come from that retrospective.

Load the `herdr` skill first; the `herdr` CLI is the authority on syntax.
`test "${HERDR_ENV:-}" = 1` or stop — this skill does not work outside Herdr.

## Size tier — decide at pick time (#330)

The loop's fixed cost (spec + plan review + worktree + briefing + review +
final review) is 30–40 min. Say which tier the change is in the first
message to the user, and run that tier.

| | **small** | **full** |
|---|---|---|
| Shape | ≤3 source files, ≤~50 lines, no new mechanism — a table row, a guard, a message, a test re-point | anything with a new mechanism, a design choice worth recording, >3 source files, or a data/intake path |
| Spec | proposal (Grounded facts + Non-goals) + tasks.md; design.md only if a decision was actually made; spec delta still required by openspec | all four files |
| Pre-execution | Fable applies the tasks in a scratch worktree and runs the touched tests + mutations before plan review (#321) | same, plus the full suite once and EVERY mutation driven |
| Plan review | **one** round; the reviewer reads, re-derives the gates, and reasons — it never executes | rounds until APPROVE; the reviewer re-derives and challenges, it does NOT re-execute — Fable's pre-execution evidence is cited in the brief (#321) |
| Build | qwen builds from the byte-synced fences | qwen builds from the byte-synced fences |
| Review rounds | one round, cap 2 | cap 2 (+1 on ruling) — pre-execution moved the effort upstream (#321) |
| Final review | read the diff; run only the touched test files + the spec's grep gate; full suite only if the diff reaches a shared module | `reviewer` skill, direct, audience ai; diff the build against the pre-executed reference worktree first — byte-identical is the expected result (#321) |

Everything else (the spec post, worktree, briefing, retrospective, gates
the user holds, exclusions) is the same in both tiers.

## Topology

All panes live in Fable's tab. Fable keeps focus; every split uses
`--no-focus` and `--cwd` set explicitly. Every herd role runs through
`pi` (#321) — the model must be verified from the pane STATUS LINE
(`herdr agent read <name> --source visible`), never by asking the model.

| Slot | Position | Agent | Name | Job |
|---|---|---|---|---|
| 0 | the calling pane | claude (Fable) | — | user contact, spec, pre-execution, rulings, final review, commit |
| 1 | top-right of Fable | pi (ollama qwen) | `pi_build` | builder, in its own worktree |
| 2 | bottom-right of Fable | pi (gpt-5.6-sol high) | `pi_review` | reviewer, round-robin with the builder |
| 3 | below Fable | pi (gpt-5.6-sol high) for plan review, else claude via `opus` alias | `pi_plan_reviewer` / `opus_<role>` | stands in for ANY subagent Fable would spawn; one occupant at a time |

**Reuse rule.** Before creating a pane, `herdr agent list`. If a live agent
of the right kind already sits in the slot (same tab, right position per
`herdr pane layout`), rename it (`herdr agent rename <id> <name>`) and
reuse it. Otherwise split and start. Panes are left open at the end — the
user can watch and re-prompt them.

Creating the panes, once (verified 2026-08-23/25):

```bash
herdr pane split --current --direction right --cwd "$PWD" --no-focus     # → slot 1 (read .result.pane.pane_id)
herdr pane split --pane <slot1> --direction down --cwd "$PWD" --no-focus  # → slot 2
herdr pane split --current --direction down --cwd "$PWD" --no-focus       # → slot 3
herdr agent start pi_build         --kind pi --pane <slot1> -- --provider ollama --model qwen3.8-128k:latest
herdr agent start pi_review        --kind pi --pane <slot2> -- --provider openai-codex --model gpt-5.6-sol --thinking high
herdr agent start pi_plan_reviewer --kind pi --pane <slot3> -- --provider openai-codex --model gpt-5.6-sol --thinking high
```

Status lines read `(ollama) qwen3.8-128k:latest • medium` and
`(openai-codex) gpt-5.6-sol • high`. Both `openai` and `openai-codex`
report ready for gpt-5.6-sol; `openai-codex` reuses the codex OAuth.
`pi --list-models <search>` shows what is reachable without starting
anything.

**Slot 3 for every other subagent role** (`opus_explore`, `opus_debug`, …):

```bash
herdr agent start opus_<role> --kind claude --pane <slot3> -- \
  --dangerously-skip-permissions --model opus \
  --append-system-prompt-file "$HOME/projects/fixing-smartass-opus-5/sr_opus_5_system_prompt.md"
```

The slot holds one agent at a time. Same kind, next role: rename and
re-prompt. Different kind: `herdr agent prompt <name> "/quit"` (pi/codex)
or `"/exit"` (claude), then `agent start` the replacement in the same
pane. Multiple pi agents are live at once — always target by NAME, never
by kind.

Prompts to any pane agent: write multi-line or quote-heavy prompts to a
file and `herdr agent prompt <name> "$(cat file)" …`. Replies: have the
agent write a file and read that — pane reads cut long output off.

**Long agent turns run backgrounded (#321).** `herdr agent prompt …
--wait` under the Bash tool's 10-minute cap produces timeout errors that
read like failures. Standing convention: run the prompt with `--wait
--timeout 540000` as a BACKGROUND task, treat an exit-1
`timed out waiting for agent status` as "still working", follow with
`herdr agent wait <name>` (also backgrounded) as needed, and let the
completion notifications drive the loop. Never poll in a foreground loop.

**Plan-reviewer brief (#330, #321).** Tell it the tier and that the plan
was ALREADY pre-executed — name the scratch worktree (read-only for it)
and the observed evidence (RED tail, GREEN counts, mutation kills, gate
lines). Direct its effort at what execution cannot catch: re-derive the
fixture arithmetic independently (a wrong expected value that the
implementation reproduces passes tests AND mutations), challenge catalog
membership / design conventions / boundary cases, check every text anchor
resolves uniquely at HEAD, every gate is a measured literal with its
baseline named, and blank-line separation is stated for every insert.
Have it write findings to `PLAN-REVIEW-<id>-round-N.md` in the repo root
and reply with only the path plus its verdict line (APPROVE / REVISE).

**Re-review prompts are disposition-numbered (#321).** Every round after
the first opens with the previous round's findings in the REVIEWER'S OWN
numbering, each marked FOLDED / NARROWED / REJECTED with one line of
evidence (what was re-run, what it printed), then instructs: "re-read the
four files fresh and sweep for anything stale or newly contradictory —
including what the revision itself broke." In #321, two of ten rounds
found defects the fold introduced; that sweep instruction is what catches
them.

**Never** use the `Agent` tool in this skill. Every subagent is the slot-3 pane.

## Roles and hand-offs

**Fable (orchestrator + strategist + final reviewer).**
- Picks the target with the user (or takes the one given). Ranks by:
  bug > enhancement; data-loss/silent-failure first; bounded scope; red
  test already sketched.
- Writes the openspec change (`openspec/changes/<name>/`: proposal with
  Grounded facts, design, spec delta, tasks.md with tests first). Every
  claim cites file:line it actually read. `openspec validate <name>`
  passes — and note validate is WEAKER than archive: a delta for a spec
  name with no file under `openspec/specs/` must be headed `## ADDED
  Requirements`, or the archive aborts later (#321).
- **Pre-executes the spec before plan review (#321).** In a scratch
  worktree cut from HEAD: apply every tasks.md instruction literally (a
  script extracting the fences, then the anchored edits), observe RED,
  reach GREEN, run every gate, drive EVERY mutation and record the killer
  test observed. Defects found here (wrong anchors, wrong expected
  values, contract tests the plan missed) are folded into the spec before
  any reviewer sees it. After every fold round, RE-execute what changed
  and re-drive affected mutations.
- **Fences are generated, never hand-edited (#321).** The big code fences
  in tasks.md (new files, full test files) are REGENERATED from the
  verified scratch-worktree files after every fold, and byte-parity
  (`fence == file`) is asserted before each review round and before
  dispatch. A hand-edited fence that drifts from the verified file ships
  the unverified version.
- **tasks.md anchors by quoted text, never by line number (#330).** "Replace
  the function `test_x` from its `def` line through `assert len(calls) ==
  12`"; prefer insert-before-the-next-unique-sibling for structural
  inserts. A line number may appear only as a parenthetical sanity check,
  marked "at HEAD". Say how many blank lines surround every insert or
  replace.
- **Measure every gate before writing its expectation (#330), and state
  its baseline (#321).** Run the exact commands the builder will run and
  paste the literal last lines. Gates are "identical to <baseline>" or
  "<baseline> + the delta you name", never absolute — and when the change
  has a prerequisite, the baseline is the PREREQUISITE's measured state,
  re-measured whenever the prerequisite changes. Include the full-suite
  wall time so the builder does not read a 5-min run as a hang.
- **Prerequisite carve-out (#321).** When review or pre-execution finds a
  defect in shared code the change depends on: carve it into its OWN
  change (usually small tier) with its own spec and review loop; build it
  first in the same builder pane; cut the dependent change's branch FROM
  the prerequisite branch; push and PR the prerequisite first; merge in
  order (true merges make the stack safe); re-baseline every dependent
  gate and re-pin every fixture number that the prerequisite moved. The
  dependent tasks.md opens with a DEPENDS ON line naming it.
- **Pre-existing shared-infra findings (#321).** A verified review finding
  in shared code that PREDATES the change and is not a dependency: file a
  GitHub issue with the evidence, correct any spec claim the finding
  falsified, and explicitly decline to widen the diff. Record the
  disposition in the re-review prompt. (Dependency-blocking defects get
  the carve-out above instead.)
- **Posts the spec, then dispatches without waiting.** Plan-review APPROVE
  is the authorization; the user does not hold a gate here. Fable posts the
  spec summary — the defect, the fix, what was deliberately left out, the
  plan-review record, the gates — and in the SAME turn creates the
  worktree and prompts the builder. Do not end a turn on the summary
  waiting for "go". The user redirects mid-build if they want something
  different. Two things still stop the loop cold: a decision only the user
  can make (a product call, a behaviour the guild would notice), and
  anything in the operator gates below. Say which one, and wait.
- Creates the build worktree, writes the briefing, prompts `pi_build`.
- Rules on escalations (BLOCKED from the builder). A ruling is one message
  to the builder, and a sentence the builder must relay to the reviewer.
- When the builder reports the reviewer green: runs the `reviewer` skill,
  `execution: direct`, `audience: ai`, scope = the worktree diff vs its
  base. **First step: diff the build against the pre-executed reference
  worktree — byte-identical (modulo doc re-wraps) is the expected result,
  and any other delta is where the review effort goes (#321).** Findings
  go to the builder (see loop below). When its own pass is clean:
  commits on the branch (never main), then **pushes and opens the PR in
  the same turn — no confirmation step.** The review passing is the
  authorization. Stage by name, check the staged list for env files and
  secrets, show the commit, push, open the PR, and hand the user the PR
  number and the merge command. Push mechanics on this machine: the
  session's `GH_TOKEN` cannot write, and the credential manager's dialog
  cannot answer headless, so push as
  `env -u GH_TOKEN git -c credential.helper='!gh auth git-credential' push
  -u origin <branch>` — the `gh` OAuth login has `repo` scope and answers
  without a prompt. Open the PR the same way
  (`env -u GH_TOKEN gh pr create --base main --head <branch>`), and verify
  `baseRefName` on the created PR before reporting it.
  This covers every branch the loop creates and owns — the build branch,
  the `chore/` branch carrying the openspec archive, and a `chore/` branch
  amending the rules the loop itself follows. The three exceptions that
  still stop and ask, review or no review: a push to `main` or to any
  branch this loop did not create, a force-push, and anything else in the
  operator's Hard Constraints.
- **The full suite runs once per build, by the builder (#330).** Its
  literal tail lives in the handoff (Fable's pre-execution run of the
  suite is separate and earlier). The plan reviewer, pi_review, and
  Fable's final pass run the touched test files plus the grep gate; any of
  them re-runs the full suite only when the handoff's tail is missing or
  does not match the gate expectation.
- **Retrospective, after all agents report DONE (#321).** Once the final
  review is clean and the PR is pushed, and before the closing report:
  prompt EACH live herd agent (`pi_build`, `pi_review`,
  `pi_plan_reviewer`) with exactly — "What would you improve in the herd
  skill after this run? Reply with concrete, numbered items grounded in
  what you actually hit; write them to RETRO-<id>-<yourname>.md in the
  repo root and reply with only the path." Fable adds its own items the
  same way. The collected items are QUOTED to the user for signoff in the
  FINAL response only — never applied to the skill, the briefings, or the
  repo without the user's explicit signoff, and never dripped mid-loop.
  RETRO-*.md files stay untracked like the review files.

**pi_build (builder).** Works ONLY in its worktree. Tests first, red,
then implementation, then gates (pytest + ruff + mypy + the spec's grep
gate), then the mutation drives. Writes `HANDOFF-<id>.md`. Then:
1. Prompts `pi_review` with the worktree path, spec path, handoff path,
   round number, and the sentinel contract (via the sed'd per-round
   prompt file). `--wait --timeout 540000`, re-waiting on timeout.
2. Reads the review file; fixes every CONFIRMED finding; re-runs ALL
   gates; updates the handoff; sends the next round.
3. Repeats until the reviewer writes `REVIEW CLEAN`. Cap **2 rounds**
   (+1 on a ruling); at the cap it sends Fable `BLOCKED:` with the open
   findings and stops.
4. Only then prompts Fable: `DONE: build for <id> — reviewer clean after
   N rounds — handoff at <path>`.
The builder never contacts Fable between dispatch and that DONE except
`BLOCKED:`. It never commits, pushes, or leaves the worktree.

**pi_review (reviewer).** Reads spec + handoff, reviews the worktree diff
against the branch base named in its prompt, runs the **touched** test
files itself (not the full suite — the handoff carries that tail
verbatim), reports only CONFIRMED defects with file:line and an exact
fix, writes `REVIEW-<id>-round-N.md`, ends with `FINDINGS: <n>` or
`REVIEW CLEAN`. A clean round still lists what it ran and what it checked
(commands + last lines) — a file that is only the sentinel is not
evidence (#330). It talks only to the builder, and contacts Fable only to
sign off: `REVIEW CLEAN for <id> after N rounds`.

## The loop, end to end

```
Fable: pick + tier → measure gates → spec (text anchors)
     → PRE-EXECUTE in a scratch worktree: RED → GREEN → gates → all mutations,
       fold defects, regenerate fences, assert fence==file
     → pi_plan_reviewer (small: 1 round; full: until APPROVE; re-derive, never re-execute;
       disposition-numbered re-review prompts; re-execute after every fold)
     → post the spec summary AND dispatch, same turn: worktree + briefing → prompt pi_build
       (prerequisite found mid-review? carve it out, loop it first, stack the branch)
qwen:  tests red → impl → gates → mutations → HANDOFF → review round 1
pi_review: REVIEW-round-1 (FINDINGS: n)       ┐
qwen:  fix → gates → HANDOFF → round 2        ┘ … until REVIEW CLEAN (cap 2, +1 on ruling)
pi_review: "REVIEW CLEAN" → Fable;  qwen: "DONE: …" → Fable
Fable: diff build vs pre-executed reference → /reviewer (direct, audience: ai)
       findings? → builder fixes → gates → reviewer re-signs → DONE again → re-review the delta
       clean?    → commit on branch → push → open PR, same turn
       → RETRO: ask all three agents "what would you improve in the skill?"
       → closing report: PR + merge command + quoted retro items for signoff
       (user merges: env -u GH_TOKEN gh pr merge N --merge --delete-branch)
       → openspec archive on a chore branch, pushed and PR'd unasked
```

## Worktree and environment (per build)

```bash
git -C <repo> worktree add -b fix/<issue>-<slug> <repo>__worktrees/<slug> <base>   # <base> = main, or the prerequisite branch when stacked
cp -r <repo>/openspec/changes/<name> <repo>__worktrees/<slug>/openspec/changes/   # spec is committed with the PR
```
Editable installs resolve to the ORIGINAL checkout: every python/pytest
command in the worktree is prefixed `PYTHONPATH=src`, and the briefing says
so with the absolute venv path. Prove it once before dispatch:
`PYTHONPATH=src <venv>/python -c 'import <pkg>; print(<pkg>.__file__)'`
must print the worktree path. mypy's count can differ between the main
checkout and a worktree — measure in the worktree and record that number.

Once per repo, check whether `pytest-xdist` is installed; if not, say so
in the briefing and do not add a dependency without asking the user.

## Briefing template (`BUILD-BRIEFING-<id>.md` in the worktree)

Sections, in order: worktree path + branch + base + "do not touch <main
checkout>"; environment (venv path, `PYTHONPATH=src`, ruff, mypy, the
**measured literal last line of every gate at its stated baseline**, plus
the full-suite wall time); the spec files in reading order + "tasks.md is
your checklist, the big fences are byte-exact file bodies — write them
verbatim"; rules (tests red first, anchors are quoted text, never loosen
an assertion, allowed file list, no git commit/push); handoff contents
(self-review ≤10 lines, RED and GREEN tails, full-suite tail verbatim,
lint/type results, grep gates, diff stat, sibling sweep if a defect fix,
mutation log with observed failure lines, unbacked-assertion list, round
log); the herdr coordination block with the **literal** `herdr agent
prompt …` commands for review rounds, BLOCKED, and DONE. Put the reviewer
prompt in its own file (`CODEX-PROMPT-<id>.md`, with `ROUND_N` and
`RULINGS_PLACEHOLDER` tokens) and have the builder `sed` a per-round copy
into the worktree root. Prompt the builder with one line pointing at the
briefing file.

## Mutation drives — canonical script (#321)

Specs name mutations and killer tests; the mechanics are always the same.
Both Fable (pre-execution) and the builder drive them with this shape —
adapt paths, never the discipline:

```python
import pathlib, subprocess, shutil
W = pathlib.Path("<worktree>"); PY = "<venv>/bin/python"
MUTS = [("M1", W/"src/pkg/mod.py", "<unique old text>", "<mutated text>",
         "tests/test_mod.py::test_killer"), ...]
for name, path, old, new, test in MUTS:
    orig = path.read_text()
    assert orig.count(old) == 1, (name, "anchor not unique")
    path.write_text(orig.replace(old, new, 1))
    for pc in W.rglob("__pycache__"): shutil.rmtree(pc, ignore_errors=True)
    r = subprocess.run([PY, "-m", "pytest", test, "-q", "--no-header"],
        cwd=W, capture_output=True, text=True,
        env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin",
             "PYTHONDONTWRITEBYTECODE": "1", "HOME": "<home>"})
    print(name, "KILLED" if r.returncode else "SURVIVED")
    path.write_text(orig)
```

Rules the script encodes: one mutation at a time; the anchor must be
unique or the drive is void; `__pycache__` cleared between mutate and
restore; the file restored after EVERY drive; a SURVIVED result means the
test or the mutation is wrong — fix the spec, never skip the drive.

## Monitoring

The backgrounded prompt/wait notifications are the primary wake signal.
Read each review file as it lands — you are watching for the reviewer
drifting out of scope (a round that asks for a new subsystem, persistence,
or a refactor the spec excluded). That is the moment for a lead ruling to
the builder, not after the cap.

Agents report `idle`/`done` when finished. A builder that settles
**without** sending DONE or BLOCKED has stalled mid-reasoning (local
models do this): read its pane, answer the question it got stuck on,
re-prompt.

## Rulings

Fable rules when: the reviewer proposes work outside the spec's Non-goals;
the builder is at the cap; the builder asks. A ruling names the finding,
says accept / reject / narrow, gives the minimal accepted shape, and
includes the sentence the builder must paste into its next reviewer prompt
("Lead ruling: X is OUT OF SCOPE for <id>; do not re-raise it."). Record
each ruling in design.md under Rejected/Decisions before the PR.

## Gates the user holds

These are operator gates, and they are the only ones. Neither spec approval
nor the push is among them — Fable commits, pushes, and opens the PR off its
own review, unasked, on every branch this loop creates: the build branch,
the archive `chore/` branch, and a `chore/` branch amending the loop's own
rules. A push to `main`, a push to any branch this loop did not create, and
a force-push are NOT covered and still stop and ask.

- **Merge** — the user runs `env -u GH_TOKEN gh pr merge N --merge
  --delete-branch` (the session token lacks merge scope; never squash in
  project-mera). Stacked PRs merge in dependency order. Fable then pulls
  main (diff the main checkout's untracked spec copy against the merged
  version BEFORE removing it), removes worktrees, deletes branches.
- **Archive** — `openspec archive <name> --yes` on a `chore/` branch, then
  pushed and PR'd unasked like the build branch. Pushed to `main` DIRECTLY
  only when the user says "override push to main".
- **Retro signoff** — the retrospective items are quoted in the closing
  report; nothing is folded into this skill without the user's word.

## Exclusions from the commit

`BUILD-BRIEFING-*.md`, `HANDOFF-*.md`, `REVIEW-*-round-*.md`,
`PLAN-REVIEW-*-round-*.md`, `RETRO-*.md`, `CODEX-*.md` stay untracked.
Stage files by name. Check the staged list for env files or secrets before
committing.

## Pitfalls (each cost time once)

- A herdr prompt with backticks, `$(…)`, or parentheses breaks zsh quoting
  — write it to a file and `"$(cat file)"` it.
- Bare `echo ====` trips zsh globbing in compound commands; use `echo "--"`.
- `gh` with the session's `GH_TOKEN` cannot merge; hand the command to the
  user.
- The openspec config may point the learning-log line at a stub file;
  the canonical log is `~/Documents/Obsidian/Exocortex/knowledge/learning-log.md`.
- `openspec validate` passes a `## MODIFIED Requirements` delta for a spec
  that does not exist yet; `openspec archive` aborts on it. New spec names
  take `## ADDED Requirements` (#321).
- The reviewer will, by round 2–3, propose restart-safe/persistent
  guarantees for edge cases the design explicitly traded away. Rule early.
- Foreground `herdr … --wait` dies at the Bash 10-min cap and the wait is
  lost (#330, twice). Background it — see "Long agent turns" above (#321).
- qwen may stop at an "Always allow /tmp/*" permission dialog on its first
  temp-file write; the pane shows `blocked`. Read with `--source visible`,
  `herdr agent send-keys pi_build enter`. Have the briefing's sed write
  into the worktree root instead of /tmp to avoid it.
- Wowhead spell pages hide tooltips behind JS; ability-catalog grounding
  uses `nether.wowhead.com/tooltip/spell/<id>?dataEnv=1&locale=0` (#321).
