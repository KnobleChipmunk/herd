## ADDED Requirements

### Requirement: Map every governing requirement
Before generating fences, the lead SHALL create a table checked against the issue and design. Each governing requirement SHALL name its source section, implementing step and acceptance evidence, or a linked deferral.

#### Scenario: Tests omit a requirement
- **WHEN** the tests pass but a source requirement has no implementation or deferral
- **THEN** the table check identifies the omission before independent review

### Requirement: Give new commands a caller
The table SHALL name a caller in the skill or a card for every new command. The independent plan reviewer SHALL verify both the table and command callers against the issue and design.

#### Scenario: A new command is never invoked
- **WHEN** a planned command has no caller in the skill or a card
- **THEN** the lead or plan reviewer identifies the missing caller before approval
