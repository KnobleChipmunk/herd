# mutation-name-parse-mismatch

Status: accepted

## Class

mutation-name-parse-mismatch — herdtool renders mutation names mutate.py cannot parse

Event lines, quoted from the ledger:

- 2026-10-02 project-mera #502p0 (linux): tasks.md names a P1 mutation but the herdtool parser accepts only M-prefixed names; drive exited 2 and the builder was blocked ~5 min inspecting and documenting.
- 2026-10-02 project-mera #502p0 (linux): herdtool render_mutations accepts any name while parse_mutations/mutate.py match only M-prefixed names; P1 rendered fine and parsed to zero mutations, blocking the builder ~10 min.
- 2026-10-02 project-mera #502 (linux): herdtool render accepted a mutation name mutate.py cannot parse; the defect was invisible until the builder's mutate.py parsed tasks.md (fixed in herd #88).

## Proposed change

The render-side fix (herd #88: render refuses non-M names) addresses this run's P1 case, but the general gap remains: anything the builder parses from tasks.md should be parsed back by the lead before dispatch. Add a `herdtool check-parse` step (or fold it into `herdtool render`) that runs `mutate.py`'s mutation parser over the generated tasks.md and exits non-zero if any rendered mutation name does not parse. This is a tool change in `tools/herdtool.py`, not a skill paragraph: the check is mechanical and the lead already has the right moment (just before dispatch).

## Prediction

No `mutation-name-parse-mismatch` events in the next run: `herdtool render` (or the new `check-parse` step) rejects any tasks.md whose mutation names do not all parse, so the builder's `mutate.py` never sees an unparseable name.
