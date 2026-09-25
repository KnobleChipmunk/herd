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

## Known debt

The tools were imported verbatim from the 2026-09-21 overnight run and still
carry project-mera paths (`PY`, `HOME`, the briefing text in `mkbrief.py`).
Making them portable is the first toolkit PR.
