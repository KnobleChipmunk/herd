---
name: herd
description: 'Run the Herdr three-agent build loop — the lead (this session) orchestrates, pre-executes, and writes the openspec change, a local builder model (via the Codex CLI) builds it in a worktree, a Codex build reviewer reviews round-robin until clean, and the lead runs the `reviewer` skill (audience: ai) as the final pass, then collects a skill retrospective from every agent. Use when the user says "/herd", "herd #N", "run the herd on <issue|goal>", or asks to build an issue with the local builder via Herdr. Requires HERDR_ENV=1. Subagents are replaced by a pane below this one — Codex for plan review, claude for every other role. Models per role are in the Roster table.'
---

# Herd — the lead orchestrates, a local model builds in Codex, Codex reviews

This skill governs `/herd` runs. An operator may keep a separate loop for
delegated builds outside `/herd` (such as a `DEVLOOP.md`); where the two
differ (who authorizes the spec, the review-round cap, who pushes), this
skill wins inside a `/herd` run (operator ruling, #32).

One session — **the lead, this one** — talks to the user, writes the spec,
pre-executes it, rules on disputes, and does the final review. Everything
else runs in Herdr panes beside it and reports inward. Proven shape:
project-mera #280 → PR #325 (2026-08-19): 4 plan-review rounds, 5 review
rounds to clean. #310 → PR #330 (same day): post-mortem found 8 of 11 plan
findings avoidable upstream; rules marked **(#330)** come from it. #321 →
PRs #377/#378 (2026-08-25): lead pre-execution + byte-synced fences made
both builds byte-identical to the reference and both reviews clean in ONE
round; a mid-review shared-infra defect forced a prerequisite carve-out.
Rules marked **(#321)** come from that retrospective.

## Roster

Who plays each role is decided by two files, not by this table: the portable
role catalog `skill/herd.yaml` (roles, cards, what each evaluates, what it may
not do; no vendor names) and the machine's bindings file (#38; `herdsetup.py`,
#39). The table below is one operator's example profile
(`skill/profiles/example-claude-codex-pi.yaml`), and its local builder model
is theirs, not a requirement. `probe.py` still reads the table until #51
moves it to the bindings (#40), so an operator with other models edits both.

This table is the one place models are named; the rest of the skill says
"the lead", "the builder", "the plan reviewer", "the build reviewer". Change
a model in the machine's bindings file; keep this table synchronized for
`probe.py` until #51 moves it to the bindings.

| Role | Harness | Model | Pane name | Falls back to |
|---|---|---|---|---|
| Lead | Claude Code | Opus 5.5 (`claude-opus-5-5`; Fable before 2026-09-25) | — (this session) | — |
| Builder | Codex, profile `swift15` | Swift 1.5 27B, local (`swift15-codex` on llama-swap, a Qwen 3.8 fine-tune) | `codex_build` | Fallback builder |
| Fallback builder | pi | Swift 1.5 27B, local (`swift15-qwen3.8-128k:latest`) | `pi_build` | — |
| Plan reviewer | Codex | GPT-6 Astra (`gpt-6-astra`), high effort | `codex_plan_reviewer` | Build reviewer, Fallback reviewer |
| Build reviewer | Codex | GPT-6 Sol (`gpt-6-sol`), high effort | `codex_review` | Fallback reviewer |
| Fallback reviewer | Claude Code | Fable (`--model fable`), else Sonnet (`--model sonnet`); the aliases track the latest version | `claude_plan_reviewer` / `claude_review` | — |

Why the two reviewers differ: plan review is where the herd catches real
defects and runs one or two rounds per issue, so it gets the strongest
model; build review runs more often against builds that match the
pre-executed reference, so it gets the faster model and spends less of the
Codex subscription. The last column is the fallback chain, read by
`tools/probe.py`: the plan reviewer falls back Astra → Sol → Claude, the
build reviewer Sol → Claude. The fallback is never Opus: an
Opus reviewer checking an Opus lead is the same model checking itself. When
a fallback runs, say so in the PR.

Reviewers run in the Codex harness, not through pi. The #321 rule that ran
every role through pi began as an 08-23 trial for the builder only; the
reviewers moved with it and were never compared (2026-09-25).

The builder runs in the Codex harness too, on the same local model pi ran
(operator decision, 2026-09-30). On project-mera #482 and #380 it built five
PRs, up to 264 steps across 47 files, each byte-identical to the lead's
reference, at about three times pi's steps per minute. It needs
`mkbrief.py --builder codex_build` (the sandbox list and the step file,
#72), `--cd <worktree>` on start (herdr's `--cwd` does not reach Codex), and
Enter after `/new` (Codex opens a checkout picker). pi stays the fallback,
on the same model.

Load the `herdr` skill first; the `herdr` CLI is the authority on syntax.
`test "${HERDR_ENV:-}" = 1` or stop — this skill does not work outside Herdr.

## Before an unattended run — the sweep

The 09-21 run stopped twice on a missing API key and left three decisions
for the morning that could have been asked the night before. Before the
user leaves, and before the first dispatch:

1. **Queue.** List the issues in run order. Read each issue, its comments,
   and the code its spec will touch.
2. **Probe.** `python3 <herd>/tools/probe.py --log --repo <repo>` (see
   Topology), after `runlog.py add run-start`.
3. **Preflight.** `python3 <herd>/tools/preflight.py --need <issue>:<VAR> …`
   with every credential any queued issue needs (an eval run, an API call).
   It reports set or missing, never values. When the machine has a bindings
   file (`~/.config/herd/bindings.yaml`; an example is in `skill/profiles/`),
   preflight checks only the harnesses it binds, and the Probe step uses
   `python3 <herd>/tools/bindings.py ready --role <role> --record` for each loop
   role instead of `probe.py` (it honors the file's `probe_consent`); `probe.py`
   and the Roster table remain only for machines without a bindings file,
   until #51 (#38).
   A new machine gets its file from `python3 <herd>/tools/herdsetup.py
   assisted` (asks per role from what is installed; saves only on "y") or
   `from-example`; `herdsetup.py validate` lists what is missing without
   prompting (#39).
4. **Decisions.** For every issue, list each call only the user can make
   that the issue could hit: behaviour the guild would notice, a cost,
   budget or model tier, a data source, a scope cut ("part 1 only?"). And
   for each pair on a stack, whether issue N+1 changes something issue N's
   tests rely on (#422 turned #421's rejected payloads into accepted ones).
5. **Proposals.** `python3 <herd>/tools/proposals.py list` prints the
   librarian's pending proposals, most-recurring first. Each `open` one goes
   into the one message too: accept, reject, or leave open. Record each
   answer with `proposals.py set <stem> accepted|rejected`. Then commit
   everything `git status` shows under the herd repo's `proposals/`: the
   librarian's new files and `sync`'s applied marks from the last run, and
   today's answers. Put it on `chore/proposals-sweep-<date>`, and push and PR
   it unasked (the librarian and `sync` never commit).
6. **Ask once.** Put every decision, every missing credential, every
   coupling and every open proposal in ONE message. Record each answer with `runlog.py add
   decision-made --issue <id> --text "<answer>"`. An issue whose question
   is unanswered starts parked.

During the run, an issue that hits a decision nobody foresaw gets
`runlog.py add decision-needed --issue <id> --text "<the question>"` and is
parked; the loop moves to the next issue that does not depend on it. On a
linear stack every later issue depends on the parked one, so the stack ends
there: start a new stack from `main` with the independent issues, or stop if
none remain. The closing report opens with the `OPEN` lines of
`runlog.py status`.

## The assignment is the whole task (#459)

A run completes everything it was assigned, as if the operator is away
from the computer. The scope has grown as trust in the loop has built. When
an issue or task is delivered as several PRs and they are in scope, every
one of them is part of the run. "#N PR 1" names where the run starts, not
where it ends. #459 stopped after PR 1 with three PRs unbuilt, and the team
sat idle.

- **Confirm the scope once, at the start.** The invocation may have come
  from an autocomplete suggestion. The first message says which issues and
  PRs the run covers and where it ends. If that reading is not certain,
  the question goes into the sweep's one message. After that, no check-ins.
- **Stack, don't wait.** An unmerged PR is not a gate. Once PR N is pushed
  and open, cut PR N+1's branch from PR N's branch, measure its gates on
  that branch, and start its spec in the same turn. The operator merges
  the stack in order with `merge_stack.py`.
- **Stopping early needs a reason the operator owns:** a decision only
  they can make, an operator gate, or a stop condition the work itself
  names. Park that item (`decision-needed`) and carry on with whatever does
  not depend on it. If nothing remains, stop, and say so first in the
  closing report.
- **The retrospective and the closing report come once**, after the last
  PR of the assignment, not after each PR.
- **Accepted proposals are part of the assignment.** After the last PR of
  the issues, build each `accepted` proposal in the herd repo, test-first,
  as its own `chore/` PR (the herd's push exception covers a `chore/`
  branch amending the loop's rules), then `proposals.py set <stem> in-pr
  --pr <url>`. The operator merges it; the librarian's `proposals.py sync`
  marks it applied, and only then grades its prediction.

## Size tier — decide at pick time (#330)

The loop's fixed cost (spec + plan review + worktree + briefing + review +
final review) is 30–40 min. Say which tier the change is in the first
message to the user, and run that tier.

| | **small** | **full** |
|---|---|---|
| Shape | ≤3 source files, ≤~50 lines, no new mechanism — a table row, a guard, a message, a test re-point | anything with a new mechanism, a design choice worth recording, >3 source files, or a data/intake path |
| Spec | proposal (Grounded facts + Non-goals) + tasks.md; design.md only if a decision was actually made; spec delta still required by openspec | all four files |
| Pre-execution | The lead applies the tasks in a scratch worktree and runs the touched tests + mutations before plan review (#321) | same, plus the full suite once and EVERY mutation driven |
| Plan review | **one** round; the reviewer reads, re-derives the gates, and reasons — it never executes | rounds until APPROVE; the reviewer re-derives and challenges, it does NOT re-execute — the lead's pre-execution evidence is cited in the brief (#321) |
| Build | the builder builds from the byte-synced fences | the builder builds from the byte-synced fences |
| Review rounds | one round, cap 2 | cap 2 (+1 on ruling) — pre-execution moved the effort upstream (#321) |
| Final review | read the diff; run only the touched test files + the spec's grep gate; full suite only if the diff reaches a shared module | `reviewer` skill, direct, audience ai; diff the build against the pre-executed reference worktree first — byte-identical is the expected result (#321) |

Everything else (the spec post, worktree, briefing, retrospective, gates
the user holds, exclusions) is the same in both tiers.

## Topology

All panes live in the lead's tab. The lead keeps focus; every split uses
`--no-focus` and `--cwd` set explicitly. The model must be verified from
the pane STATUS LINE (`herdr agent read <name> --source visible`), never by
asking the model.

| Slot | Position | Agent | Name | Job |
|---|---|---|---|---|
| 0 | the calling pane | claude (lead) | — | user contact, spec, pre-execution, rulings, final review, commit |
| 1 | top-right of the lead | codex (builder model, local profile) | `codex_build` | builder, in its own worktree |
| 2 | bottom-right of the lead | codex (build reviewer model) | `codex_review` | build reviewer, round-robin with the builder |
| 3 | below the lead | codex (plan reviewer model) for plan review, else claude | `codex_plan_reviewer` / `opus_<role>` | stands in for ANY subagent the lead would spawn; one occupant at a time |

**Reuse rule.** Before creating a pane, `herdr agent list`. If a live agent
of the right kind already sits in the slot (same tab, right position per
`herdr pane layout`), rename it (`herdr agent rename <id> <name>`) and
reuse it. Otherwise split and start. Panes stay up across every issue and
PR of one assignment, and are shut down once, after the retrospective (see
"Shut down" under Roles).

**After a resume, find the live pane first.** A resumed session inherits
`HERDR_PANE_ID` and `HERDR_TAB_ID` from the session it resumed, and they can
name panes that no longer exist (#55: `w1:p2Z` inherited, `w1:p30` live, so
the first `--current` split failed). Before the first split or dispatch of
a resumed run, read `herdr pane list` for the lead's own pane (its agent is
`claude`, its cwd the repo) and its tab, and pass those IDs explicitly:
`--pane <live id>` instead of `--current`, and `--lead-pane <live id>` to
`mkbrief.py`.

Creating the panes, once (the Codex invocation is the pre-08-23 one, with
the roster's models):

```bash
herdr pane split --current --direction right --cwd "$PWD" --no-focus     # → slot 1 (read .result.pane.pane_id)
herdr pane split --pane <slot1> --direction down --cwd "$PWD" --no-focus  # → slot 2
herdr pane split --current --direction down --cwd "$PWD" --no-focus       # → slot 3
herdr agent start codex_build         --kind codex --pane <slot1> -- --profile <builder profile> --cd <worktree> -c check_for_update_on_startup=false
herdr agent start codex_review        --kind codex --pane <slot2> -- -m gpt-6-sol -c model_reasoning_effort=high
herdr agent start codex_plan_reviewer --kind codex --pane <slot3> -- -m gpt-6-astra -c model_reasoning_effort=high
```

The builder starts per build with `--cd` set to that build's worktree: restart
it (`/quit`, then `agent start`) for the next build. Status lines: the
builder's names its model and effort; a pi fallback builder
(`--kind pi -- --provider <provider> --model <model>`) reads
`(<provider>) <model> • medium`; the reviewers' Codex
shows the model and reasoning effort (its `tui.status_line` includes
`model-with-reasoning`). The Codex CLI lists models the ChatGPT login
refuses, so a listed model is not an available one. Before the first
review of a run, and again after any refusal or usage-limit error mid-run,
probe the roster and start each pane with the model it names:

```bash
python3 <herd>/tools/probe.py --log --repo <repo>   # one line per role; FALLBACK lines go to the run log
```

**Fallback reviewer** (roster's last row), in the reviewer's own slot:

```bash
herdr agent start claude_review --kind claude --pane <slot> -- \
  --dangerously-skip-permissions --model fable    # else --model sonnet
```

**Slot 3 for every other subagent role** (`opus_explore`, `opus_debug`, …):

```bash
herdr agent start opus_<role> --kind claude --pane <slot3> -- \
  --dangerously-skip-permissions --model opus \
  --append-system-prompt-file "$HOME/projects/fixing-smartass-opus-5/sr_opus_5_system_prompt.md"
```

The slot holds one agent at a time. Same kind, next role: rename and
re-prompt; an evaluator (plan reviewer, build reviewer, QA) first gets a
fresh context (`/new`, or a restart), as its card requires. Different kind: `herdr agent prompt <name> "/quit"` (pi/codex)
or `"/exit"` (claude), then `agent start` the replacement in the same
pane. Several agents of one kind can be live at once — always target by NAME, never
by kind.

Prompts to any pane agent: write multi-line or quote-heavy prompts to a
file and `herdr agent prompt <name> "$(cat file)" …`. Replies: have the
agent write a file and read that — pane reads cut long output off.

**Long agent turns run backgrounded (#321).** Dispatch with `python3
<herd>/tools/dispatch.py <agent> --file <prompt>` as a BACKGROUND task: it
sends the prompt and waits until the agent settles, treating Herdr's `timed
out waiting for agent status` as "still working", so one call replaces the
prompt-then-wait pair. Let the completion notifications drive the loop; never
poll in a foreground loop.

**Plan-reviewer brief (#330, #321).** Tell it the tier and that the plan
was ALREADY pre-executed — name the scratch worktree (read-only for it)
and the observed evidence (RED tail, GREEN counts, mutation kills, gate
lines). Direct its effort at what execution cannot catch: re-derive the
fixture arithmetic independently (a wrong expected value that the
implementation reproduces passes tests AND mutations), challenge catalog
membership / design conventions / boundary cases, check every text anchor
resolves uniquely at HEAD, every gate is a measured literal with its
baseline named, and blank-line separation is stated for every insert.
Apply the authority-rule check in `skill/cards/plan-reviewer.md` whenever
a rule is extracted, reformatted, or rewritten.
Tell it where its line is: it may read files and git blobs, do its own
arithmetic, inspect code, and run the read-only fence
projection command in `skill/cards/plan-reviewer.md` against the pinned base;
it never applies the plan, imports the plan's code, or runs its tests or
mutations. The lead's pre-execution is the execution evidence.
Have it write findings to `PLAN-REVIEW-<id>-round-N.md` in the repo root
and reply with only the path plus its verdict line (APPROVE / REVISE).

**Re-review prompts are disposition-numbered (#321).** Every round after
the first opens with the previous round's findings in the REVIEWER'S OWN
numbering, each marked FOLDED / NARROWED / REJECTED with one line of
evidence (what was re-run, what it printed), then instructs: "re-read the
four files fresh and sweep for anything stale or newly contradictory —
including what the revision itself broke." In #321, two of ten rounds
found defects the fold introduced; that sweep instruction is what catches
them. A fold that changes the model (what a function returns, which inputs it
accepts, a default) carries an outcome checklist in its disposition, one row
each: (1) the normal boundary, (2) the late boundary, (3) the absent-state
behaviour, and (4) every mutation and killer pair it moved. A spec claim about
a helper ("never returns 0") holds only when it follows every branch of the helper,
and its wording is bounded to the encoding actually observed, without growing
the change into defensive parsing (#460, #333).

**Never** use the `Agent` tool in this skill. Every subagent is the slot-3 pane.

## Roles and hand-offs

Each role's contract is its card in `skill/cards/` (the lead's five roles share
`cards/lead.md`). At dispatch, `python3 <herd>/tools/team.py assign <role>
--issue <id> --session <name> --candidate <commit> --scope <files> --checks
<gates>` records the assignment and must print `recorded`. Then, and after a
compaction, `team.py packet <role> --issue <id>` gives a session its card,
current step, return route, independence rule, and the binding and candidate
recorded at dispatch (an explicit `--candidate <commit>` names a newer one).
Before dispatch, `team.py gate dispatch --issue <id>` must print `ok`; before
each review round, `team.py gate review --issue <id>`; and a review file must
name its candidate (`team.py gate review-file <path>`). The gates check
structure only (#40).

**Lead (orchestrator + strategist + final reviewer).**
- Picks the target with the user (or takes the one given). Ranks by:
  bug > enhancement; data-loss/silent-failure first; bounded scope; red
  test already sketched.
- Writes the openspec change (`openspec/changes/<name>/`: proposal with
  Grounded facts, design, spec delta, tasks.md with tests first). Every
  claim cites file:line it actually read. A fact about live data is
  queried through the consumer's own code path: find the function the
  change reads the data through, reproduce its actor selection and
  filters, and report counts per selected actor, labelled per-actor or
  combined, never a broader table standing in for it (#333 queried a raw
  table, not the fetch function the change reads through, and plan review
  overturned the model). Sample the failure mode as well as clean
  examples; a clean example cannot show what an error looks like.
  `openspec validate <name>` passes — and note validate is WEAKER than archive: a delta for a spec
  name with no file under `openspec/specs/` must be headed `## ADDED
  Requirements`, or the archive aborts later (#321).
- Before generating fences, complete the requirement table from `openspec/config.yaml`
  against the issue and design, including a skill/card caller for each new command.
- **Pre-executes the spec before plan review (#321).** In a scratch
  worktree cut from HEAD: apply every tasks.md instruction literally (a
  script extracting the fences, then the anchored edits), observe RED,
  reach GREEN, run every gate, drive EVERY mutation and record the killer
  test observed. Defects found here (wrong anchors, wrong expected
  values, contract tests the plan missed) are folded into the spec before
  any reviewer sees it. After every fold round, RE-execute what changed
  and re-drive affected mutations. Before pre-execution, grep the repo for
  an existing implementation of every helper the plan adds or extracts
  (CLAUDE.md, One copy), and record each match with its disposition in the
  proposal: reuse, hoist in a prerequisite PR, or exclude with a stated
  behavioural difference. #502 found two duplicates after plan review, and
  each cost a prerequisite PR and a rebuilt stack.
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
  its baseline (#321).** A grep gate is written as `python3
  <herd>/tools/gates.py count '<text>' <path>…`, never raw `grep -c`: it is
  literal, a directory counts only its `*.py` files, zero exits 0, and it
  counts the same in the builder's shell as in the lead's (#459). Run the exact commands the builder will run and
  paste the literal last lines. Gates are "identical to <baseline>" or
  "<baseline> + the delta you name", never absolute, and they are compared
  by counts with `tools/gates.py match` (write the counts, not pytest's
  whole last line; warnings and wall time do not count) — and when the change
  has a prerequisite, the baseline is the PREREQUISITE's measured state,
  re-measured whenever the prerequisite changes. Include the full-suite
  wall time so the builder does not read a 5-min run as a hang. The
  full-suite baseline is RUN at the base, in its own clean worktree cut from
  the base commit (`base-<id>`), never in the pre-execution tree or any
  worktree you will edit: the suite reads files at run time, so an edit
  during the run contaminates it (#459-4, #334). It runs in the background
  at the start of pre-execution, and its line says
  `(measured, <seconds> s)`: never the
  after count less the new tests (#482). `mkbrief.py` refuses a gates
  section without that mark, or with `(derived`.
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
  is the authorization; the user does not hold a gate here. The lead posts the
  spec summary — the defect, the fix, what was deliberately left out, the
  plan-review record, the gates — and in the SAME turn creates the
  worktree and prompts the builder. Do not end a turn on the summary
  waiting for "go". The user redirects mid-build if they want something
  different. Two things still stop an issue: a decision only the user can
  make (a product call, a behaviour the guild would notice), and anything
  in the operator gates below. With the user present, say which one and
  wait. Unattended, park that issue and carry on (see the sweep).
- Creates the build worktree, writes the builder's step file with
  `python3 <herd>/tools/herdtool.py <plan> emit-steps <worktree>/STEPS-<id>.json`
  (exact bytes; a fence cannot carry a mid-line fragment exactly, #482), and
  generates the briefing after APPROVE with
  `python3 <herd>/tools/mkbrief.py <id> <worktree> <branch> <pinned-base-sha>
  <change-name> <allowed-files-file> --lead-pane <live-pane-id> --builder <pane name>`,
  then prompts the builder. A `codex*` builder gets the sandbox escalation list. Put every measured gate, including the full-suite count,
  mutation names and fence step count, in tasks.md's single `## 0. Gates`
  section. The generator copies that section; it takes no separate gate file.
  After any spec amendment, regenerate the briefing from tasks.md before
  dispatching the next round. Keep the original base SHA pinned.
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
  number and the merge command. When the session's `GH_TOKEN` cannot
  write and the credential manager's dialog cannot answer headless, push as
  `env -u GH_TOKEN git -c credential.helper='!gh auth git-credential' push
  -u origin <branch>` — a `gh` OAuth login with `repo` scope answers
  without a prompt. Open the PR the same way
  (`env -u GH_TOKEN gh pr create --base main --head <branch>`), and verify
  `baseRefName` on the created PR before reporting it.
  This covers every branch the loop creates and owns — the build branch,
  the `chore/` branch carrying the openspec archive, and a `chore/` branch
  amending the rules the loop itself follows. The three exceptions that
  still stop and ask, review or no review: a push to `main` or to any
  branch this loop did not create, a force-push, and anything else in the
  operator's Hard Constraints.
- **The full suite runs once per build-state, by the builder (#330):** after the
  last fold, never while one is pending; `python3 <herd>/tools/gates.py suite-ok
  --issue <id>` says whether it may run (`fold start|done` marks a fold; a
  ruling's reference mutation reopens it once with `--ruling`). Its
  literal tail lives in the handoff (the lead's pre-execution run of the
  suite is separate and earlier). codex_review and the lead's final pass
  run the touched test files plus the grep gate; either re-runs the full
  suite only when the handoff's tail is missing or does not match the gate
  expectation. The plan reviewer runs nothing (see its brief).
- **Retrospective, after all agents report DONE (#321).** Once the final
  review of the assignment's LAST PR is clean and that PR is pushed, and
  before the closing report:
  prompt EACH live herd agent (`codex_build`, `codex_review`,
  `codex_plan_reviewer`) with exactly — "What would you improve in the herd
  skill after this run? Reply with concrete, numbered items grounded in
  what you actually hit; write them to RETRO-<id>-<yourname>.md in the
  repo root and reply with only the path." The lead adds its own items the
  same way, as `RETRO-<id>-lead.md`. The librarian files every item into the
  friction ledger after the run (see "After the run"); the closing report
  lists the retro paths, it does not quote them. Nothing reaches the skill,
  the briefings, or the repo without the user's explicit signoff, and
  nothing is dripped mid-loop. RETRO-*.md files stay untracked like the
  review files.
- **Shut down, after the retrospective.** Once every `RETRO-*.md` has
  landed, and before the closing report, end each herd agent the run
  started or reused: `herdr agent prompt <name> "/quit"` (pi, Codex) or
  `"/exit"` (Claude). Confirm with `herdr agent list` that none of them is
  still listed, and read each pane (`herdr pane read <pane> --source
  visible`) for the shell prompt and the resume command the agent prints on
  exit. Then `herdr pane close <pane>` for each. Close only the panes of
  this run's slots in the lead's tab: never the lead's own pane, and never
  an agent in another tab. The closing report lists each agent's resume
  command, so the operator can still reopen a session after the panes are
  gone.

**codex_build (builder).** Works ONLY in its worktree. Tests first, red,
then implementation, then gates (pytest + ruff + mypy + the spec's grep
gate), then the mutation drives. Writes `HANDOFF-<id>.md`. Then:
1. Prompts `codex_review` with the worktree path, spec path, handoff path,
   round number, and the sentinel contract (via the sed'd per-round
   prompt file). `--wait --timeout 540000`, re-waiting on timeout.
2. Reads the review file; on `FINDINGS: <n> (spec)` records friction and
   sends BLOCKED in that round (see Rulings); otherwise fixes every
   CONFIRMED finding; re-runs ALL
   gates; updates the handoff; sends the next round.
3. Repeats until the reviewer writes `REVIEW CLEAN`. Cap **2 rounds**
   (+1 on a ruling); at the cap it sends the lead `BLOCKED:` with the open
   findings and stops.
4. Only then prompts the lead: `DONE: build for <id> — reviewer clean after
   N rounds — handoff at <path>`.
The builder never contacts the lead between dispatch and that DONE except
`BLOCKED:`. It never commits, pushes, or leaves the worktree.

**codex_review (build reviewer).** Reads spec + handoff, reviews the worktree diff
against the branch base named in its prompt, runs `tools/fencecheck.py`
(the prompt carries the exact command) instead of checking fences by eye,
runs the **touched** test
files itself (not the full suite — the handoff carries that tail
verbatim), reports only CONFIRMED defects with file:line and an exact
fix, writes `REVIEW-<id>-round-N.md`, ends with `FINDINGS: <n>`,
`FINDINGS: <n> (spec)` when any unresolved confirmed finding is in a byte-exact
fence (see Rulings), or `REVIEW CLEAN`. A clean round still lists what it ran and what it checked
(commands + last lines) — a file that is only the sentinel is not
evidence (#330). It talks only to the builder, and contacts the lead only to
sign off: `REVIEW CLEAN for <id> after N rounds`.

## The loop, end to end

```
lead:  pick + tier → measure gates → spec (text anchors)
     → PRE-EXECUTE in a scratch worktree: RED → GREEN → gates → all mutations,
       fold defects, regenerate fences, assert fence==file
     → codex_plan_reviewer (small: 1 round; full: until APPROVE; re-derive, never re-execute;
       disposition-numbered re-review prompts; re-execute after every fold)
     → post the spec summary AND dispatch, same turn: worktree + briefing → prompt codex_build
       (prerequisite found mid-review? carve it out, loop it first, stack the branch)
codex_build: tests red → impl → gates → mutations → HANDOFF → review round 1
codex_review: REVIEW-round-1 (FINDINGS: n; spec finding → builder BLOCKED → lead ruling)   ┐
codex_build: fix → gates → HANDOFF → round 2   ┘ … until REVIEW CLEAN (cap 2, +1 on ruling)
codex_review: "REVIEW CLEAN" → lead;  codex_build: "DONE: …" → lead
lead:  diff build vs pre-executed reference → /reviewer (direct, audience: ai)
       findings? → builder fixes → gates → reviewer re-signs → DONE again → re-review the delta
       clean?    → commit on branch → push → open PR, same turn
       → more PRs in the assignment? cut the next branch from this one → spec → the loop again
       → RETRO (after the last PR): ask all three agents "what would you improve in the skill?"
       → SHUT DOWN: /quit (or /exit) each herd agent, confirm it left `herdr agent list`, close its pane
       → accepted proposals: each built as its own herd `chore/` PR, `proposals.py set <stem> in-pr --pr <url>`
       → closing report: `runlog.py status` OPEN lines + PRs + the merge_stack.py command + "the librarian starts itself after --apply" + each agent's resume command + `proposals.py list`
       (user runs merge_stack.py, then --apply: merge in order, pull, clean up)
       → openspec archive on a chore branch, pushed and PR'd unasked
```

## Worktree and environment (per build)

```bash
git -C <repo> worktree add -b fix/<issue>-<slug> <repo>__worktrees/<slug> <base>   # <base> = main, or the prerequisite branch when stacked
cp -r <repo>/openspec/changes/<name> <repo>__worktrees/<slug>/openspec/changes/   # spec is committed with the PR
python3 <herd>/tools/runlog.py add worktree-created --repo <repo> --issue <issue> \
  --worktree <repo>__worktrees/<slug> --branch fix/<issue>-<slug>   # cleanup removes only what the log names
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

## Mutation drives — `tools/mutate.py` (#321)

Specs name mutations and killer tests in tasks.md section 3; the mechanics
are always the same, so nobody hand-writes a driver. The lead
(pre-execution, from its plan module: `herdtool.py <plan> mutate <tree>`)
and the builder (`mutate.py <tasks.md> <worktree>`) run the same engine;
the build reviewer re-drives two of its own choosing with `--scratch`,
which works on a copy and never touches the build.

What the engine enforces: one mutation at a time; an anchor that does not
occur exactly once voids the drive (VOID); `__pycache__` cleared across the
whole tree and pytest run with `-B`, so stale bytecode cannot fake a
survivor; the file restored after EVERY drive, and the tree's git status
checked unchanged afterwards (TREE CHANGED catches a test with side effects
or a failed restore); it refuses to start while pytest is running in the
tree. A SURVIVED result means the test or the mutation is wrong — fix the
spec, never skip the drive.

## Tickets (`tools/tickets.py`)

A question goes as a message (`herdr agent prompt`); work someone must own
goes as a ticket. `tickets.py create --title <t> --to <owner> --by <you>
[--parent <issue>]` opens one; its owner `claim`s it, then `close`s it with
a reason (`no-follow-on`, `denied`, `canceled`, `superseded`, or
`escalation --target <who>`), `block`s it `--on <who>`, or `handoff`s it `--to <next owner>`,
which closes it and opens the successor in one write. Record each gate
with `check <id> --name <n> --status pass|fail|not-checked|blocked|omitted
[--candidate <commit>]` (a pass names the candidate it was measured on);
`page <id>` writes the ticket's page to `<git common dir>/herd/tickets/`.
An omitted, blocked or unchecked gate is never a PASS (#36, #37).

## Run log (`tools/runlog.py`)

The run's durable record is `<git common dir>/herd/run-log.jsonl`: one JSON
line per checkpoint, appended, shared by every worktree, never committed.
It replaces the hand-edited state file. After a compaction or a crash, the
lead recovers from `runlog.py status` and live git/gh, not from memory.
A crashed run stays open: resume it by appending as usual, or end it with
`runlog.py close --reason "<why>"`. A second `run-start` is refused while
a run is open, and `status` keeps listing decisions an earlier run left
open, marked with that run's id (#32).

The lead records each checkpoint as it happens (`runlog.py add <kind>
--issue <id> …`): `run-start` first, then per issue `spec-approved` (with
`--tier`), `plan-review` (with `--round` and `--verdict`),
`worktree-created` / `scratch-created` / `branch-created` for everything
the loop creates, `dispatched`, `review-round` (with `--round` and
`--verdict`), `ruling`, `gate-miss` (a briefing baseline the builder did not
reproduce), `lead-finding` (each finding the lead's final pass caught after
the reviewer signed off), `done`, `blocked`, `pr-opened` (with `--pr` and
`--branch`), `fallback` whenever a roster fallback runs, `decision-needed` /
`decision-made`, `session` (with `--agent`, `--role` and `--outcome`
resumed | fresh | failed | unknown, whenever the lead starts, reuses or
recovers an agent), and `run-end`. These are the herd ledger's columns: a
checkpoint the lead skips is a count the ledger gets wrong.
Agents add `friction` lines themselves; their briefing and prompt carry the
command. `status` shows each issue's progress and what is still open;
`created` is what post-merge cleanup may remove, and nothing else;
`friction` is the input to the post-run review, which the librarian
(Hermes) reads after the run rather than during it.

## After the run — the librarian

Post-mortem belongs to the librarian, not to the lead's last turn: the lead's
context may not survive the night, and the librarian runs on the local model
with nothing else waiting. `merge_stack.py --apply` starts it: when the
merges, the pull and the cleanup all succeed, it launches Hermes with the
`herd-librarian` skill (versioned in this repo at `hermes/herd-librarian/`)
in the background, once per run, and prints where its report goes; the run
log records the start, so a re-run does not file everything twice.
`--no-librarian` skips it. It appends one row per build to the
vault's `herd-ledger.md`, files every friction line and retro item under a
class in `friction-ledger.md`, and writes a proposal to `proposals/` when a
class reaches two events. It commits nothing; a proposal becomes a change to
this skill or its tools only through a PR the operator merges. Each proposal
carries a `Status:` line (`tools/proposals.py`): `open` until the sweep's
question settles it, `accepted` or `rejected`, `in-pr <url>` once the lead
opens its PR, and `applied` when the librarian's `proposals.py sync` sees
that PR merged. The closing report ends with the merge_stack command and the
`proposals.py list` output.

## Monitoring

At `run-start`, recorded with the run's tab (`runlog.py add run-start --tab
"$HERDR_TAB_ID" ...`), the lead starts the attention watcher as a background task:
`python3 <herd>/tools/attention.py watch --repo <repo>` (add `--ntfy <url>` to
also push to a phone; a second watcher for the same repo exits at once). It
raises a Herdr notification once per open decision, permission dialog,
batch of ready PRs, and stalled run, retries one Herdr drops, and never
pages the operator for a worker block the lead has not yet ruled on. When
an issue is deliberately waiting, say so with `runlog.py add wait --issue
<id> --reason resource|peer|environment|auth|rate-limit|scheduled|other`, so
it is not read as a stall. The operator's view of every agent and issue is
`python3 <herd>/tools/attention.py monitor --repo <repo>`, run in any pane;
both read the current run's tab from its `run-start` (#33, #34). Each Claude Code pane's
context use shows in the monitor once `python3 <herd>/tools/context_collector.py
install` has wrapped the status line (it backs up `settings.json` first, and
`uninstall` restores it); other harnesses show `context unknown` (#41).

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

**Finding in a byte-exact fence.** The build reviewer tags each such confirmed
finding "in the fence", keeps it unresolved (never FOLDED), and ends the round
with `FINDINGS: <n> (spec)`, counting all unresolved confirmed findings.
The builder records friction and sends BLOCKED in that same round, without
editing the fence or spec. If the lead rejects the finding, the builder passes
the ruling to the next review without waiting for a fold, preserves the
unchanged build-state evidence, and records the ruling in the handoff.
For an accepted fence change, the lead marks `gates.py fold start --issue <id>`,
folds the accepted fix into the reference,
re-runs the affected tests and mutations, and runs `python3 -B
<herd>/tools/fencecheck.py <tasks.md> <reference> --base <pinned-base-sha>
--rebase REBASE-<id>-round-N.md`: the report names every fence the fold
made stale, with its diff and, for a whole-file fence, the regenerated
body, so the fold reaches every fence it touched in the same round. It then
regenerates the fences and verifies byte parity (the same command, now
`PROJECTION OK` and no report). When the fold changes a test fence, the lead runs that test file against the pinned base in scratch
and records its new RED tail and `gates.py match` line in section 0 before
re-applying the implementation, so section 0 and the builder's carried RED
never silently disagree. It then installs any regenerated test fences in the build worktree,
regenerates the briefing from the amended tasks.md (`mkbrief.py`, same pinned
base SHA), then marks `gates.py fold done --issue <id>`. The builder
re-applies the affected implementation files, re-runs all gates (including the full suite once
for the new build-state after `gates.py suite-ok --issue <id>`), updates the
handoff and resumes review within the cap authorized by the lead ruling. A pending reference fold prevents REVIEW CLEAN and DONE.

The lead rules when: the reviewer proposes work outside the spec's Non-goals;
the builder is at the cap; the builder asks. A ruling names the finding,
says accept / reject / narrow, gives the minimal accepted shape, and
includes the sentence the builder must paste into its next reviewer prompt
("Lead ruling: X is OUT OF SCOPE for <id>; do not re-raise it."). Record
each ruling in design.md under Rejected/Decisions before the PR.

## Gates the user holds

These are operator gates, and they are the only ones. Neither spec approval
nor the push is among them — the lead commits, pushes, and opens the PR off its
own review, unasked, on every branch this loop creates: the build branch,
the archive `chore/` branch, and a `chore/` branch amending the loop's own
rules. A push to `main`, a push to any branch this loop did not create, and
a force-push are NOT covered and still stop and ask.

- **Merge** — the user runs `python3 <herd>/tools/merge_stack.py --repo
  <repo>` to see the plan, then again with `--apply`. It merges every PR the
  run opened, in order, with a true merge (never squash),
  stopping at the first one that does not target main or will not merge;
  pulls main, removing an untracked spec copy only when it is byte-identical
  to what merged; and removes the worktrees and branches the run log says
  the run created, for merged issues only, never forcing one with
  uncommitted work (a scratch reference is forced only when every change it
  holds is already on origin/main, and otherwise kept with the differing
  files named); then it starts the librarian in the background.
  Re-running it is safe, so a crash half-way is fixed by running it again. One PR by hand is still `env -u GH_TOKEN gh pr merge N
  --merge` when the session token lacks merge scope; not `--delete-branch`,
  which fails on the local branch while its worktree exists.
- **Archive** — `openspec archive <name> --yes` on a `chore/` branch, then
  pushed and PR'd unasked like the build branch. Pushed to `main` DIRECTLY
  only when the user says "override push to main".
- **Retro signoff** — the retrospective items are quoted in the closing
  report; nothing is folded into this skill without the user's word.

## Exclusions from the commit

`BUILD-BRIEFING-*.md`, `HANDOFF-*.md`, `REVIEW-*-round-*.md`,
`PLAN-REVIEW-*-round-*.md`, `RETRO-*.md`, `CODEX-*.md`, `ALLOWED-*.txt`,
`STEPS-*.json` and the builder's `SCRATCH-*` files stay untracked.
Stage files by name. Check the staged list for env files or secrets before
committing.

## Pitfalls (each cost time once)

- A herdr prompt with backticks, `$(…)`, or parentheses breaks zsh quoting
  — write it to a file and `"$(cat file)"` it.
- Bare `echo ====` trips zsh globbing in compound commands; use `echo "--"`.
- When the lead's shell is zsh, a variable is not word-split:
  `R="python3 tools/runlog.py"; $R add …` runs a command literally named
  `python3 tools/runlog.py`, and the error does not point at the missing
  run-log entry. In any shell, call every tool by its full path on the
  command line (#33, #333).
- Quote every heredoc, `<<'EOF'` and never `<<EOF`: an unquoted heredoc runs
  the backticks and `$(…)` in its body (#333).
- Background a herdr prompt with the Bash tool's background mode, never
  `&`: a `&` job sends no completion notification (#33).
- Chain a gate into the step it guards with `&&`, never `;`: on #380,
  `team.py gate dispatch …; herdr agent prompt …` printed the refusal and
  dispatched anyway.
- When the session's `GH_TOKEN` lacks merge scope, `gh` cannot merge; hand
  the command to the user.
- The openspec config may point the learning-log line at a stub file;
  the canonical log is `$HERD_VAULT/knowledge/learning-log.md`.
- `openspec validate` passes a `## MODIFIED Requirements` delta for a spec
  that does not exist yet; `openspec archive` aborts on it. New spec names
  take `## ADDED Requirements` (#321).
- The reviewer will, by round 2–3, propose restart-safe/persistent
  guarantees for edge cases the design explicitly traded away. Rule early.
- Foreground `herdr … --wait` dies at the Bash 10-min cap and the wait is
  lost (#330, twice). Background it — see "Long agent turns" above (#321).
- A pi fallback builder may stop at an "Always allow /tmp/*" permission dialog on its first
  temp-file write; the pane shows `blocked`. Read with `--source visible`,
  `herdr agent send-keys pi_build enter`. Have the briefing's sed write
  into the worktree root instead of /tmp to avoid it.
- Wowhead spell pages hide tooltips behind JS; ability-catalog grounding
  uses `nether.wowhead.com/tooltip/spell/<id>?dataEnv=1&locale=0` (#321).
