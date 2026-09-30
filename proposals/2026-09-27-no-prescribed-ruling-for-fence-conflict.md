# Proposal: no prescribed ruling shape when a finding breaks the byte-exact fences

Status: applied https://github.com/KnobleChipmunk/herd/pull/66 2026-09-28

## Class

no-prescribed-ruling-for-fence-conflict — no prescribed ruling shape when a finding breaks the byte-exact fences

Events (friction ledger):
- 2026-09-25 project-mera #460: "A build-review finding in a byte-exact build needed a lead fold (fold fix into reference, regenerate fences, builder re-applies affected files) but the skill never names this ruling shape; the builder had to infer the only legal move was BLOCKED."
- 2026-09-27 herd #41: "codex_review round-1 finding (dangling symlink at backup name in context_collector._backup) was real but unfixable without editing the byte-exact fence, which would break the FENCES OK (6 steps) gate; the builder surfaced it to the lead as BLOCKED."
- 2026-09-27 herd #40: "Round 1 findings 1-4 (null binding/card, non-card path, extra role, None binding in assignment) required deviating from the byte-exact fence I10 of tools/team.py, which the mandatory FENCES OK (15 steps) gate forbade; unfixable by the builder without a lead ruling on the spec fence."
- 2026-09-27 herd #39: "Lead: stale fences after builder fixes ended in BLOCKED at the cap, a lead fold, and a ruling for +1; cost about 15 minutes and the builder was right."
- 2026-09-27 herd #41: "Lead: _backup wrote through a dangling symlink, ending in BLOCKED at the cap, a lead fold, and a ruling for +1; cost about 15 minutes and the builder was right."
- 2026-09-27 herd #40: "pi_build: round 1 returned five CONFIRMED findings, four of which required deviating from the byte-exact I10 fence while FENCES OK was a mandatory gate; the builder refused to edit the spec, recorded friction, and routed it to the lead for a ruling."
- 2026-09-27 herd #40: "codex_review: four round-1 findings were in the I10 tools/team.py fence; the builder could not fix them while FENCES OK remained mandatory, so the reviewer marked them FOLDED, ended round 2 with REVIEW CLEAN, and the lead had to rule."
- 2026-09-27 herd #40: "Lead: REVIEW CLEAN hid four confirmed defects in the byte-exact fence; the build reviewer marked them 'FOLDED - lead/spec change needed' and ended round 2 with REVIEW CLEAN, the builder sent DONE, and the lead found them only while reading the review file on the final pass."
- 2026-09-27 herd #40: "pi_build: nothing in the skill names the fence-vs-finding rule, so the builder had to infer that a CONFIRMED finding requiring deviation from the byte-exact I10 fence is not builder-fixable and must be recorded as friction and routed to the lead."

## Proposed change

The #40 cost was that the reviewer masked fence-owned findings as FOLDED and
ended with REVIEW CLEAN, so the builder sent DONE and the lead only found the
defects on a final-pass read. The fix is to name the ruling shape in the tool
and skill so the builder blocks in round 1 instead of spending a second round.

1. `tools/mkbrief.py`: in the build-reviewer prompt, add an explicit rule: a
   CONFIRMED finding whose fix requires editing a byte-exact fence (the spec's
   text) is tagged "in the fence" in the review body, is NOT marked FOLDED,
   and is NOT counted toward a clean round. When any such finding exists, the
   round ends with `FINDINGS: <n> (spec)` — never `REVIEW CLEAN` — and the
   builder sends `BLOCKED` to the lead in that same round.
2. `skill/SKILL.md` builder card, Authority section: add the fence-vs-finding
   rule verbatim — "a CONFIRMED finding that requires deviating from a
   byte-exact fence is not builder-fixable; record friction and report it for
   a lead ruling. Do not edit the fence or the spec."
3. `skill/SKILL.md` lead section: name the ruling shape that was always the
   only legal move — fold the fix into the reference, regenerate the fences,
   and have the builder re-apply the affected files.

## Prediction

No `no-prescribed-ruling-for-fence-conflict` events in the next run's friction
lines; fence-owned findings appear as `FINDINGS: <n> (spec)` in the round
file, the builder sends BLOCKED in round 1 (no second round spent), and the
lead never has to discover spec-owned defects during a final-pass read.

## Grading
- 2026-09-29: held
- 2026-09-30: held
