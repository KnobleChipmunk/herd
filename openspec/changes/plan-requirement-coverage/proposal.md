# Account for governing requirements before generating fences

## Why
The accepted proposal `proposals/2026-09-27-plan-omits-required-requirements.md` records green pre-execution that omitted governing requirements and introduced a command with no caller.

## Grounded facts
At base 8c97de1, `openspec/config.yaml:1` selects the spec-driven schema and has only commented artifact-rule examples. `skill/cards/plan-reviewer.md:21` describes review checks without a requirement table. The lead's pre-execution step at `skill/SKILL.md:292` follows spec authoring without a coverage checkpoint.

## What Changes
Add a task-artifact rule for a table mapping each governing requirement to its source section, implementing step and acceptance evidence, or a linked deferral. Require source comparison against the issue and design, and a skill/card caller for each new command. Add the checkpoint before fence generation and its independent plan-review check.

## Non-goals
No automatic completeness checker, new commands, changed permissions, new dependencies, or retroactive edits to archived plans.

## Impact
Three instruction/configuration files and one contract test (small tier, fewer than 50 added lines, no mechanism). Existing PyYAML in requirements.txt parses the config test.
