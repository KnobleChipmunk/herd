## ADDED Requirements

### Requirement: A transparent collector
The collector SHALL record the pane's context use and SHALL pass the wrapped status line's output and exit code through unchanged; a collector error SHALL NOT change the status line.

#### Scenario: Bad input
- **WHEN** stdin is not JSON
- **THEN** nothing is recorded and the wrapped command's output is unchanged

### Requirement: Reversible install
`install` SHALL back up settings.json before wrapping, SHALL not wrap twice, and `uninstall` SHALL restore the original command.

#### Scenario: Install then uninstall
- **WHEN** install and then uninstall run
- **THEN** the status line command is the original again and a dated backup exists

### Requirement: Context in the monitor
The monitor SHALL show each pane's latest recorded context percentage with its age, and `context unknown` when there is no sample or the percentage is null.

#### Scenario: A pi pane
- **WHEN** a pane has no sample
- **THEN** its row says `context unknown`
