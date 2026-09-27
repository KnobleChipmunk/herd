# Design — herd setup

**`herdsetup.py`, not `setup.py`.** A file named `setup.py` is taken by
Python packaging tools; the command stays "herd setup" in the docs.

**Recommendations are data with provenance.** Each entry must say why, what
kind of evidence it rests on, and when; stale entries are flagged, not hidden.
Setup never forces an entry and never mixes brands for their own sake.

**Prompts are injectable.** `assisted` takes `ask` and `which`, so a
Claude-only, Codex-only or mixed machine is tested without a terminal.

## Rejected

- Refusing or re-asking a saved choice because its harness is not installed
  now (build review round 3, lead ruling): saved choices stay saved —
  rediscovery never overrides them (U4); with every role saved, setup still
  offers to keep them; `herdsetup.py validate` reports an uninstalled harness.

- Probing every candidate during setup: costs quota before the user chose;
  readiness stays a separate, consented step (#38).
