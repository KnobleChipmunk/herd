# Design — bindings

**YAML through PyYAML, imported lazily.** The consensus and the team design
name `bindings.yaml` and `herd.yaml`. PyYAML is installed here but herd
declares no dependencies; the import happens only when a bindings file is
read, and its absence fails with `pip install pyyaml`. Machines without a
bindings file never import it (preflight keeps its fixed list).

**Adapters are code, not config.** Argument vectors are built in
`bindings.py` per harness; the YAML never holds a command line, so a config
file cannot run arbitrary shell (consensus U2).

**Readiness is several observations.** Installed, auth and usable stay apart
so a timeout is never read as "no access", and a local provider is not marked
logged out. The classifier matches known phrases and answers `unknown`
otherwise.

**Fallback is the user's chain.** `choose` walks the binding and its listed
fallbacks only; it labels each one it passes over transient (rate-limited,
unreachable, unknown, not-probed) or permanent (model-denied, needs-login,
not-installed).

**Lead rulings (plan review round 1, in the run log).** F1 NARROWED: identity
fields an adapter cannot honor are rejected at validation instead of ignored;
honoring them comes with the adapters that need them. F2 NARROWED: project
capability requirements arrive with `herd.yaml` (#40/#51); this change routes
`ready` through `resolve()` with an override and records the chosen binding.

## Rejected

- TOML via the standard library: renames what the consensus and #31 fixed as
  YAML, and needs a hand-written writer for `herd setup`.
- Migrating `probe.py` now: #40 retires the Roster table; changing both twice
  would churn the loop mid-roadmap.
