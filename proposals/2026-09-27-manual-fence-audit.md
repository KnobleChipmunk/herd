# Proposal: plan reviewer hand-rebuilds the base-to-fences audit each run

Status: accepted

## Class

manual-fence-audit — plan reviewer hand-rebuilds the base-to-fences audit each run

Events (friction ledger):
- 2026-09-25 project-mera #460: "Plan reviewer independently rebuilt the base→fences→replay audit in memory in rounds 4 and 5, checking 62 steps and then 46/48 mutations across 28 files, because no read-only audit command exists."
- 2026-09-27 herd #40: "Plan reviewer's first literal fence projection in round 2 counted zero matches for I13 because the rendered fence ended with a newline while its anchor ended mid-line; reading herdtool.forms() and fencecheck.py showed the repo deliberately permits removing that rendering-added newline, so a read-only base-projection mode for the fence tools is needed."

## Proposed change

Both events are the reviewer hand-rebuilding a projection the tooling already
has the rules for, and getting it wrong on the newline form. Add a read-only
base-projection mode to the existing fence tooling (`tools/fencecheck.py` /
`herdtool`): it reads the supplied base files, applies the documented forms
(including the permitted removal of the rendering-added trailing newline) in
memory only, and reports per-step anchor counts plus final base parity. It
never writes files and never imports or executes plan code, so it preserves
the prohibition on re-executing the plan.

Put the exact invocation and its boundary (read-only, in-memory forms, no
plan-code execution) in the plan-review brief, replacing reviewer-written
parsers and the in-memory base→fences→replay rebuild.

## Prediction

No `manual-fence-audit` events in the next run's friction lines; the
plan reviewer runs the base-projection command and reads anchor counts /
parity from its output instead of rebuilding the audit in memory, and
newline-form mismatches no longer read as false zero-match defects.
