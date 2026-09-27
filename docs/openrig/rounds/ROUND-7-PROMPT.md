# Round 7 — team composition (new question from the operator)

The operator's question, verbatim:

> One item I haven't seen mentioned is the design of the team defined in the
> yaml config. The herd skill defines most of the same roles from the youtube
> video I shared. I saw mention of the new watchdog role, but I haven't yet
> seen mention of the Architect, Test QA, or Dogfood role. Have those been
> considered by either of you?

Honest answer: no — neither of us considered team composition; we treated
herd.yaml as a format for herd's existing roles. (Our row-2 "watchdog" is a
script folded into the watcher, not an agent seat.)

The video's workflow slide: ARCHITECT (sets shape) → PLANNER (writes the
spec) → BUILDER (implements) → REVIEWER (reads it) → TEST QA (checks it) →
DOGFOOD (uses it) → back to ARCHITECT; WATCHDOG (the clock) above.

## Sources — read them yourself

OpenRig clone (`../openrig-src/packages/daemon/specs/`):
- `rigs/launch/factory-rsi/rig.yaml` — the loop closest to the video
- `rigs/preview/product-team/rig.yaml` — orchestrator pair (Claude lead + Codex peer)
- `agents/development/qa/guidance/role.md` (+ its agent.yaml)
- `agents/factory-rsi/dogfood/guidance/role.md`
- `agents/factory-rsi/release-manager/`, `agents/orchestration/orchestrator/`
- search for any architect agent/role (`grep -ri architect`)
Herd: `/home/tusk/.claude/skills/herd/SKILL.md`, `/home/tusk/.claude/DEVLOOP.md`.
Our current table: `CONSENSUS.md` in this folder is v1; v2 is at
`/mnt/c/Users/Tusk/Desktop/openrig-herd-consensus/CONSENSUS.md` (read v2).

## What to do

PART 1 — before opening CLAUDE-round-7.md, write your own independent
assessment for each candidate seat: Architect, Test QA, Dogfood, Release
manager, Orchestrator peer (and any other seat in the shipped rigs you think
herd lacks). For each: what herd already does that covers it (cite
SKILL.md/DEVLOOP.md lines), the gap if any, a concrete shape (who, which
runtime, when in the loop, gated how), and a rating 1–5.

PART 2 — then read CLAUDE-round-7.md and give AGREE / COUNTER per row with
the reason, plus any change this causes to existing v2 rows (especially 3, 4,
2, 7a, and the order).

Write both parts to `CODEX-round-7.md`, end with `CONSENSUS: yes` or
`CONSENSUS: no — <rows>`, and reply with only the path.
