# team Specification

## Purpose
TBD - created by archiving change team. Update Purpose after archive.
## Requirements
### Requirement: A portable role catalog
`skill/herd.yaml` SHALL list every role with where it runs, its binding, its card, its activation, purpose, outputs, prohibitions, capabilities, skip conditions, allowed operations, time limit, cost limit, exclusions and an advisory flag, with no vendor names, and `team.py check` SHALL reject a catalog that lacks one of the twelve roles, moves a role between lead-held and own-session, or whose role lacks these, runs a lead-held role in its own session, names an unknown binding or card, names a card that is not a `.md` under `skill/cards/` or `hermes/`, or lets a role evaluate itself; a null field counts as missing, and a project may add roles beyond the twelve.

#### Scenario: A role evaluating itself
- **WHEN** the build reviewer lists itself under `evaluates`
- **THEN** the catalog is rejected

### Requirement: Role cards
Every own-session role except the librarian SHALL have a card with the eight fields, the lead card SHALL have a section per lead-held role, and every evaluator card SHALL state the same hard independence rule.

#### Scenario: A card missing a field
- **WHEN** a card lacks its Evidence heading
- **THEN** the card test fails

### Requirement: Loop gates
Dispatch SHALL require `spec-approved` and a last plan review of APPROVE; a further review round SHALL be refused at the cap of 2 plus one per ruling; a review file SHALL name its candidate with a value on the `Candidate:` line itself.

#### Scenario: A REVISE plan review
- **WHEN** the last plan review of the issue is REVISE
- **THEN** the dispatch gate refuses and names the verdict

#### Scenario: A blank candidate line
- **WHEN** a review file's `Candidate:` line is empty and the verdict follows on a later line
- **THEN** the review-file gate refuses

### Requirement: The step packet
`team.py assign` SHALL record a role's resolved assignment (role, binding, session, candidate, scope, selected checks) in the run log and refuse an unknown role; `team.py packet` SHALL give a role's card, current step, candidate, return route, independence rule, binding, prohibitions and latest assignment, showing `unknown` where no record exists.

#### Scenario: No bindings file
- **WHEN** the machine has no bindings file
- **THEN** the packet's binding is `unknown (no bindings file)`

#### Scenario: Recovery after compaction
- **WHEN** the lead recorded an assignment for the builder at dispatch
- **THEN** the builder's packet carries that assignment, and another role's packet shows `unknown`

#### Scenario: The bindings file changed after dispatch
- **WHEN** the bindings file is edited, broken or removed after the assignment was recorded
- **THEN** the packet's binding and candidate are still the recorded ones

