## ADDED Requirements

### Requirement: Briefing gates come from the current plan
The generator SHALL copy the named change's single nonempty `## 0. Gates` section from tasks.md on every generation and SHALL accept no separate gate-text input.

#### Scenario: An approved plan is amended
- **WHEN** tasks.md changes its suite count, mutation names, or fence count and the lead regenerates the briefing
- **THEN** the new literals appear and the old ones do not remain in its measured gates

### Requirement: Invalid gate sources preserve previous outputs
The generator SHALL reject an unreadable tasks file or missing, empty, or repeated gate section before writing any generated file. Fenced-code headings and four-space-indented code SHALL NOT be treated as gate-section headings.

#### Scenario: The plan has no usable gate section
- **WHEN** generation encounters a missing or ambiguous section
- **THEN** it reports the tasks path and required heading while leaving existing outputs unchanged

#### Scenario: A code example contains a section heading
- **WHEN** the heading occurs inside a backtick or tilde code fence
- **THEN** it does not start or end the gate section

### Requirement: Briefings are regenerated after amendments
The lead SHALL generate after plan approval and regenerate after any amendment before the next dispatch, using the original pinned base SHA.

#### Scenario: A lead ruling amends tasks.md
- **WHEN** the reference and plan have been revalidated
- **THEN** the lead regenerates the briefing from current tasks.md before resuming the builder
