# Proposal: Herdr notification socket blocked by the sandbox

Status: applied https://github.com/KnobleChipmunk/herd/pull/28 2026-09-26

## Class

sandbox-socket-denied — Herdr notification socket blocked by the sandbox

Events (friction ledger):
- 2026-09-25: "Herdr prompt hit sandbox socket PermissionDenied and needed an escalated retry, costing about 20 seconds on the required signoff."
- 2026-09-25: "Clean round-3 herdr agent prompt to w1:p2D failed in the sandbox with Operation not permitted; an escalated retry succeeded after the review was already complete."

## Proposed change

Change the tooling that scripts the reviewer handoff in `~/projects/herd/tools`
so the signoff command is issued with its required execution permission stated
up front (escalated, non-sandbox), rather than being run sandboxed and retried
after a socket PermissionDenied. The handoff should treat exactly one
PermissionDenied on the Herdr socket as a scripted escalation, not a
diagnosable failure — the signoff must not fail after the review is complete.

## Prediction

No `sandbox-socket-denied` events in the next run's friction lines; the clean-
round signoff command succeeds on its first attempt.
2026-09-26: missed — two events in the #459 run (459-1: herdr signoff to w1:p2D
failed in the sandbox with PermissionDenied, escalated retry succeeded; 459-4:
same signoff command failed with Operation not permitted after REVIEW CLEAN).
