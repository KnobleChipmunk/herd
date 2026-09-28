# Design

Use git blobs from one resolved commit as the base, rather than the mutable working files. The CLI validates the base ref once. Missing paths are absent base files so new_file steps can introduce them. Reference contents are read from the worktree argument. Only touched paths are compared.

The projection copies the base mapping and updates strings in step order. Reuse resolve/forms: the reference selects rendered forms; if a later replacement erased an intermediate inline result, the current unique base anchor selects the corresponding replacement form (exact first). Report the selected anchor count and require exactly one. This deterministic policy follows the checker’s form pairing and fails final parity if forms cannot be resolved consistently. It does not search alternative rewrite histories.

new_file requires absence; whole_file and append require presence; append keeps the existing single-terminal-newline precondition. Their fence bodies are exact, as in the existing checker. A replacement described only in prose cannot be projected safely and reports quoted old text required. Final comparison detects extra or missing content and missing reference files, even if each local replacement matched.

The pure projection never mutates the input mapping, writes files, calls apply_step or loads a plan module. The CLI only invokes read-only git commands; the documented python3 -B invocation also prevents import bytecode writes. Existing CLI behavior remains: FENCES OK for a final-build check, exit2 for no parsed steps. Projection prints per-step counts, per-file PARITY and PROJECTION OK only when all checks pass; exit1 for a projection/parity failure and exit2 for invalid base/empty plan.

The new CLI option’s caller is the plan-reviewer Evidence section, reached from the skill’s plan-review brief. It is permitted read-only inspection, preserving the ban on applying plans or running their code/tests/mutations.

## Plan review dispositions

F1 folded: assertions now cover new_file, append and whole_file n/a output; M6 removes the output and is killed. F2 retained as the explicit deterministic-form limitation: an ambiguous sequential insertion may fail parity, never pass incorrectly; arbitrary rewrite-history inference remains out of scope. F3 is an optional README follow-up outside the accepted impact scope; existing documented invocation stays valid. F4 requires no change: file snapshots and input-mapping assertions measure the read-only boundary; the monkeypatch is an additional guard, not the sole evidence.

## Build review ruling

Round1 F1 ACCEPTED: file-operation steps emit anchors=n/a before any precondition error, including all three existing failure cases. Lead regression RED3 failed32 passed; tests installed by the lead, implementation reapplied by builder. No step/test count change; review cap remains2.
