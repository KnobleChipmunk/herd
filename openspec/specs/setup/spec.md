# setup Specification

## Purpose
TBD - created by archiving change setup. Update Purpose after archive.
## Requirements
### Requirement: Assisted setup per role
Assisted setup SHALL ask for each required role from the harnesses installed on the machine, keep a saved choice as the default, re-ask on an unusable answer, show the selected bindings and every author/evaluator pair's diversity (same, different, unknown) before the consent question, warn on a same-model pair, and save only after the user confirms a preview.

#### Scenario: A Claude-only machine
- **WHEN** only Claude Code is installed
- **THEN** every offered choice is a Claude binding, and choosing one model for builder and build reviewer prints a same-model warning

#### Scenario: Declined save
- **WHEN** the user declines the save
- **THEN** nothing is written and the preview was shown

### Requirement: Headless validation
`herdsetup.py validate` SHALL list, without prompting, a missing or invalid file, unbound required roles and uninstalled harnesses, and exit 1 when any exist.

#### Scenario: A half-configured machine
- **WHEN** the builder is bound to an uninstalled harness and the reviewers are unbound
- **THEN** each problem is listed and the exit code is 1

### Requirement: Recommendations with provenance
Every recommendation SHALL carry a reason, a source type from `official | preference | observed`, and a date; offers SHALL be limited to installed harnesses and flag entries older than the stale window.

#### Scenario: A stale entry
- **WHEN** an offered entry is older than the window
- **THEN** it is marked stale

