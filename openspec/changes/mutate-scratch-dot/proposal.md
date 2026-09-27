# Fix scratch mutation runs from the current directory

Issue: https://github.com/KnobleChipmunk/herd/issues/55
Tier: small. Scope ends at a reviewed PR; merge stays with the operator.

## Grounded facts

- At base 1dce870, `tools/mutate.py:67-69` constructs a copy destination with `w.name`; Path('.') has an empty name, so copytree receives the already-created temporary directory.
- `tools/mutate.py:85` passes the command-line worktree to drive without normalization.
- `tests/test_mutate.py:97-101` covers scratch isolation using an absolute fixture path, but not the current-directory CLI argument.
- Pre-execution reproduces FileExistsError for both `.` and `./`; the absolute case succeeds.

## Change

Resolve the scratch source before deriving its basename. Add a parameterized main-entry regression for `.`, `./`, and an absolute path. It checks the selected mutation is killed, the command succeeds, and source bytes, mtime, and git status remain unchanged.

## Non-goals

No mutation-engine redesign, gate relaxation, dependency additions, or changes to non-scratch execution. Existing proposals and other issues stay outside this run. QA is not selected separately: the CLI-entry regression and independent build review cover this bounded change.
