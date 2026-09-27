## ADDED Requirements

### Requirement: One open run per repository
The run log SHALL refuse a `run-start` while the latest run has no `run-end`, and the check and the append SHALL be atomic.

#### Scenario: A second run-start while a run is open
- **WHEN** a run is open and `runlog.py add run-start` is called
- **THEN** it exits 2, appends nothing, and prints the open run's id and the command `runlog.py close --reason`

#### Scenario: Concurrent run-starts
- **WHEN** several `run-start` calls race on a log with no open run
- **THEN** exactly one succeeds and the rest are refused

#### Scenario: An append that read the log before a close
- **WHEN** an ordinary append has read the log while run A is open, and a `close` and a new `run-start` are attempted before it writes
- **THEN** the append's line lands before the close is evaluated, it carries A's id, the close is refused as `no open run`, and the new run B stays open

#### Scenario: A run-start after run-end
- **WHEN** the latest run has a `run-end`
- **THEN** `run-start` succeeds and opens a new run with a new id

### Requirement: Crash close
`runlog.py close --reason <why>` SHALL end the open run with a `run-end` whose text is `closed: <why>`, and SHALL be refused when no run is open.

#### Scenario: Closing a crashed run
- **WHEN** a run is open and `close --reason "crashed at 3am"` is called
- **THEN** a `run-end` with text `closed: crashed at 3am` is appended to that run, and a following `run-start` succeeds

#### Scenario: Nothing to close
- **WHEN** the log is empty or its latest run has a `run-end`
- **THEN** `close` exits 2 and prints `no open run`

### Requirement: Events after run-end stay with the ended run
An event appended after `run-end` and before the next `run-start` SHALL carry the ended run's id.

#### Scenario: merge_stack's librarian note
- **WHEN** a `note` is appended after `run-end`
- **THEN** it succeeds and its `run` equals the ended run's id

### Requirement: Unique run ids
Every `run-start` SHALL get a run id unused in the log, equal to its own `ts`.

#### Scenario: Two runs in the same instant
- **WHEN** the clock returns the same instant for two successive runs
- **THEN** their run ids differ, and each equals its `run-start` event's `ts`

### Requirement: Unresolved decisions survive a new run
`status` SHALL list a `decision-needed` from any run until a later `decision-made` for the same issue, marking decisions from earlier runs with their run id.

#### Scenario: A decision left open by the previous run
- **WHEN** run A records `decision-needed` for #426 and ends, and run B starts
- **THEN** `status` prints `OPEN decision #426: <text> (from run <A id>)`

#### Scenario: Resolved in a later run
- **WHEN** run B records `decision-made` for #426
- **THEN** `status` no longer lists #426 as open

#### Scenario: Only a later answer for the same issue resolves
- **WHEN** a `decision-made` for #426 comes before the `decision-needed`, or a `decision-made` is recorded for a different issue
- **THEN** `status` still lists #426 as open

#### Scenario: Sessions are not progress
- **WHEN** a `session` event names an issue that has a progress event
- **THEN** `status` shows the progress event and does not render the session

### Requirement: Session outcomes
The run log SHALL record a `session` event with agent, logical role, and an outcome from `resumed | fresh | failed | unknown`.

#### Scenario: A resumed builder
- **WHEN** `add session --agent pi_build --role builder --outcome resumed` is called in an open run
- **THEN** it exits 0 and the event carries agent, role and outcome; each of the four outcomes is accepted

#### Scenario: Invalid or missing fields
- **WHEN** `--outcome` is not one of the four values, or any of `--agent`, `--role`, `--outcome` is missing
- **THEN** the call is refused and nothing is appended

### Requirement: Loop scope is stated
The herd skill SHALL state that it governs `/herd` runs and wins where it differs from DEVLOOP.md.

#### Scenario: Reading the skill
- **WHEN** the skill text is read
- **THEN** the paragraph under its title names DEVLOOP.md and says this skill wins inside a `/herd` run
