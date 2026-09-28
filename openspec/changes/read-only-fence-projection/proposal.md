# Read-only projection of plan fences

## Why
The accepted proposal `proposals/2026-09-27-manual-fence-audit.md` records reviewers rebuilding the projection and mistaking a renderer-added newline for a required source newline.

## Grounded facts
At ace145d, `tools/fencecheck.py:23` resolves rendered forms against a built worktree and `tools/fencecheck.py:43` checks final step text. `tools/herdtool.py:255` defines the permitted forms; `tools/herdtool.py:335` parses tasks without loading a Python plan module. `skill/cards/plan-reviewer.md:29` asks the reviewer to project fences in memory without a command.

## What Changes
Add `--base <pinned-base-sha>` to fencecheck. Read base git blobs, project parsed steps in memory, report each anchor count and compare final touched-file text with the supplied reference. Support all existing step kinds with quoted anchors, existing newline forms, and sequential inline replacements. Refuse absent/nonunique anchors, failed file preconditions and prose-only replacements with clear diagnostics. Give the plan reviewer the exact command and read-only boundary.

## Non-goals
No plan-code execution, file writes, new parser, arbitrary prose interpretation, mutation execution, automatic plan repair or broader task grammar. This is a deterministic audit using the existing form-resolution rules, not a search over all possible rewrites. No changes to the existing two-positional-argument final-build check or operator permissions.

## Impact
`tools/fencecheck.py`, its tests, the plan reviewer card and its pointer in the skill. Full tier: new audit mechanism. Standard-library imports only.
