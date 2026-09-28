# Generate briefing gates from tasks.md

## Why

The accepted proposal `proposals/2026-09-27-stale-gate-evidence-in-brief.md` records briefing suite counts, mutation ranges and fence counts drifting after spec amendments.

## Grounded facts

At prerequisite d6b0ed7 (PR #66), `tools/mkbrief.py:3` accepts a separate gates-file argument, and `tools/mkbrief.py:46` accepts the gates string separately from the named change. `skill/SKILL.md:346` asks the lead to write the briefing without a mandatory regeneration step after amendments. These are independent copies of the authoritative plan evidence.

## What Changes

The generator reads the single nonempty `## 0. Gates` section from the named change's tasks.md on each invocation. It respects fenced code while finding sections, copies the measured text, and rejects missing or ambiguous gate sections before writing outputs. The separate gate-file CLI argument and gates function argument are removed. The lead generates after approval and regenerates after every amendment, with a pinned base SHA.

## Non-goals

No validation of whether a claimed test result really ran, no new gate execution engine, no automatic spec amendments, no migration of archived specs, no generic Markdown parser, and no changes to operator permissions.

## Impact

`tools/mkbrief.py`, its tests, and the lead's briefing-generation instruction. Existing callers must supply tasks.md's gate section and omit the old gates-file argument.
