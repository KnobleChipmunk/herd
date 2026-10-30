# readonly-worktree-cache-dir

Status: applied https://github.com/KnobleChipmunk/herd/pull/82 2026-09-30

## Class

readonly-worktree-cache-dir (read-only build worktree rejects linter cache writes)

Event lines, quoted from the ledger:

- 2026-09-30 project-mera #380-1: Ruff and mypy initially tried to write caches in the read-only build worktree; rerunning with /tmp cache directories cost about 30 seconds.
- 2026-09-30 project-mera #380-2: Read-only ruff cache in the build worktree required a /tmp cache rerun, and the mutation driver refused to run while a touched pytest was running, adding about 2 minutes.
- 2026-09-30 project-mera #380-3: Read-only build worktree cache paths made the initial ruff and mypy commands fail; rerunning with cache directories under /tmp cost about 9 seconds.
- 2026-09-30 project-mera #380-4: Read-only cache paths caused the initial ruff and mypy attempts to fail; redirecting both caches to /tmp cost about 1 minute.
- 2026-09-30 project-mera #380-4: The round-1 ruff run failed trying to write .ruff_cache in the read-only worktree and mypy failed before MYPY_CACHE_DIR was set; adding /tmp cache dirs to the reviewer gate commands fixed both, costing about one minute.

## Proposed change

Pre-set `RUFF_CACHE_DIR` and `MYPY_CACHE_DIR` in `tools/mkbrief.py`'s generated
gate commands: every ruff and mypy invocation in the build and build-reviewer
briefing carries `RUFF_CACHE_DIR=/tmp/<run-id>-ruff` and
`MYPY_CACHE_DIR=/tmp/<run-id>-mypy`, the same way the outside-sandbox pytest
rule already does. The worktree is read-only by design, so the env vars
belong in the generated command line, not in agent memory; a wording fix in
the skill has already been tried (the #333 and #482 runs both hit it) and
recurred, so this belongs in code.

## Prediction

No readonly-worktree-cache-dir events in the next run's friction lines:
first-attempt ruff and mypy runs succeed in every pane.

## Grading
2026-10-02: missed — #502p0 codex_review friction: read-only sandbox cache failures cost ~2 min (first-attempt cache writes failed again).

## Note (2026-10-30)

The cache locations no longer default to `/tmp`: `mkbrief.py --cache-dir` defaults to `~/Documents/claude/tmp/herd/<id>` (operator rule: nothing that must outlive one command goes in `/tmp`), on `chore/path-a-retros-fold`.
