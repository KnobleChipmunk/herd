# Proposal: fencecheck prints FENCES OK (n steps) but the prompt calls for bare FENCES OK

Status: applied https://github.com/KnobleChipmunk/herd/pull/26 2026-09-26

## Class

fencecheck-success-line-mismatch — fencecheck prints FENCES OK (n steps) but the prompt calls for bare FENCES OK

Events (friction ledger):
- 2026-09-26: "The reviewer prompt said every line other than 'FENCES OK' was a finding, but fencecheck.py printed 'FENCES OK (12 steps)', so the success line reads as a spurious finding."
- 2026-09-26: "The build-reviewer prompt again treated fencecheck's actual 'FENCES OK (25 steps)' line as a finding; the same prompt/tool mismatch recurred a week after the 459-1 review hit it."

## Proposed change

Prefer a tool change over a skill paragraph: the reviewer prompt text in
`tools` (or the skill template it is generated from) should
define the sentinel as the regex `^FENCES OK` — i.e. accept
`FENCES OK (<n> steps)` explicitly and reserve findings for mismatch lines or
a nonzero exit. If the sentinel is generated from the tool's own output, make
the prompt generation read the success format from `fencecheck.py` so the
two can never drift. Recurred after a wording-adjacent miss, which argues the
sentinel must live in code, not prose.

## Prediction

No `fencecheck-success-line-mismatch` events in the next run's friction
lines; reviewer transcripts show `FENCES OK (n steps)` accepted as success
with no spurious finding raised against it.

## Grading
- 2026-09-27: held
- 2026-09-29: held
- 2026-09-30: held
- 2026-10-02: held
