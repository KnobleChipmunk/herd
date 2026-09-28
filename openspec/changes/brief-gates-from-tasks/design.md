# Design

DEPENDS ON PR #66 at d6b0ed7. The CLI already knows the worktree and change, so tasks.md is the only gate-text input. Require exactly one nonempty level-two `## 0. Gates` heading outside backtick or tilde fences, copy through the next level-two heading outside fences, and normalize surrounding blank lines to a single trailing newline. Indented code with four spaces is not a heading. This bounded scan handles the generated plan format; it does not claim full CommonMark support.

Render both prompt documents before writing any coordination file so missing/ambiguous gates preserve previous generated outputs. Tests call the CLI twice with changed suite/mutation/fence literals and check both freshness and failed-regeneration preservation. Existing prompt tests now create tasks.md fixtures and use the new API. The old CLI is intentionally replaced, not silently ignored.

The generator copies authoritative evidence; the lead still measures and validates it. Full-suite and mutation counts inside the gate section are not inferred or executed by the generator. The lead uses a pinned SHA so regenerated review comparisons keep the actual branch base even if main advances.

## Plan review dispositions

F1 folded: the gate section contains one builder-local RED command and one count (30 failed, 3 passed). Intermediate development counts and the cross-module check are excluded from the gate contract. F2 folded: the fold procedure regenerates the briefing before fold done and resumption. F3 is recorded as the bounded-format limitation already declared above; F4 needs no change because the existing output spacing is valid Markdown.

## Build review ruling

Round 1 finding 1 ACCEPTED: trim blank-only boundary lines, preserving whitespace within retained lines. The focused regression fails with 1 failed, 32 passed on the pre-fold implementation. Lead installs the revised test; builder reapplies implementation and reruns gates. Lead ruling: preserve gate indentation within the bounded scanner; no broader Markdown parser is in scope.
