# Role catalog, role cards, step packet and loop gates (#40)

## Why

Roadmap step 6 (rows 3, 4, C and X-gates) and the team design
(`docs/team-design.md`, PR #48): roles are not seats. Today the roles live in
prose inside `skill/SKILL.md`, the Roster table names vendors, a recovering
session has to reread the whole skill, and the loop's structural gates (spec
approved, review cap) are rules in prose that nothing checks.

## What changes

- New `skill/herd.yaml`: the portable role catalog, 12 roles (5 lead-held,
  7 own-session), each with where it runs, its binding, card, activation,
  purpose, outputs, what it evaluates, where it returns, and what it may not
  do, plus the team design §2 policy fields: capabilities, skip conditions,
  allowed operations, time and cost limits (`unset` until the operator sets
  one; dogfood 20 minutes), exclusions, and `advisory: true`. No vendor
  names; constraints are advisory until a tool enforces them.
- New `skill/cards/`: one card per own-session role with the eight agreed
  fields (purpose, inputs, outputs, activation, scope, evidence, authority,
  exclusions), extracted from today's SKILL.md contracts and the team design;
  one lead card with the same eight fields for each of the five lead-held
  roles. Every evaluator card (plan reviewer, build reviewer, QA) states the
  same hard independence rule: no authorship of what it judges, including
  the lead's pre-execution, and a fresh context whatever pane or model. The
  build reviewer therefore excludes the planner as well as the builder. The librarian keeps `hermes/herd-librarian/`.
- New `tools/team.py`: `check` validates the catalog and cards, and requires
  all twelve roles with the 5 lead-held / 7 own-session split; `assign`
  records the resolved assignment at dispatch (role, binding, session,
  candidate, scope, selected checks) as a run-log `note` holding JSON; `packet`
  prints a role's card, current step (from the run log), candidate, return
  route, independence rule, binding (from #38), prohibitions and the latest
  recorded assignment for the role, for dispatch and after compaction; when an
  assignment exists, its binding and candidate are the packet's, and the
  bindings file is not read; `gate dispatch` requires `spec-approved` and a last
  plan review of APPROVE; `gate review` enforces the 2-round cap, +1 per ruling;
  `gate review-file` requires a `Candidate:` line with a value on the same
  line.
- `skill/SKILL.md`: the Roster section says the catalog and the bindings file
  decide, and the table is this machine's example profile; Roles and
  hand-offs points at the cards, `assign` then `packet` at dispatch, and the
  gates; the slot-3 rule
  "same kind, next role: rename and re-prompt" gains the evaluator's fresh
  context.

## Grounded facts

- Builder and build-reviewer contracts: `skill/SKILL.md` ("pi_build (builder)",
  "codex_review (build reviewer)"); plan-reviewer brief: "Plan-reviewer brief
  (#330, #321)"; review cap: "Cap **2 rounds** (+1 on a ruling)".
- Team design §2 (roles, lead-held vs own-session, may-not), §3 (seats), §4
  (independence), `docs/team-design.md` on `feat/31-team-design`.
- `bindings.ROLES` and `bindings.resolve` (#38).
- Live (2026-09-27): `team.py check` → valid; `team.py packet build_reviewer
  --issue 33` on the real run log → step `pr-opened`, binding from the example
  profile.

## Non-goals

- `probe.py` still reads the Roster table, and pane names still carry vendor
  names; both move in #51 (filed in this run), which also creates this
  machine's bindings file before the table goes.
- The gates are checks the lead runs; wiring them into every tool is later.
- A new run-log kind for assignments: `note` with a JSON body is enough for
  one reader (`packet`); a kind is added when a second reader needs one.
- Vendor-neutral pane names and the model-free Roster: #51.
- Binding the librarian through any available harness, and recording a
  durable pending obligation when none can run it (plan review F4): moved
  to #51 by https://github.com/KnobleChipmunk/herd/issues/51#issuecomment-5859350684.
- The skill's "the fallback is never Opus" rule stays. Team design §4 makes
  model diversity a recommendation that a project may make stricter; this is
  this machine's stricter rule, and the cards say so.

## Impact

New `skill/herd.yaml`, `skill/cards/*.md` (7), `tools/team.py`,
`tests/test_team.py`; edits to `skill/SKILL.md`, `tests/test_skill_text.py`,
`pyproject.toml`. Stacked on `feat/41-context`.
