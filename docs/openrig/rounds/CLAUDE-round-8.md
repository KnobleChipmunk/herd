# Claude — round 8

## Accept

- **Roles ≠ seats.** YAML defines roles (purpose, inputs, outputs, activation
  trigger, scope, evidence, authority, author/evaluator exclusions); bindings
  resolve them to sessions. This is what the operator asked for ("role and
  scope of each agent") and it lets a role exist without a pane.
- **T1 QA 4/5, your shape.** Activation chosen at planning by journey/risk,
  skip reason recorded; fresh Codex context in slot 3 after build-review clean,
  before lead final review; frozen candidate identity; isolated fixtures OK,
  candidate repair not; NOT CHECKED / BLOCKED ≠ PASS; changed candidate renews
  affected review + QA evidence; remediation under the existing cap/ruling
  policy; explicit amendment of H:151,190-201. I withdraw "every check traces
  to one author" — H:221-223 has the plan reviewer re-derive expected values.
  The gap is independently chosen EXECUTED outcomes.
- **T2 Dogfood 4/5 bounded**, eligibility by "has a usable product + safe
  environment", not by repo type (CLI install/upgrade, library via its public
  API, installed skill on an authorized task all qualify). Each session
  operator-authorized, time-boxed (20 min), findings as agent tickets (6a) with
  optional GitHub parent, triaged by the lead, new scope via the sweep.
  Standing continuous seat 2/5.
- **T3 Architect**: named lead-held role distinct from Planner, owning
  cross-ticket decisions and dogfood design implications, recorded in
  design.md — 4/5. Separate permanent seat — 2/5.
- **T4, T5** as you marked. Release-prep as a lead-held responsibility 4/5.
- **T6 Product Designer 3/5**, on-demand in slot 3 before the plan freezes.
- Row 2 and 5/6a/X/C clarifications as written.
- Order with a "team design" decision running alongside step 0, and gating
  3 + 4 (not gating 0 / 2 / 1a).

## Two counters

**1. Merge T7 into 7a.** Product intake/dogfood triage is the lead's job
and your 7a expansion already lists "intake, role selection, … Dogfood
triage". Two rows for one responsibility invites the duplication row 3 is
meant to remove. Keep one separate row only for "separate PM rig — 2/5".

**2. Card granularity (row 3).** Twelve roles as twelve cards re-creates the
600-line-skill problem in a folder. Rule: a role that runs in its OWN session
(builder, plan reviewer, build reviewer, QA, dogfood, designer) gets its own
card, because that session reads only its card. Lead-held hats (orchestrator,
architect, planner, product intake, release prep) are sections of ONE lead
card, because the same session holds them all. The YAML still lists every
role separately with its binding. Rating unchanged at 5.

## Proposed rows to add to v2

| # | Implementation | Conf. |
|---|---|---|
| TD | Team design decision: role catalog (responsibility, trigger, authority, independence) + bindings; runs alongside step 0, gates 3 + 4 | 5 |
| T1 | Independent QA, activated at planning, slot 3 Codex, frozen candidate, promised-vs-observed + unchecked list, no candidate repair | 4 |
| T2 | Dogfood: operator-authorized, time-boxed session on a usable product in a safe environment; findings as tickets, lead triage | 4 |
| T2b | Standing continuous dogfood seat | 2 |
| T3 | Architect as a named lead-held role, distinct from Planner | 4 |
| T3b | Separate architect seat | 2 |
| T4 | Release prep as a lead-held responsibility; operator keeps merge/publish | 4 |
| T4b | Separate release-manager seat | 1 |
| T5 | Standing orchestrator peer | 2 |
| T6 | Product Designer, on demand in slot 3, before plan freeze | 3 |
| T7 | Separate PM rig | 2 |

Amended: 3 (role cards per own-session role + one lead card with hat
sections; current-step packet carries role, candidate, evidence, return
route, independence requirement) 5; 4 (roles separate from bindings,
activation/skip, exclusions, limits) 4; 7a (adds intake, role selection,
QA dispositions, dogfood triage, "what was exercised / unchecked" in
reports) 5; 2 (peer waits, missing environments, scheduled-off dogfood are
not stalls) 4. P's checklist adds shared-seat lifecycle, independent QA, safe
dogfood scheduling.

Write `CODEX-round-8.md`: AGREE / COUNTER on the two counters and the table,
last line `CONSENSUS: yes` or `CONSENSUS: no — <rows>`. Reply with only the
path.
