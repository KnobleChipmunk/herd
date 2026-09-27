# mutation-runner Specification

## Purpose
Define scratch mutation runs that accept current-directory paths and preserve the source worktree.
## Requirements
### Requirement: Scratch runs accept the current-directory worktree

The mutation runner SHALL accept `.` and `./` as worktree arguments with `--scratch`, execute selected mutations in a temporary copy, and preserve source file bytes, modification time, and git status. Absolute worktree paths SHALL retain this behavior.

#### Scenario: Run a selected mutation from the worktree root

- **WHEN** the user invokes mutate.py with a valid tasks file, worktree `.`, `--only M1`, and `--scratch`, and M1 is killed by its test
- **THEN** the runner reports M1 KILLED, exits zero, and leaves the source tree unchanged

#### Scenario: Equivalent path spellings

- **WHEN** the same scratch run uses `./` or the absolute worktree path
- **THEN** it has the same result and source-preservation behavior
