## ADDED Requirements

### Requirement: Owned work with a claim
A ticket SHALL open pending with one owner, and only that owner SHALL claim, block, close or hand it off.

#### Scenario: A non-owner claims
- **WHEN** someone other than the owner claims a pending ticket
- **THEN** the claim is refused and the ticket stays pending

#### Scenario: The owner claims
- **WHEN** the owner claims a pending or blocked ticket
- **THEN** it becomes in-progress

### Requirement: Closing with a reason
A ticket SHALL close only with a reason from `no-follow-on | denied | canceled | superseded | escalation`, or `handed_off_to` through a handoff; `escalation` SHALL name a target; a closed ticket SHALL stay closed.

#### Scenario: Escalation without a target
- **WHEN** the owner closes with `escalation` and no target
- **THEN** the close is refused

### Requirement: Transactional handoff
A handoff SHALL close the ticket as `handed_off_to` its new owner and open a pending successor, inheriting the parent, in one write under the run-log lock.

#### Scenario: Builder hands to reviewer
- **WHEN** the builder hands off T1 to the reviewer
- **THEN** T1 is closed with `handed_off_to reviewer`, and a new pending ticket owned by the reviewer names T1 as its predecessor, written together

### Requirement: The ticket page
`page <id>` SHALL write a Markdown page at `<git common dir>/herd/tickets/<id>.md` from the records, with a verdict that is PASS only when every recorded check passed.

#### Scenario: An omitted check
- **WHEN** one check passed and another is omitted, blocked, failed or not-checked
- **THEN** the page's verdict is NOT PASS

#### Scenario: Passes on two candidates
- **WHEN** every check passed but on different candidates
- **THEN** the verdict is NOT PASS and names both

### Requirement: One durable handoff record
A handoff SHALL be written as one record; an incomplete last line SHALL be ignored when read and dropped before the next write; blank owners, actors and targets SHALL be refused.

#### Scenario: A crash mid-write
- **WHEN** the store ends with a line without its newline
- **THEN** readers ignore it and the next write removes it first
