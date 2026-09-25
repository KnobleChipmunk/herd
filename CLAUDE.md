# CLAUDE.md — herd

This repo is the `/herd` skill and its toolkit. `~/.claude/skills/herd` is a
symlink into `skill/`, so a change here is live for the next run.

- Changes land through PRs on `chore/` or `feat/` branches, never directly
  on `main`. The herd's push exception covers a `chore/` branch amending the
  rules the loop follows; see the operator's global CLAUDE.md.
- Prefer a tool change over a new paragraph in the skill. A problem class
  that recurs after one wording fix moves into `tools/`.
- A change that loosens a gate, widens what an agent may edit, or skips a
  check is labelled as a relaxation in its PR and never bundled.
- Retro and post-mortem items are proposals; nothing is merged without the
  operator's signoff.
