## ADDED Requirements

### Requirement: Fence-owned findings block a clean review
The reviewer SHALL tag confirmed findings requiring byte-exact fence changes "in the fence" and SHALL keep them unresolved until disposition or correction. When any remain, the sentinel SHALL be `FINDINGS: <n> (spec)`, counting all unresolved confirmed findings.

#### Scenario: A confirmed defect requires changing the reference
- **WHEN** its fix requires a byte-exact fence change
- **THEN** the reviewer returns the spec sentinel and the builder records friction and reports BLOCKED in the same round without editing the fence or spec

### Requirement: The lead regenerates a verified reference
The lead SHALL fold accepted fixes into the reference, rerun affected tests and mutations, regenerate fences and verify parity and install any regenerated test fences in the build worktree before the builder reapplies affected implementation files.

#### Scenario: The lead accepts a fence-owned fix
- **WHEN** the lead validates and regenerates the reference fences
- **THEN** the lead installs any regenerated test fences and the builder reapplies the affected implementation files, runs every gate for the new build state, updates the handoff, and resumes review within the authorized cap

#### Scenario: The lead rejects the reported finding
- **WHEN** the lead rejects a fence-owned finding
- **THEN** the builder forwards the ruling to the next review without waiting for a fold, preserves unchanged build-state evidence, and updates the handoff with the ruling
