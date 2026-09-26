# Proposal: mutate.py's running-pytest guard matches any argv mentioning pytest

Status: applied https://github.com/KnobleChipmunk/herd/pull/22 2026-09-26

## Class

mutate-py-argv-match — mutate.py's running-pytest guard matches any argv mentioning pytest

Events (friction ledger):
- 2026-09-26: "mutate.py falsely detected pytest from the Herdr prompt command line; creating an outer scratch copy and rerunning outside the sandbox cost about 3 minutes."
- 2026-09-26: "mutate.py treated a herdr prompt process whose argv mentions pytest as a running pytest and refused the reviewer's scratch re-drive; fixed in herd#22 during the run."

## Proposed change

The guard fix shipped in herd#22 mid-run, so the proposal is a code change to
keep it fixed: add a regression test under `~/projects/herd/tools` that
(a) starts a dummy process whose argv contains the word "pytest" (e.g. a
`herdr agent prompt`-style command) and asserts `mutate.py`'s guard does not
report pytest running, and (b) starts a real `python3 -m pytest` process and
asserts the guard does detect it. The guard should match the pytest process
by executable + module/argument shape, not by substring scan of argv.

## Prediction

No `mutate-py-argv-match` events in the next run's friction lines; the
regression suite passes on a fresh clone before the run starts.
