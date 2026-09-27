## ADDED Requirements

### Requirement: Operator attention items
The attention rules SHALL raise operator items for open decisions from any run, blocked panes (one per episode), ready PRs of the latest run, and a stalled run, and an informational item for run end.

#### Scenario: A decision left open by an earlier run
- **WHEN** a `decision-needed` has no later `decision-made` for its issue, in any run
- **THEN** an operator item `Decision needed: #<issue>` carries its text

#### Scenario: A permission dialog
- **WHEN** Herdr reports an agent `blocked`, in any tab
- **THEN** an operator item is raised whose key names the pane and its `state_change_seq`

### Requirement: Stall versus hold
The rules SHALL report a stalled run only when work is in flight, no agent in the run's tab is working, unknown or blocked, the log has been quiet for the stall window, and the run is open; an issue with an open decision is held and never raises a stall.

#### Scenario: A quiet run with nobody working
- **WHEN** an issue's latest progress is in flight, every agent in the tab is idle, and the last event is older than 20 minutes
- **THEN** an operator item `Run may be stalled` names the issue

#### Scenario: A held issue
- **WHEN** the in-flight issue has an open decision
- **THEN** no stall item is raised and the decision item remains

#### Scenario: An answered hold
- **WHEN** the decision is answered and the work is still unfinished and quiet past the window
- **THEN** the stall becomes eligible again

#### Scenario: A deliberate wait or an unknown observation
- **WHEN** the issue has an open `wait` with a reason, or `herdr agent list` failed, or the run tab is unknown
- **THEN** no stall item is raised

### Requirement: Lead items stay with the lead
A worker `blocked` event older than the overdue window SHALL become a lead item and SHALL never be sent to the operator.

#### Scenario: An aged worker block
- **WHEN** a `blocked` event is 20 minutes old with no later `done` or `pr-opened` for its issue
- **THEN** a lead item is shown and the watcher sends nothing for it

### Requirement: Each item is sent once
The watcher SHALL send each operator or informational item once across restarts, batch several ready PRs into one notification, and send informational items without a sound.

#### Scenario: A restart and a new decision
- **WHEN** the watcher runs twice on the same log and a new decision is then appended
- **THEN** the first decision was sent once and the new one is sent once

#### Scenario: A dropped notification
- **WHEN** Herdr reports the notification not shown (for example rate-limited)
- **THEN** the item is not recorded as sent and is retried on the next poll

#### Scenario: A second watcher
- **WHEN** a watcher already runs for the repository
- **THEN** a second one exits without sending

#### Scenario: A replaced log
- **WHEN** the log is replaced and a different event lands at a previously sent offset
- **THEN** the new event is sent

### Requirement: The monitor
The monitor SHALL list every agent in the workspace with its activity and role (or `unknown`), mark agents outside the run's tab, list each issue's latest progress with its age, and list what needs the operator.

#### Scenario: A mixed workspace
- **WHEN** agents run in the run's tab and another tab
- **THEN** every agent is listed and the other tab's are marked `(outside run)`

### Requirement: One open decision per issue
The run log SHALL refuse a `decision-needed` without an issue, or for an issue that already has an unanswered decision in any run.

#### Scenario: A second question
- **WHEN** #426 has an open decision and another `decision-needed` for #426 is added
- **THEN** it is refused and names the open question
