# Team design — roles, bindings, independence (#31)

Status: decision, 2026-09-27. Source: `docs/openrig/ROADMAP.md` (consensus v4,
rows TD, U1, U5, T1–T7, 3, 4, 7a). This document gates #40 (role cards and
`herd.yaml`) and fixes the contracts #38 (resolver) and #39 (setup) implement.
It changes no code.

## 1. Roles are not seats

A **role** is a responsibility: what it does, when it runs, what it may touch,
and whose work it may not judge. A **seat** is a live agent session in a pane.
A **binding** says which harness, provider, model and login plays a role on
one machine. A role can exist without a seat of its own (the lead holds
several), and one seat can hold different roles over time (the specialist
slot). A binding never grants a permission the role does not have.

## 2. Role catalog

"Own session" roles get their own card, because their session is dispatched with that card, its packet and its
evidence, not the whole team's cards. "Lead-held" roles are sections of one lead card, because one session
holds them all.

| Role | Runs in | Activates | Produces | May not |
|---|---|---|---|---|
| Orchestrator | lead-held | always | routing, rulings, one consolidated report to the operator (what was exercised, what is unchecked) | hand off operator gates |
| Architect | lead-held | intake; cross-ticket findings | decisions in `design.md`: interfaces, invariants, non-goals, affected tickets | change scope or product behavior without the operator |
| Planner | lead-held | every ticket | the openspec change, pre-executed; byte-exact fences | skip pre-execution on the full tier |
| Product intake | lead-held | operator input; dogfood findings | tickets with evidence, ranked; new goals routed to the operator | self-approve new scope |
| Release prep | lead-held | after final review | commit, normal push and PR on branches this loop created, release notes where relevant | merge, publish; push to `main`, to a branch the loop did not create, or force-push without the operator |
| Builder | own session | dispatch | implementation in its worktree; the handoff | commit, push, leave the worktree |
| Plan reviewer | own session | every spec | `PLAN-REVIEW-<id>-round-N.md`, APPROVE / REVISE | execute the plan or its tests |
| Build reviewer | own session | builder's round | `REVIEW-<id>-round-N.md`, FINDINGS / REVIEW CLEAN | edit the candidate |
| Test QA | own session (specialist slot) | chosen at planning by journey/risk; skip reason recorded | promised vs observed, unchecked list, verdict on a frozen candidate | repair the candidate it certifies |
| Dogfood | own session | only when the operator authorizes a session (20 min, safe environment) | findings as tickets with evidence | act as a build gate; start itself |
| Product designer | own session (specialist slot) | UI or interaction ambiguity, before the plan freezes | flows, states, acceptance examples | count as the independent evaluator of a candidate it shaped |
| Librarian | own session, after the run | `merge_stack.py --apply` | ledger rows, friction classes, proposals | commit; change the skill |

Not roles (rated 2 or less in the consensus): a standing orchestrator peer, a
separate architect or release-manager seat, a continuous dogfood seat, a
separate PM rig. The watcher (#33) is a script, not a role. When a large or
contested plan needs a second look at coordination, the lead may select a
bounded coordination audit in the plan-review slot: it returns a file and
never dispatches, cancels or reprioritizes work.

### Role contracts

Every role card carries eight fields: purpose, inputs, outputs, activation,
scope, evidence, authority, and exclusions. The table gives purpose,
activation, outputs and the main exclusion. The rest is settled here, either
by inheriting today's contract in `skill/SKILL.md` (this decision and §4 win
where they differ) or by the rules below.

| Role | Inputs | Scope and authority | Evidence and return route |
|---|---|---|---|
| Orchestrator, Architect, Planner, Product intake, Release prep | the operator's goal, issues and comments, the code the spec touches, dogfood findings | inherits the lead rules in SKILL.md "Roles and hand-offs" and "Gates the user holds" | the openspec change with Grounded facts, pre-execution evidence, rulings in design.md; reports to the operator |
| Builder | the approved spec, its briefing, one worktree | inherits "pi_build (builder)": only its worktree and allowed files; tests red first; no commit or push | the handoff (gates, full-suite tail, mutation log, unbacked claims); returns DONE or BLOCKED to the lead |
| Plan reviewer | the spec files, the lead's pre-execution evidence, git blobs | inherits "Plan-reviewer brief": reads and reasons, never executes the plan or its tests | `PLAN-REVIEW-<id>-round-N.md`, APPROVE / REVISE, to the lead |
| Build reviewer | the spec, the handoff, the candidate diff against its named base | inherits "codex_review (build reviewer)": runs fencecheck, the touched tests and two mutation re-drives on a scratch copy (`mutate.py --scratch`); edits nothing | `REVIEW-<id>-round-N.md`, FINDINGS / REVIEW CLEAN, to the builder; sign-off to the lead |
| Test QA, Dogfood, Librarian | see the rules below | see the rules below | see the rules below |
| Product designer | the approved product intent and the named interaction ambiguity | only the design scope the lead authorized; new user-visible behavior still goes to the operator | flows, states and acceptance examples, consumed by the Planner and QA |

The rules below complete Test QA, Dogfood and the Librarian, and add what the
consensus agreed beyond today's contracts.

- **Orchestrator** also owns intake, role selection for each ticket (including
  whether QA is selected, with the reason when it is not), QA dispositions, and
  dogfood triage. Its report says which promised outcomes were exercised and
  which remain unchecked. It keeps pre-execution and the operator gates.
- **Architect** also owns what dogfood findings mean for the design.
- **Test QA.** Inputs: a frozen candidate (commit or tree fingerprint) and an
  isolated environment. It runs after the build review is clean and before the
  lead's final review. It may create isolated fixtures; it may not repair the
  candidate. Output: candidate id, environment, expected vs observed,
  reproduction, unchecked coverage, verdict. NOT CHECKED or BLOCKED is never
  PASS. A changed candidate renews the affected review and QA evidence.
  In-scope defects go back to the builder under the existing round cap and
  ruling policy; broader ones become new tickets. No merge authority.
- **Dogfood.** Eligible only for a product with a usable surface and a safe
  environment (web app, CLI install or upgrade, a library through its public
  API, an installed skill on an authorized task). Input: an identified
  released or installed build, approved test accounts and data. It never
  installs or updates the operator's live system on its own. Findings go to
  the lead's product intake; new scope goes through the sweep.
- **Librarian** keeps its existing guidance (`hermes/herd-librarian/`). It is
  bound to any available harness; where none can run it, the run records its
  post-run work as a pending obligation instead of dropping it.

### Current-step packet and resolved assignment

Every dispatch or recovery hands the session a packet: role, current step,
candidate, required evidence, return route (who receives the output), and the
independence requirement. At dispatch the run stores the resolved assignment:
role + binding + session + candidate + scope + selected checks.

`herd.yaml` (#40) declares, per role: capability requirements, activation and
skip conditions, author/evaluator exclusions, allowed operations, and time and
cost limits. Each constraint is advisory until a tool enforces it, and says
so.

## 3. Seats

Four seats, as today: the lead; the builder slot; the build-review slot; the
specialist slot below the lead. The specialist slot holds one role at a time
(plan reviewer, QA, designer, or any lead-requested helper). A role change
assigns the new role's contract and scope; a renamed or reused pane never
keeps the previous role's authority or erases what it authored. Designated
independent evaluation always starts from a fresh non-author context,
whatever the pane, harness or model. The number of seats is a
deployment choice. `herd.yaml` defines roles, not a seat count.

## 4. Independence policy

Two separate rules:

1. **Evaluator separation, hard.** A role doing independent evaluation (plan
   review, build review, QA) must not be the author of what it judges, and must
   start from a fresh context. This holds regardless of vendor or model. The
   lead's pre-execution makes it an author, so the lead's own final pass never
   counts as the independent evaluation.
2. **Model diversity, recommended.** For each author/evaluator pair, a
   different model is recommended, warned about when missing, and recorded in
   the run as `same`, `different` or `unknown`. It is never forced, unless the
   project's policy requires it. A same-model evaluator in a fresh non-author
   session is a valid setup with reduced diversity, and the run says so.

This replaces the rule "never Opus reviewing Opus": that rule is rule 2 for one
model.

## 5. Binding contract

The portable role catalog (section 2, later `herd.yaml`) ships with herd and
names no vendor. Each machine keeps its own bindings file in the platform
config directory (`$XDG_CONFIG_HOME/herd/bindings.yaml`, default
`~/.config/herd/bindings.yaml`). It is never committed.

A binding is the full identity of what plays a role:

| Field | Meaning |
|---|---|
| `harness` | the agent CLI (e.g. Claude Code, Codex, pi) |
| `provider` | where the model is served (vendor login, local server) |
| `endpoint` | the server address, where one applies |
| `model` | the model id the harness is started with |
| `auth_profile` | a reference to a login, never a secret |
| `settings` | e.g. reasoning effort |
| `fallback` | an ordered list of other bindings, each listed by the user |

Precedence: an invocation flag, then user-local bindings, then portable
defaults. Every resolved choice, including an invocation override and a
fallback, must satisfy the project's hard requirements (rule 1, required
capabilities); a local binding can never relax them. The file carries a
`version`; an unsupported version or an unknown key is rejected. Fallback
chains are finite, ordered and user-listed: a fallback uses only bindings
listed in that role's chain, never switches login or provider unless that
exact binding is listed, and never rotates accounts. Listing a provider or
login change does not permit switching global credentials under live
sessions. A transient limit (rate limit, timeout) is kept distinct from a
permanent denial. Each run stores the sanitized binding it resolved for each
role.

This machine's roster (Claude Code lead, pi builder on a local model, Codex
reviewers) becomes an example profile. It is not a requirement.

## 6. Support envelope

- **Required today:** Herdr (the seat layer), git, gh, openspec, Python 3.10+.
  `tools/preflight.py` also hard-requires `pi`, `codex` and `claude`, and the
  librarian needs Hermes on a local model. #38 removes the fixed harness list
  (preflight derives it from the bindings) and #40 binds the librarian to any
  available harness.
- **After #32:** the run log's lock uses `fcntl`, which is POSIX.
- **Verified:** only this machine's example profile, on Linux under WSL2.
- **Binding portability (#38, #39):** single-harness (Claude-only,
  Codex-only) and local-only profiles get resolver and adapter fixture tests;
  they are labelled untested until the operator runs one live.
- **Transport:** herd needs Herdr. Running without it (tmux, or in-session
  agents) is not supported; #42 records what the seat layer must provide, and
  any other transport is decided after the #35 evaluation.

## 7. What each later issue takes from this

- **#38 resolver:** section 5 is its schema and precedence; rule 1 is a hard
  validation error; rule 2 is a warning plus a run record.
- **#39 setup:** asks per role, from the usable pool; shows each pair's
  diversity (section 4); previews the effective bindings and obtains the
  user's confirmation before saving section 5's file.
- **#40 cards and `herd.yaml`:** section 2 is the catalog; cards follow the own
  session / lead-held split; bindings stay out of `herd.yaml`.
