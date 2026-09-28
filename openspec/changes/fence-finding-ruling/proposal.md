# Findings in byte-exact fences

## Why

The accepted proposal `proposals/2026-09-27-no-prescribed-ruling-for-fence-conflict.md` records confirmed defects being marked FOLDED while unresolved. A clean review must mean those defects were resolved.

## Grounded facts

- `tools/mkbrief.py:129` tells builders to fix every confirmed finding without distinguishing a fix requiring a spec edit.
- `tools/mkbrief.py:183` permits only FINDINGS or REVIEW CLEAN sentinels.
- `skill/cards/builder.md:29` gives builders review authority but no fence-conflict route.
- `skill/SKILL.md:609` records lead rulings; pre-execution and generated fences remain lead responsibilities.

## What Changes

A reviewer tags confirmed fence-owned findings "in the fence" and returns FINDINGS: <n> (spec). The builder reports BLOCKED immediately. The lead folds accepted fixes into the reference, validates and regenerates fences, and the builder reapplies affected files.

## Non-goals

No automatic review parser, changed review caps, new persistence, changes to operator gates, or weakening fence parity.

## Impact

Generated build briefings, reviewer prompts, builder and build-reviewer cards, and lead ruling instructions.
