# Design — team

**Catalog and cards are data; the skill points at them.** A session reads its
card and its packet, not the whole skill (team design §2). The skill keeps the
loop; the cards keep each role's contract.

**Gates check structure only.** `team.py gate` reads the run log and review
files; it cannot judge quality, and does not try (roadmap row X).

**The assignment is a run-log note.** Team design §2 says an assignment is
role + binding + session + candidate + scope + selected checks. `team.py
assign` writes it as a `note` whose text is `assignment <json>`, and `packet`
reads back the latest one for the role. Plan review round 1 F2 asked for this;
a dedicated run-log kind was narrowed away (ruling in the run log) because
only `packet` reads it. When an assignment exists, the packet's binding and
candidate come from it and the bindings file is not read, so a changed or
broken bindings file does not change recovery (plan review round 2 F1); an
explicit `--candidate` names a newer candidate.

**Scoped down on purpose.** Moving `probe.py` to bindings and renaming panes
touches every briefing and tool; it is a separate change (#51) so this one
stays reviewable. The librarian's harness binding and its pending obligation
move to #51 too (plan review round 1 F4).

**The catalog check requires, and does not limit.** It requires the twelve
roles, their fields (a null value counts as missing) and a card that is a `.md`
under `skill/cards/` or `hermes/`; a project may add a thirteenth role (build
review F3, rejected). An assignment keeps the reason when its binding was
unknown (build review F4).

## Rejected

- Generating SKILL.md from the cards now: a large rewrite of the live loop in
  the middle of a run.
