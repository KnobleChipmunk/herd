# mutation-only-full-name

Status: accepted

## Class

mutation-only-full-name — mutate.py --only requires full labels and silently no-ops

Event lines, quoted from the ledger:

- 2026-10-02 project-mera #502p0 (linux): mutate.py --only matched only full mutation labels; short names silently matched nothing, costing ~2 min.
- 2026-10-02 project-mera #502h (linux): mutate.py --only silently matched no mutations for shorthand M1,M2; finding the required full heading names cost ~1 min.
- 2026-10-02 project-mera #502b (linux): mutate.py --only requires full mutation labels; trying short IDs M1,M9 produced no drives and cost ~1 min.
- 2026-10-02 project-mera #502b (linux): passing --only M1,M9 following the usage example exited 0 with no output because section 3 stores full labels; had to inspect the parser and rerun with both full labels.

## Proposed change

Code change in `tools/mutate.py`. When `--only` is given, after parsing the filter and matching it against the mutation list, if zero mutations match, exit non-zero and print the available full labels (one per line, prefixed with "available:"). Currently the filter silently matches nothing and the drive exits 0 with no output, which reads as a successful no-op and fails a review gate only when the operator counts the expected result lines. A tool change, not a skill instruction: the check is mechanical and every agent hit it independently.

Additionally, the reviewer's scratch drive should require exactly the expected number of result lines (one per requested mutation) before the gate is satisfied; this is already in the reviewer's card for the 502b run but should be stated unconditionally in the build-reviewer section of the skill.

## Prediction

No `mutation-only-full-name` events in the next run's friction lines: a `--only` filter that matches nothing exits non-zero with the available labels listed, so agents never spend minutes inspecting the parser to discover the full-label requirement.
