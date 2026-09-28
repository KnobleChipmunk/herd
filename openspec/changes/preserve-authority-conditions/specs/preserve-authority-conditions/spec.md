## ADDED Requirements

### Requirement: Review authority rules against their source
When a rule is extracted, reformatted, or rewritten, the plan reviewer SHALL compare actor, action, scope, and authorization condition against the source skill, checking tightened prohibitions and relaxed permissions.

#### Scenario: A card changes a conditional prohibition
- **WHEN** a rewritten card drops the operator-authorization exception
- **THEN** the reviewer identifies the changed condition before approving

### Requirement: Require evidence that the condition survives
The reviewer SHALL require a focused assertion of the surviving authorization condition; existing coverage may be cited.

#### Scenario: Protected pushes already have regression coverage
- **WHEN** the existing assertion covers the rewritten rule
- **THEN** the plan cites that assertion rather than adding a duplicate
