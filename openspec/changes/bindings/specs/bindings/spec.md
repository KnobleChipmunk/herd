## ADDED Requirements

### Requirement: Validated machine-local bindings
The bindings file SHALL be rejected, with a reason, for an unsupported or missing version, an unknown key, an unknown role, an unsupported harness, or a binding without harness or model.

#### Scenario: A secret in the file
- **WHEN** a binding carries an `api_key` key
- **THEN** the file is rejected as having an unknown key

### Requirement: Precedence
A role SHALL resolve to the invocation flag, else the user file, else the portable default, else nothing.

#### Scenario: All three present
- **WHEN** a flag, a user binding and a default exist for a role
- **THEN** the flag wins

### Requirement: Readiness keeps its observations apart
Readiness SHALL report installed, auth and usable separately; a timeout SHALL be `unknown`; a local provider's auth SHALL be `not-required`; without probe consent no probe SHALL run.

#### Scenario: A rate limit
- **WHEN** the probe fails with a rate-limit message
- **THEN** usable is `rate-limited`, and a fallback marks it transient

### Requirement: Fallback stays in the listed chain
Choosing a binding SHALL try only the role's binding and its listed fallbacks, in order.

#### Scenario: Nothing usable
- **WHEN** every binding in the chain fails
- **THEN** no binding is chosen and every reason is listed

### Requirement: Preflight follows the bindings
With a bindings file, preflight SHALL require only the base tools and the harnesses the file binds, fallbacks included.

#### Scenario: A Claude-only machine
- **WHEN** the file binds only Claude Code
- **THEN** preflight does not require `pi` or `codex`
