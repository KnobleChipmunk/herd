# Proposal: zero-count grep gate exits 1 and reads like a failure

Status: applied https://github.com/KnobleChipmunk/herd/pull/27 2026-09-26

## Class

grep-zero-exit-one-misread — zero-count grep gate exits 1 and reads like a failure

Events (friction ledger):
- 2026-09-25: "grep -c exits 1 on zero matches, which the tool surfaces as 'Command exited with code 1', so both zero-count grep gates read like failures in the transcript."
- 2026-09-26: "grep -c exits 1 on zero matches, which broke the builder's &&-chained baseline/after grep gates twice, forcing re-runs of the remaining greps separately."
- 2026-09-26: "Grep gates were not shell-proof: a $(...)-looking pattern counted 5 in bash and 0 in zsh, and grep -rn over a source dir also matched a .pyc, so gates had to be re-measured in the builder's shell."

## Proposed change

Code change in `~/projects/herd/tools`: when a briefing generates grep gates,
emit them as a single script (`herdtool.py run-gates <gate-spec>`) that runs
each gate statement separately (no `&&` chaining), appends `|| true`-safe
count capture so zero matches are a normal result, forces literal matching
(`grep -Fc` for literal patterns), and pins `--include='*.py'` for directory
sweeps. The briefing template should point builders at that one command
instead of raw grep one-liners, so shell differences and exit-code semantics
stop being builder-local problems.

## Prediction

No `grep-zero-exit-one-misread` events in the next run's friction lines;
briefing grep gates appear as a single generated command and zero-count
results appear as `0` with exit 0.

## Grading
- 2026-09-27: held
