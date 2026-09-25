# herd

The `/herd` skill and the toolkit it runs on.

- `skill/SKILL.md` is the live skill. `~/.claude/skills/herd` is a symlink to
  `skill/`, so editing this file changes what the next run loads.
- `tools/` holds the helpers the lead and agents call during a run:
  - `herdtool.py` applies a plan module to a worktree, drives its mutations,
    checks fence parity and renders `tasks.md`.
  - `mkbrief.py` writes the builder briefing and the reviewer prompt.
  - `wait_file.sh` and `watch_review.sh` wait on the files agents write,
    which is the reliable completion signal.

## Install

```bash
ln -s ~/projects/herd/skill ~/.claude/skills/herd
```

## Configuration

Nothing in `tools/` names a machine path or a pane. Each value is resolved
at run time:

- **Python** for tests and mutation drives: `$HERD_PYTHON` if set, else
  `.venv/bin/python` in the worktree's main checkout (found through git),
  else the interpreter running the tool.
- **Lead pane** that receives DONE, BLOCKED and REVIEW CLEAN: `mkbrief.py
  --lead-pane`, else `$HERDR_PANE_ID`, so run it from the lead's pane.
- **Build reviewer** pane: `mkbrief.py --reviewer`, default `codex_review`
  (the skill's Roster table).

## Tests

```bash
python3 -m pytest
ruff check tools tests
```

`tests/test_herdtool.py` fails if any tool names a machine path, the
project-mera checkout, or a pane from a past run.
