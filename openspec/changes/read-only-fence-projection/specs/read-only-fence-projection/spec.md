## ADDED Requirements

### Requirement: Project base text without executing the plan
The audit SHALL read pinned base git blobs, parse tasks with the existing parser, and apply documented rendered forms in memory only. It SHALL never write files or import/execute plan code. The original base mapping SHALL remain unchanged.

#### Scenario: A rendered inline anchor gained a newline
- **WHEN** a unique source anchor matches the permitted shortened form
- **THEN** projection uses the documented source form and reports its anchor count

#### Scenario: Sequential replacements change one line twice
- **WHEN** a later step consumes an earlier inline replacement
- **THEN** projection evaluates each anchor against the preceding in-memory state

### Requirement: Report anchor counts and final parity
The audit SHALL report each step's anchor count (or not-applicable for file operations) and final touched-file parity with the reference. It SHALL reject absent or nonunique anchors, invalid file preconditions, unprojectable prose-only replacements and final drift. Empty plans and invalid base refs SHALL exit2.

#### Scenario: Local replacement succeeds but reference contains extra content
- **WHEN** projected final text differs from the reference
- **THEN** the audit reports the path and fails

### Requirement: Make the audit the plan review path
The reviewer card SHALL name the exact read-only invocation, its success line and its boundary. The skill brief SHALL direct the reviewer to that command instead of rebuilding the projection. The existing final-build CLI SHALL retain its behavior.

#### Scenario: A reviewer needs to check fences
- **WHEN** the lead supplies tasks, reference worktree and pinned base
- **THEN** the reviewer runs the documented command and investigates mismatches without applying or executing plan code
