# Proposal: herdr --wait returns on acknowledgment, not idle

Status: applied https://github.com/KnobleChipmunk/herd/pull/53 2026-09-27

## Class

herdr-wait-not-idle — herdr agent prompt --wait returns on acknowledgment, not idle

Events (friction ledger):
- 2026-09-25: "herdr agent prompt --wait returned agent_prompted as soon as the agent acknowledged, not when it went idle, forcing a separate 'agent wait --until idle' step plus an unhandled stalled case; cost about 1 minute and confusion."
- 2026-09-26: "herdr agent prompt codex_review --wait --timeout 540000 exited with 'timed out waiting for agent status' before the reviewer finished; had to follow with herdr agent wait, costing about 1 minute extra."

## Proposed change

Change the tooling that scripts agent dispatch in `tools`: the
dispatch helper should always sequence `herdr agent prompt <role>` followed by
`herdr agent wait <role> --timeout <t>` as one two-step command, and treat
"timed out waiting for agent status" from `--wait` as an expected case that
hands off to the same wait step rather than a dispatch failure. Do not add a
paragraph to the skill explaining the two-step; the two-step becomes one
tool call.

## Prediction

No `herdr-wait-not-idle` events in the next run's friction lines; dispatch
transcripts show a single scripted dispatch+wait step and no follow-up manual
`herdr agent wait` commands.
2026-09-27: held
2026-09-29: held
- 2026-09-30: held

## Grading
- 2026-10-02: held
