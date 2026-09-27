# Proposal: mutate.py --scratch fails when the worktree argument is '.'

Status: in-pr https://github.com/KnobleChipmunk/herd/pull/62

## Class

mutate-scratch-dot-arg — mutate.py --scratch fails when the worktree argument is '.'

Events (friction ledger):
- 2026-09-27 herd #32: "mutate.py --scratch with worktree '.' raised FileExistsError because Path('.').name is empty, so the scratch copy collided in /tmp; reviewer and builder retried with an absolute worktree path."
- 2026-09-27 herd #33: "mutate.py --scratch with worktree '.' raised FileExistsError (Path('.').name empty); an absolute worktree path succeeded."
- 2026-09-27 herd #36: "mutate.py --scratch with worktree '.' raised FileExistsError (Path('.').name empty); an absolute worktree path succeeded."
- 2026-09-27 herd #38: "mutate.py --scratch with worktree '.' raised FileExistsError (Path('.').name empty); an absolute worktree path succeeded."
- 2026-09-27 herd #39: "mutate.py --scratch with worktree '.' raised FileExistsError (Path('.').name empty); an absolute worktree path succeeded."
- 2026-09-27 herd #39: "pi_build: mutate.py --scratch with worktree '.' failed (Path('.').name empty, copy target equals existing temp dir); the codex_review round-1 hit was retried with an absolute path."
- 2026-09-27 herd #40: "mutate.py --scratch with worktree '.' crashed in shutil.copytree (tmp dir already exists); absolute path succeeded and killed M12 and M15."
- 2026-09-27 herd #40: "Round 3 scratch mutation with worktree '.' still failed at mutate.py:69 (copytree destination exists); absolute path killed M18 and M19."
- 2026-09-27 herd #40: "Lead: mutate.py --scratch '.' was hit again by the #40 reviewer who retried with an absolute path; every briefing and reviewer prompt in this run passed '.'."
- 2026-09-27 herd #40: "pi_build: mutate.py --scratch with a '.' tree argument failed with FileExistsError; the reviewer had to retry with the absolute worktree path in rounds 1, 2 and 3."
- 2026-09-27 herd #40: "codex_review: mutate.py --scratch with worktree '.' failed with FileExistsError before running either mutation in all three review rounds; the absolute worktree path worked."
- 2026-09-27 herd #40: "Lead retro: mutate.py --scratch '.' was hit again by the #40 reviewer who retried with an absolute path; every briefing and reviewer prompt in this run passed '.'."

## Proposed change

Code change in `~/projects/herd/tools/mutate.py`. In `drive()`, resolve the
worktree path before it is used for the scratch copy name:
`w = w.resolve()` at the top of `drive()` (or just before line 68). The bug is
line 68, `copy = pathlib.Path(tmp) / w.name`: when the worktree argument is
`.`, `pathlib.Path(".").name` is `""`, so `copy` collapses to `tmp` itself and
`shutil.copytree(w, copy)` raises `FileExistsError` because `tmp` already
exists. After `.resolve()`, `w.name` is the real directory name and the copy
target is `tmp/<dirname>`.

Add a regression test that calls `drive()` (or the CLI) with
`--scratch .` and a relative worktree, asserting it runs the mutations instead
of raising `FileExistsError`.

Until that fix ships, generated reviewer prompts (`tools/mkbrief.py`) should
pass an absolute worktree path rather than `.`, since every briefing and
reviewer prompt in this run passed `.`.

## Prediction

No `mutate-scratch-dot-arg` events in the next run's friction lines;
`mutate.py --scratch` succeeds with a `.`, relative, or absolute worktree
argument, and reviewers no longer retry with an absolute path.
