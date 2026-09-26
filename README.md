# herd

The `/herd` skill and the toolkit it runs on.

- `skill/SKILL.md` is the live skill. `~/.claude/skills/herd` is a symlink to
  `skill/`, so editing this file changes what the next run loads.
- `tools/` holds the helpers the lead and agents call during a run:
  - `herdtool.py` applies a plan module to a worktree, drives its mutations,
    checks fence parity and renders `tasks.md`.
  - `mkbrief.py` writes the builder briefing and the reviewer prompt.
  - `fencecheck.py <tasks.md> <worktree>` checks a build against the
    byte-exact fences in its `tasks.md` and prints one line per deviation
    (step, file, why). It needs only `tasks.md`, so the builder runs it
    before the handoff and the build reviewer runs it instead of reading
    fences by eye; `mkbrief.py` writes both commands into place.
  - `gates.py match "<expected>" <output>` compares a gate by its counts
    (pytest's warnings and wall time ignored; mypy's error, file and checked
    counts all count). `gates.py manifest <worktree> <base> --allowed <file>`
    lists every changed file, untracked ones included, and flags any file
    outside the allowed list. Coordination files and `SCRATCH-*` are ignored.
  - `mutate.py <tasks.md> <worktree> [--only M1,M2] [--scratch]` drives the
    mutations in `tasks.md`: KILLED with the failing test, SURVIVED, VOID
    when an anchor is not unique, TREE CHANGED when a drive left the tree
    different. `--scratch` drives a copy, for reviewers.
  - `runlog.py add <kind> …` appends one checkpoint to the run log in the
    repo's git directory; `status`, `created` and `friction` read the latest
    run back (progress per issue and what is still open, what the run
    created, and the agents' friction lines).
  - `probe.py [--role ROLE] [--log --repo PATH]` reads the Roster table,
    sends each candidate in a role's fallback chain a one-line request
    through its own harness, and prints the model each role will use;
    fallbacks are logged to the run log.
  - `preflight.py [--need ISSUE:VARIABLE ...]` checks the run is inside
    Herdr, every tool is on PATH, and each needed variable is set, without
    printing values. Part of the skill's pre-run sweep.
  - `merge_stack.py [--repo PATH] [--apply]` is the operator's morning
    command: merge the run's PRs in order, pull main, and remove what the
    run log says the run created, then start the librarian (Hermes) in the
    background, once per run (`--no-librarian` skips it). A dry run without
    `--apply`; safe to re-run.
  - `librarian.py` is the post-run librarian's deterministic half: ledger
    rows counted from the run log and live gh (`ledger-rows`,
    `append-ledger`), the run's friction lines and retro files
    (`friction`), and filing one friction line under a class in the vault's
    friction ledger with the class's event count (`friction-append`).
  - `wait_file.sh` and `watch_review.sh` wait on the files agents write,
    which is the reliable completion signal.

## Install

```bash
ln -s ~/projects/herd/skill ~/.claude/skills/herd
ln -s ~/projects/herd/hermes/herd-librarian ~/.hermes/skills/herd-librarian
```

`hermes/herd-librarian/` is the Hermes skill that files a finished run into
the vault ledgers with `tools/librarian.py`. `merge_stack.py --apply`
starts it; its report is a `librarian-<time>.log` next to the run log. Its
proposals land in `proposals/`, each with a `Status:` line that
`tools/proposals.py` manages: the lead asks about `open` ones in its
pre-run sweep, builds `accepted` ones as herd PRs, and the librarian marks
them applied when those PRs merge.

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
