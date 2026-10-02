# sandbox-write-blocked

Status: in-pr https://github.com/KnobleChipmunk/herd/pull/92

## Class

sandbox-write-blocked — read-only sandbox blocks tool cache/state writes

Event lines, quoted from the ledger:

- 2026-10-02 project-mera #502p0 (linux): read-only sandbox blocked cache writes during the review, costing ~2 min.
- 2026-10-02 project-mera #502 (linux): suite-ok first attempt failed because it writes shared Git herd state outside the sandbox; retried elevated, ~1 min lost.

## Proposed change

This is the same failure class as `readonly-worktree-cache-dir` (which missed its 2026-09-30 proposal: the 502p0 reviewer hit cache-write failures again), extended to non-cache writes. The generated gate commands in `tools/mkbrief.py` should pre-set every env var that a tool needs to write outside the worktree: `RUFF_CACHE_DIR`, `MYPY_CACHE_DIR`, and any tool-specific state dir (the Git herd state path for `suite-ok`). The `readonly-worktree-cache-dir` proposal already covers ruff/mypy; this proposal adds the general rule to the tooling: every generated command that a sandboxed agent runs must have its write targets resolved to writable paths before the agent sees the command. If a tool's state path is not configurable by env var, the briefing should state the exact `env FOO=/tmp/<run-id>-foo` prefix to use.

This is a tool change in `tools/mkbrief.py`, not a skill paragraph: the `readonly-worktree-cache-dir` proposal (PR #82) already fixed the ruff/mypy case and the 502p0 reviewer hit it again, so the fix is incomplete and belongs in code.

## Prediction

No `sandbox-write-blocked` events in the next run's friction lines: first-attempt gate commands succeed in every sandboxed pane without the agent discovering a blocked write path.
