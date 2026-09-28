# Design

Use an additional textual sentinel because the existing workflow consumes review documents through agents. Count all unresolved confirmed findings when any is in the fence. The spec suffix controls immediate escalation; unresolved findings may never authorize DONE. The canonical builder card carries the authority restriction, and the lead ruling section carries the recovery sequence. Tests exercise the generated prompts consumed by both roles. No new parser or runtime state is introduced.

## Decisions

The lead decides whether to accept, narrow, or reject a finding using the existing ruling process. An accepted fence change requires reference validation and regenerated fences before builder work resumes.

## Plan review dispositions

Claude round 1 findings 1–3 are folded: the build-reviewer card permits the spec sentinel; the skill's role paragraphs and diagram agree; recovery runs every gate for the new build state and updates the handoff before another review. The existing fold start/done and suite-ok controls apply. Scope is full tier because the reviewer card makes four source files. Quoted replacements are generated from the verified reference rather than embedding the entire skill.

Build review round 1 finding 1 accepted: the lead may reject a reported finding. Only accepted fence changes require a reference fold and new build-state gates; rejection forwards the ruling to the next review with unchanged build-state evidence and an updated handoff. The ruling authorizes one extra review round.

Build review round 2: finding 1 accepted, builder card now says once per build-state. Finding 2 narrowed: the existing ban on builder test edits after the tests-first step remains. The lead installs verified regenerated test fences in the build worktree; the builder reapplies implementation fences. This preserves authority rather than widening builder permissions. One extra review round authorized.
