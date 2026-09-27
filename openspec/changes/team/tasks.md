# Tasks — team: catalog, cards, packet, gates (#40)

Tier: **full**. DEPENDS ON #41: the branch is stacked on `feat/41-context`.
Fences are generated from the lead's pre-executed tree; `tools/fencecheck.py` must print `FENCES OK (16 steps)`.

## 1. Tests first — apply T1, T2, then observe RED

- [ ] **T1** `tests/test_team.py` — acceptance tests: catalog, cards, gates, packet

Create this file with exactly this body (byte-exact, ends with one newline):

```python
import pathlib

import pytest

import runlog
import team

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent / "skill"
FIELDS = ("Purpose", "Inputs", "Outputs", "Activation", "Scope", "Evidence", "Authority", "Exclusions")


# --- the catalog ------------------------------------------------------------

def test_the_shipped_catalog_is_valid():
    assert team.validate(team.load()) == []


def test_the_catalog_names_no_vendor():
    text = (SKILL_DIR / "herd.yaml").read_text().lower()
    assert not [v for v in ("claude", "codex", "opus", "sonnet", "fable", "gpt", "ollama", "qwen") if v in text]


def test_every_own_session_card_carries_the_eight_fields_and_the_lead_card_its_five_roles():
    catalog = team.load()
    for name, role in catalog["roles"].items():
        card = (SKILL_DIR / role["card"]).resolve()
        assert card.exists(), name
        if role["runs_in"] == "own-session" and name != "librarian":
            text = card.read_text()
            assert all(f"## {f}\n" in text for f in FIELDS), name
    lead = (SKILL_DIR / "cards" / "lead.md").read_text()
    assert all(f"## {h}\n" in lead for h in ("Orchestrator", "Architect", "Planner", "Product intake", "Release prep"))
    for section in lead.split("\n## ")[1:]:
        assert all(f"- **{f}.** " in section for f in FIELDS), section.splitlines()[0]


@pytest.mark.parametrize("change, error", [
    (lambda d: d["roles"]["builder"].pop("card"), "builder: missing card"),
    (lambda d: d["roles"]["builder"].update(runs_in="sometimes"), "builder: runs_in must be own-session or lead-held"),
    (lambda d: d["roles"]["builder"].update(binding="barista"), "builder: unknown binding 'barista'"),
    (lambda d: d["roles"]["build_reviewer"].update(evaluates=["builder", "build_reviewer"]),
     "build_reviewer: a role cannot evaluate itself"),
    (lambda d: d["roles"]["qa"].update(evaluates=["nobody"]), "qa: evaluates unknown role 'nobody'"),
    (lambda d: d["roles"]["architect"].update(runs_in="own-session"), "architect: a lead-held role"),
    (lambda d: d["roles"].pop("librarian"), "missing role librarian"),
    (lambda d: d["roles"]["qa"].update(runs_in="lead-held"), "qa: an own-session role"),
    (lambda d: d["roles"]["builder"].update(binding=None), "builder: missing binding"),
    (lambda d: d["roles"]["builder"].update(card=None), "builder: missing card"),
    (lambda d: d["roles"]["builder"].update(card="../pyproject.toml"), "builder: card ../pyproject.toml is not a role card"),
    (lambda d: d["roles"]["builder"].update(card="../README.md"), "builder: card ../README.md is not a role card"),
])
def test_an_invalid_catalog_is_rejected_with_a_reason(change, error):
    doc = team.load()
    change(doc)
    assert any(error in e for e in team.validate(doc))


# --- gates (row X) -------------------------------------------------------------

def add(repo, *args):
    return runlog.main(["add", *args, "--repo", str(repo)])


def test_dispatch_needs_an_approved_spec_and_an_approving_last_plan_review(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    assert team.main(["gate", "dispatch", "--issue", "40", "--repo", str(main)]) == 2
    assert "no spec-approved for #40" in capsys.readouterr().out
    add(main, "spec-approved", "--issue", "40", "--tier", "full")
    add(main, "plan-review", "--issue", "40", "--round", "1", "--verdict", "REVISE (3)")
    assert team.main(["gate", "dispatch", "--issue", "40", "--repo", str(main)]) == 2
    assert "the last plan review of #40 is REVISE (3), not APPROVE" in capsys.readouterr().out
    add(main, "plan-review", "--issue", "40", "--round", "2", "--verdict", "APPROVE")
    assert team.main(["gate", "dispatch", "--issue", "40", "--repo", str(main)]) == 0


def test_the_review_round_cap_escalates_and_a_ruling_grants_one_more(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    for n in ("1", "2"):
        add(main, "review-round", "--issue", "40", "--round", n, "--verdict", "FINDINGS: 1")
    assert team.main(["gate", "review", "--issue", "40", "--repo", str(main)]) == 2
    assert "BLOCKED: #40 reached the review cap (2 rounds)" in capsys.readouterr().out
    add(main, "ruling", "--issue", "40", "--text", "narrow F2")
    assert team.main(["gate", "review", "--issue", "40", "--repo", str(main)]) == 0
    add(main, "review-round", "--issue", "40", "--round", "3", "--verdict", "FINDINGS: 1")
    assert team.main(["gate", "review", "--issue", "40", "--repo", str(main)]) == 2


def test_a_review_file_must_name_its_candidate(tmp_path, capsys):
    f = tmp_path / "REVIEW-40-round-1.md"
    f.write_text("Findings...\n\nREVIEW CLEAN\n")
    assert team.main(["gate", "review-file", str(f)]) == 2
    assert "names no candidate" in capsys.readouterr().out
    f.write_text("Candidate: 55356d9 + worktree diff\n\nREVIEW CLEAN\n")
    assert team.main(["gate", "review-file", str(f)]) == 0


# --- the current-step / recovery packet (row C) ------------------------------------

def test_the_packet_names_role_card_step_return_route_and_independence(repo_with_worktree, tmp_path):
    main, _ = repo_with_worktree
    add(main, "run-start")
    add(main, "dispatched", "--issue", "40")
    bindings_file = tmp_path / "b.yaml"
    bindings_file.write_text("version: 1\nroles:\n  build_reviewer: {harness: codex, model: m1}\n")
    p = team.packet("build_reviewer", issue="40", repo=main, candidate="abc123", bindings_file=bindings_file)
    assert p["role"] == "build_reviewer" and p["card"].endswith("cards/build-reviewer.md")
    assert p["step"] == "dispatched" and p["candidate"] == "abc123" and p["returns_to"] == "builder"
    assert p["independence"] == "fresh context whatever pane or model; must not have authored: builder, planner"
    assert p["binding"] == {"harness": "codex", "model": "m1"}


def test_a_lead_held_role_resolves_the_lead_binding_and_unknowns_stay_unknown(repo_with_worktree, tmp_path):
    main, _ = repo_with_worktree
    p = team.packet("planner", issue="99", repo=main, candidate=None, bindings_file=tmp_path / "missing.yaml")
    assert p["binding"] == "unknown (no bindings file)" and p["step"] == "unknown" and p["candidate"] == "unknown"
    assert p["independence"] == "none required"


def test_the_packet_cli_prints_every_field(repo_with_worktree, tmp_path, capsys):
    main, _ = repo_with_worktree
    assert team.main(["packet", "qa", "--issue", "40", "--repo", str(main), "--bindings", str(tmp_path / "x")]) == 0
    out = capsys.readouterr().out
    for field in ("role:", "card:", "step:", "candidate:", "returns_to:", "independence:", "binding:", "may_not:"):
        assert field in out


# --- plan review #40 round 1 -------------------------------------------------

def test_the_catalog_requires_the_policy_fields_of_team_design_section_2():
    doc = team.load()
    doc["roles"]["qa"].pop("skip_when")
    assert "qa: missing skip_when" in team.validate(doc)
    assert team.load()["roles"]["dogfood"]["time_limit_minutes"] == 20


def test_an_assignment_is_recorded_at_dispatch_and_recovered_by_the_packet(repo_with_worktree, tmp_path, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    add(main, "dispatched", "--issue", "40")
    b = tmp_path / "b.yaml"
    b.write_text("version: 1\nroles:\n  builder: {harness: pi, provider: ollama, model: m}\n")
    assert team.main(["assign", "builder", "--issue", "40", "--session", "pi_build", "--candidate", "abc123",
                      "--scope", "tools/team.py", "--checks", "suite,ruff", "--bindings", str(b), "--repo", str(main)]) == 0
    p = team.packet("builder", issue="40", repo=main, candidate=None, bindings_file=b)
    assert p["assignment"] == {"role": "builder", "binding": {"harness": "pi", "provider": "ollama", "model": "m"},
                               "session": "pi_build", "candidate": "abc123", "scope": "tools/team.py",
                               "checks": ["suite", "ruff"]}
    assert team.packet("qa", issue="40", repo=main, candidate=None, bindings_file=b)["assignment"].startswith("unknown")


def test_recovery_reads_the_recorded_assignment_not_the_current_bindings_file(repo_with_worktree, tmp_path):
    main, _ = repo_with_worktree
    add(main, "run-start")
    b = tmp_path / "b.yaml"
    b.write_text("version: 1\nroles:\n  builder: {harness: pi, provider: ollama, model: m}\n")
    assert team.main(["assign", "builder", "--issue", "40", "--session", "pi_build", "--candidate", "abc123",
                      "--bindings", str(b), "--repo", str(main)]) == 0
    recorded = {"harness": "pi", "provider": "ollama", "model": "m"}
    for bindings_text in ("version: 1\nroles:\n  builder: {harness: pi, provider: ollama, model: other}\n",
                          "not: [valid", None):
        if bindings_text is None:
            b.unlink()
        else:
            b.write_text(bindings_text)
        p = team.packet("builder", issue="40", repo=main, candidate=None, bindings_file=b)
        assert p["binding"] == recorded and p["candidate"] == "abc123"
    assert team.packet("builder", issue="40", repo=main, candidate="def456", bindings_file=b)["candidate"] == "def456"


def test_release_prep_keeps_the_operator_authorization_for_protected_pushes():
    section = (SKILL_DIR / "cards" / "lead.md").read_text().split("## Release prep\n")[1]
    assert "only explicit operator authorization allows them" in section
    may_not = team.load()["roles"]["release_prep"]["may_not"]
    assert [m for m in may_not if m.startswith(("push to main", "force-push"))] == [
        "push to main or a branch the loop did not create, without explicit operator authorization",
        "force-push without explicit operator authorization"]


def test_a_project_may_add_a_role_beyond_the_twelve():
    doc = team.load()
    doc["roles"]["security_reviewer"] = dict(doc["roles"]["designer"])
    assert team.validate(doc) == []


def test_an_assignment_without_a_bindings_file_keeps_the_reason(repo_with_worktree, tmp_path):
    main, _ = repo_with_worktree
    add(main, "run-start")
    assert team.main(["assign", "qa", "--issue", "40", "--session", "qa_1", "--bindings", str(tmp_path / "none.yaml"),
                      "--repo", str(main)]) == 0
    p = team.packet("qa", issue="40", repo=main, candidate=None, bindings_file=tmp_path / "none.yaml")
    assert p["binding"] == p["assignment"]["binding"] == "unknown (no bindings file)"


def test_an_unknown_role_cannot_be_assigned(repo_with_worktree, capsys):
    main, _ = repo_with_worktree
    add(main, "run-start")
    assert team.main(["assign", "barista", "--issue", "40", "--session", "x", "--repo", str(main)]) == 2
    assert "unknown role 'barista'" in capsys.readouterr().out


def test_the_build_reviewer_card_asks_for_the_candidate_line_the_gate_checks():
    assert "opening with a `Candidate: <commit or tree>` line" in (SKILL_DIR / "cards" / "build-reviewer.md").read_text()


@pytest.mark.parametrize("text", ["Candidate:\n\nREVIEW CLEAN\n", "Candidate:   \nREVIEW CLEAN\n",
                                  "candidate:\nverdict: ok\n"])
def test_a_blank_candidate_header_is_refused(tmp_path, text):
    f = tmp_path / "REVIEW-40-round-1.md"
    f.write_text(text)
    assert team.main(["gate", "review-file", str(f)]) == 2


def test_every_evaluator_card_states_the_same_hard_independence_rule():
    for c in ("plan-reviewer.md", "build-reviewer.md", "qa.md"):
        text = (SKILL_DIR / "cards" / c).read_text()
        assert "must not be an author of what it judges" in text and "fresh context" in text

```

- [ ] **T2** `tests/test_skill_text.py` — the skill points at the catalog, cards and gates

Append exactly this text at the END of the file. The fence below BEGINS with the blank lines that separate it from the existing last line — keep them. The file must end with one newline:

```python

def test_the_skill_points_at_the_catalog_the_cards_and_the_gates():
    text = " ".join(SKILL.read_text().split())
    roster = text[text.index("## Roster"): text.index("## Before an unattended run")]
    roles = text[text.index("## Roles and hand-offs"): text.index("## The loop, end to end")]
    assert "skill/herd.yaml" in roster and "#51" in roster
    assert "skill/cards/" in roles and "team.py packet" in roles and "team.py gate dispatch" in roles
    assert "an evaluator (plan reviewer, build reviewer, QA) first gets a fresh context" in text
    assert "team.py assign" in roles and roles.index("team.py assign") < roles.index("team.py packet")

```

RED after T1–T2: `tests/test_team.py` fails to collect (no module `team`); the new skill-text test fails.

## 2. Implementation — apply I1–I14

- [ ] **I1** `pyproject.toml` — register the new module for isort

Find this exact text (it occurs exactly once):

```python
"probe", "runlog", "tickets"]
```

Replace it with exactly:

```python
"probe", "runlog", "team", "tickets"]
```

- [ ] **I2** `skill/herd.yaml` — the portable role catalog

Create this file with exactly this body (byte-exact, ends with one newline):

```python
# The portable role catalog (#40; docs/team-design.md §2). No vendor names: which harness and model
# plays a role is a machine-local binding (~/.config/herd/bindings.yaml, #38). Every constraint here is
# advisory until a tool enforces it; `enforced_by` names the tool when one does.
version: 1
roles:
  orchestrator:
    runs_in: lead-held
    binding: lead
    card: cards/lead.md
    activation: always
    purpose: route work, rule on disputes, give the operator one consolidated report
    outputs:
    - rulings
    - run log checkpoints
    - closing report
    may_not:
    - hand off operator gates
    capabilities:
    - repo read/write
    - git and gh
    - Herdr control
    skip_when: never
    allowed_operations:
    - route
    - rule
    - report
    - commit/push/PR on loop branches
    time_limit_minutes: unset
    cost_limit: unset
    exclusions: []
    advisory: true
  architect:
    runs_in: lead-held
    binding: lead
    card: cards/lead.md
    activation: intake; cross-ticket findings
    purpose: decide interfaces, invariants and non-goals across tickets
    outputs:
    - design.md decisions
    may_not:
    - change scope or product behavior without the operator
    capabilities:
    - repo read
    skip_when: a ticket with no cross-ticket decision
    allowed_operations:
    - write design.md decisions
    time_limit_minutes: unset
    cost_limit: unset
    exclusions: []
    advisory: true
  planner:
    runs_in: lead-held
    binding: lead
    card: cards/lead.md
    activation: every ticket
    purpose: write the openspec change and pre-execute it
    outputs:
    - openspec change
    - pre-execution evidence
    - byte-exact fences
    may_not:
    - skip pre-execution on the full tier
    capabilities:
    - repo read/write
    - tests
    - scratch worktree
    skip_when: never
    allowed_operations:
    - write the openspec change
    - pre-execute in a scratch worktree
    time_limit_minutes: unset
    cost_limit: unset
    exclusions: []
    advisory: true
  product_intake:
    runs_in: lead-held
    binding: lead
    card: cards/lead.md
    activation: operator input; dogfood findings
    purpose: turn requests and findings into ranked tickets
    outputs:
    - tickets
    may_not:
    - self-approve new scope
    capabilities:
    - gh issues
    skip_when: no new input or findings
    allowed_operations:
    - create and rank tickets
    time_limit_minutes: unset
    cost_limit: unset
    exclusions: []
    advisory: true
  release_prep:
    runs_in: lead-held
    binding: lead
    card: cards/lead.md
    activation: after the final review
    purpose: commit, push and open the PR on branches this loop created
    outputs:
    - commit
    - PR
    may_not:
    - merge
    - publish
    - push to main or a branch the loop did not create, without explicit operator authorization
    - force-push without explicit operator authorization
    capabilities:
    - git and gh
    skip_when: no reviewed candidate
    allowed_operations:
    - commit
    - normal push
    - open a PR on loop branches
    time_limit_minutes: unset
    cost_limit: unset
    exclusions: []
    advisory: true
  builder:
    runs_in: own-session
    binding: builder
    card: cards/builder.md
    activation: dispatch
    purpose: implement the spec in one worktree
    outputs:
    - implementation
    - handoff
    returns_to: build_reviewer
    may_not:
    - commit
    - push
    - leave the worktree
    - edit a test after the tests-first step
    capabilities:
    - file edits
    - shell
    - tests
    skip_when: never
    allowed_operations:
    - edit the briefing's allowed files
    - run gates and mutations
    time_limit_minutes: unset
    cost_limit: unset
    exclusions: []
    advisory: true
  plan_reviewer:
    runs_in: own-session
    binding: plan_reviewer
    card: cards/plan-reviewer.md
    activation: every spec
    purpose: challenge the spec before the build
    outputs:
    - PLAN-REVIEW file
    returns_to: planner
    evaluates:
    - planner
    may_not:
    - execute the plan or its tests
    capabilities:
    - repo read
    - git blobs
    skip_when: never
    allowed_operations:
    - read
    - reason
    - write its review file
    time_limit_minutes: unset
    cost_limit: unset
    exclusions:
    - must not have authored the work it judges
    - fresh context
    advisory: true
  build_reviewer:
    runs_in: own-session
    binding: build_reviewer
    card: cards/build-reviewer.md
    activation: each build round
    purpose: review the build against the spec
    outputs:
    - REVIEW file
    returns_to: builder
    evaluates:
    - builder
    - planner
    may_not:
    - edit the candidate
    capabilities:
    - repo read
    - shell
    - tests
    skip_when: never
    allowed_operations:
    - run fencecheck, touched tests, scratch mutation drives
    - write its review file
    time_limit_minutes: unset
    cost_limit: unset
    exclusions:
    - must not have authored the work it judges
    - fresh context
    advisory: true
  qa:
    runs_in: own-session
    binding: qa
    card: cards/qa.md
    activation: chosen at planning by journey and risk; skip reason recorded
    purpose: exercise the promised outcome on a frozen candidate
    outputs:
    - QA report
    - ticket checks
    returns_to: orchestrator
    evaluates:
    - builder
    - planner
    may_not:
    - repair the candidate it certifies
    capabilities:
    - shell
    - the product's public surface
    - isolated environment
    skip_when: not selected at planning (the reason is recorded)
    allowed_operations:
    - exercise the candidate
    - create isolated fixtures
    - record ticket checks
    time_limit_minutes: unset
    cost_limit: unset
    exclusions:
    - must not have authored the work it judges
    - fresh context
    advisory: true
  dogfood:
    runs_in: own-session
    binding: dogfood
    card: cards/dogfood.md
    activation: only when the operator authorizes a session
    purpose: use the shipped product for real
    outputs:
    - finding tickets
    returns_to: product_intake
    may_not:
    - act as a build gate
    - start itself
    - install on the operator's live system
    capabilities:
    - the installed product
    - approved test accounts
    skip_when: no operator authorization
    allowed_operations:
    - use the product
    - file finding tickets
    time_limit_minutes: 20
    cost_limit: unset
    exclusions: []
    advisory: true
  designer:
    runs_in: own-session
    binding: designer
    card: cards/designer.md
    activation: UI or interaction ambiguity before the plan freezes
    purpose: settle flows, states and acceptance examples
    outputs:
    - flows and acceptance examples
    returns_to: planner
    may_not:
    - count as the independent evaluator of a candidate it shaped
    capabilities:
    - repo read
    skip_when: no UI or interaction ambiguity
    allowed_operations:
    - write flows, states and acceptance examples
    time_limit_minutes: unset
    cost_limit: unset
    exclusions:
    - cannot count as the independent evaluator of what it shaped
    advisory: true
  librarian:
    runs_in: own-session
    binding: librarian
    card: ../hermes/herd-librarian/SKILL.md
    activation: merge_stack.py --apply
    purpose: file the run's friction and propose rule changes
    outputs:
    - ledger rows
    - proposals
    may_not:
    - commit
    - change the skill
    capabilities:
    - a local or hosted model
    - the run log
    - the vault ledgers
    skip_when: the run is not merged
    allowed_operations:
    - append ledger rows
    - write proposals
    time_limit_minutes: unset
    cost_limit: unset
    exclusions: []
    advisory: true
```

- [ ] **I3** `skill/cards/lead.md` — the lead role card

Create this file with exactly this body (byte-exact, ends with one newline):

```python
# Role card — the lead

One session holds these five roles; the loop itself is `skill/SKILL.md`.

## Orchestrator

- **Purpose.** Route work, rule on disputes, and give the operator one consolidated report.
- **Inputs.** The operator's instructions, the run log, tickets, review files.
- **Outputs.** Rulings (in design.md and the run log), each dispatch's assignment (`team.py assign`, before the packet), the closing report.
- **Activation.** Always.
- **Scope.** Intake, role selection per ticket (including whether QA is selected, with the reason when not), QA dispositions, dogfood triage.
- **Evidence.** Reports which promised outcomes were exercised and which remain unchecked.
- **Authority.** Rules within the spec's non-goals; keeps pre-execution and the operator gates.
- **Exclusions.** Never hands off an operator gate.

## Architect

- **Purpose.** Decide interfaces, invariants and non-goals across tickets.
- **Inputs.** Issues, dogfood findings, the code.
- **Outputs.** Decisions in design.md.
- **Activation.** At intake and on cross-ticket findings.
- **Scope.** Cross-ticket design, including what dogfood findings mean for it.
- **Evidence.** Each decision cites what it was based on.
- **Authority.** Decides design within the agreed product scope.
- **Exclusions.** Never changes scope or product behavior without the operator.

## Planner

- **Purpose.** Write the openspec change and pre-execute it.
- **Inputs.** The issue, the design decisions, the code the spec touches.
- **Outputs.** The openspec change, pre-execution evidence, byte-exact fences.
- **Activation.** Every ticket.
- **Scope.** Tests first; fences generated from the pre-executed tree and checked with fencecheck; gates measured with a named baseline.
- **Evidence.** Grounded facts cite what was read; RED, GREEN, mutation kills.
- **Authority.** Plan-review APPROVE authorizes the build.
- **Exclusions.** Never skips pre-execution on the full tier.

## Product intake

- **Purpose.** Turn operator requests and dogfood findings into ranked tickets.
- **Inputs.** Operator input, dogfood finding tickets.
- **Outputs.** Ranked tickets.
- **Activation.** New input or findings.
- **Scope.** New goals and new scope go to the operator in the sweep's one message.
- **Evidence.** Each ticket carries its evidence.
- **Authority.** Ranks and files work within agreed scope.
- **Exclusions.** Never self-approves new scope.

## Release prep

- **Purpose.** Commit, push normally, and open the PR on branches this loop created.
- **Inputs.** A candidate whose final review is clean.
- **Outputs.** Commit, pushed branch, PR.
- **Activation.** After the final review.
- **Scope.** Branches this loop created and owns.
- **Evidence.** The PR names its review record and gates.
- **Authority.** Normal push and PR creation (herd's carve-out).
- **Exclusions.** Never merges or publishes (the operator does). A push to main or to a branch the loop did not create, and a force-push, stop and ask: only explicit operator authorization allows them.
```

- [ ] **I4** `skill/cards/builder.md` — the builder role card

Create this file with exactly this body (byte-exact, ends with one newline):

```python
# Role card — builder

## Purpose

Implement one openspec change in one worktree, from the lead's byte-exact fences.

## Inputs

The approved spec (proposal, design, spec delta, tasks.md), `BUILD-BRIEFING-<id>.md`, and the worktree it names.

## Outputs

The implementation and `HANDOFF-<id>.md`: self-review (10 lines or fewer), RED and GREEN tails, the full-suite tail verbatim, lint and type results, fencecheck, diff stat, mutation log with each observed kill, unbacked claims, round log.

## Activation

The lead's dispatch prompt pointing at the briefing.

## Scope

Only the worktree and the briefing's allowed files. Tests first (apply the T steps, observe RED), then the I steps, then every gate, then the mutation drives. The full suite runs once, after all edits.

## Evidence

Literal command lines and their last lines, in the handoff. A number is never estimated.

## Authority

Sends review rounds to the build reviewer; fixes every CONFIRMED finding and re-runs all gates; cap 2 rounds, +1 on a lead ruling. At the cap: `BLOCKED:` to the lead with the open findings. On `REVIEW CLEAN`: `DONE: build for <id> — reviewer clean after N rounds — handoff at <path>`.

## Exclusions

Never commits, pushes, or leaves the worktree; never edits a test after the tests-first step or loosens an assertion; contacts the lead only with BLOCKED or DONE.
```

- [ ] **I5** `skill/cards/plan-reviewer.md` — the plan-reviewer role card

Create this file with exactly this body (byte-exact, ends with one newline):

```python
# Role card — plan reviewer

## Purpose

Challenge the spec before anything is built.

## Inputs

The four spec files, the lead's pre-execution evidence (RED and GREEN tails, mutation kills, gate lines), and git blobs.

## Outputs

`PLAN-REVIEW-<id>-round-N.md`: numbered findings with location, evidence and an exact fix, marked CONFIRMED or PLAUSIBLE, remedies marked UNTESTED; one verdict line, APPROVE or REVISE.

## Activation

Every spec; on the small tier one round, on the full tier until APPROVE.

## Scope

Spends effort on what execution cannot catch: re-derive fixture arithmetic, challenge design conventions and boundary cases, check that every text anchor resolves once, and that every gate is a measured literal with its baseline.

## Evidence

Reads files and git blobs, does its own arithmetic, projects fences onto the base in memory.

## Authority

Its APPROVE authorizes the build (the operator does not hold a gate there). Later rounds open with the previous findings in its own numbering, each FOLDED, NARROWED or REJECTED, and sweep for what the revision broke.

## Exclusions

Never applies the plan, imports its code, or runs its tests or mutations. A fresh session for each new spec. Hard rule (team design §4): must not be an author of what it judges — including the lead's pre-execution and design contributions — and starts from a fresh context, whatever pane or model it runs in. A different model from the author is recommended and recorded (same / different / unknown), never required unless project policy says so.
```

- [ ] **I6** `skill/cards/build-reviewer.md` — the build-reviewer role card

Create this file with exactly this body (byte-exact, ends with one newline):

```python
# Role card — build reviewer

## Purpose

Review the build against the spec and report only confirmed defects.

## Inputs

The spec, the handoff, and the candidate diff against the base its prompt names.

## Outputs

`REVIEW-<id>-round-N.md`, opening with a `Candidate: <commit or tree>` line
(`team.py gate review-file` checks it) and ending `FINDINGS: <n>` or `REVIEW CLEAN`.

## Activation

Each review round the builder sends.

## Scope

Runs `tools/fencecheck.py` (never checks fences by eye), the touched test files (not the full suite; the handoff carries its tail), and two mutation re-drives of its choice with `mutate.py --scratch`.

## Evidence

Every finding has file:line and an exact fix. A clean round still lists what it ran and each command's last line; a file that is only the sentinel is not evidence.

## Authority

Talks only to the builder; contacts the lead only to sign off: `REVIEW CLEAN for <id> after N rounds`.

## Exclusions

Never edits the candidate. It is not the author, and it starts from a fresh context (team design §4). Hard rule (team design §4): must not be an author of what it judges — including the lead's pre-execution and design contributions — and starts from a fresh context, whatever pane or model it runs in. A different model from the author is recommended and recorded (same / different / unknown), never required unless project policy says so.
```

- [ ] **I7** `skill/cards/qa.md` — the qa role card

Create this file with exactly this body (byte-exact, ends with one newline):

```python
# Role card — test QA

## Purpose

Exercise the promised outcome on a frozen candidate, independently of its authors.

## Inputs

A frozen candidate (commit or tree id), an isolated environment, the spec's promised outcomes.

## Outputs

Candidate id, environment, expected vs observed, reproduction, unchecked coverage, verdict; recorded as ticket checks (`tickets.py check ... --candidate`).

## Activation

Chosen at planning by journey and risk; a skip is recorded with its reason.

## Scope

Runs after the build review is clean and before the lead's final review. May create isolated fixtures; never touches production data or accounts.

## Evidence

What it ran and what it saw. NOT CHECKED or BLOCKED is never PASS.

## Authority

In-scope defects go back to the builder under the existing round cap and ruling policy; broader ones become new tickets. A changed candidate renews the affected review and QA evidence.

## Exclusions

Never repairs the candidate it certifies; never an author of it; no merge authority. Hard rule (team design §4): must not be an author of what it judges — including the lead's pre-execution and design contributions — and starts from a fresh context, whatever pane or model it runs in. A different model from the author is recommended and recorded (same / different / unknown), never required unless project policy says so.
```

- [ ] **I8** `skill/cards/dogfood.md` — the dogfood role card

Create this file with exactly this body (byte-exact, ends with one newline):

```python
# Role card — dogfood

## Purpose

Use the shipped product for real and report what building and review cannot see.

## Inputs

An identified released or installed build, approved test accounts and data, a real task.

## Outputs

Finding tickets with evidence, for the lead's product intake.

## Activation

Only when the operator authorizes a session: time-boxed (20 minutes), on a product with a usable surface and a safe environment.

## Scope

Web apps, CLI installs or upgrades, a library through its public API, an installed skill on an authorized task.

## Evidence

The attempted journey and reproducible findings, including friction that is not a code defect.

## Authority

New scope goes through the operator's sweep; in-scope fixes use the existing loop.

## Exclusions

Not a build gate; never starts itself; never installs or updates the operator's live system on its own.
```

- [ ] **I9** `skill/cards/designer.md` — the designer role card

Create this file with exactly this body (byte-exact, ends with one newline):

```python
# Role card — product designer

## Purpose

Settle flows, states and acceptance examples before the plan freezes.

## Inputs

The approved product intent and the named interaction ambiguity.

## Outputs

Flows, interaction states and acceptance examples, consumed by the planner and QA.

## Activation

On demand, when a ticket has UI or interaction ambiguity.

## Scope

Only the design scope the lead authorized.

## Evidence

Examples concrete enough to test.

## Authority

New user-visible behavior still goes to the operator.

## Exclusions

Never counts as the independent evaluator of a candidate it shaped.
```

- [ ] **I10** `tools/team.py` — catalog check, step packet, loop gates

Create this file with exactly this body (byte-exact, ends with one newline):

```python
"""The team: the portable role catalog, the current-step packet, and the loop's gate checks (#40).

usage: team.py check                                   validate skill/herd.yaml and its cards
       team.py assign ROLE --issue N --session S [--candidate C] [--scope TEXT] [--checks A,B]
                      [--bindings PATH] [--repo PATH]     record the resolved assignment at dispatch
       team.py packet ROLE --issue N [--candidate C] [--bindings PATH] [--repo PATH]
                                                       what a session needs at dispatch or after compaction
       team.py gate dispatch --issue N [--repo PATH]   the spec is approved and the last plan review approves
       team.py gate review   --issue N [--repo PATH]   the review-round cap (2, +1 per ruling) is not exceeded
       team.py gate review-file PATH                   a review file names the candidate it reviewed

Roles are not seats (docs/team-design.md): `skill/herd.yaml` names each role's
purpose, where it runs, its card, what it evaluates and what it may not do; the
machine-local bindings (#38) say which harness and model play it. The gates
check structure only; reviewers and the operator judge outcomes.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

import bindings
import runlog

SKILL = pathlib.Path(__file__).resolve().parent.parent / "skill"
CATALOG = SKILL / "herd.yaml"
CARD_ROOTS = (SKILL / "cards", SKILL.parent / "hermes")
KEYS = ("runs_in", "binding", "card", "activation", "purpose", "outputs", "may_not", "capabilities", "skip_when",
        "allowed_operations", "time_limit_minutes", "cost_limit", "exclusions", "advisory")
LEAD_HELD = ("orchestrator", "architect", "planner", "product_intake", "release_prep")
OWN_SESSION = ("builder", "plan_reviewer", "build_reviewer", "qa", "dogfood", "designer", "librarian")
REVIEW_CAP = 2


def load(path: pathlib.Path = CATALOG) -> dict:
    import yaml
    return yaml.safe_load(path.read_text())


def validate(doc: dict) -> list[str]:
    errors = [] if doc.get("version") == 1 else ["unsupported or missing version"]
    roles = doc.get("roles") or {}
    errors += [f"missing role {name}" for name in LEAD_HELD + OWN_SESSION if name not in roles]
    for name, r in roles.items():
        errors += [f"{name}: missing {k}" for k in KEYS if r.get(k) is None]
        if r.get("runs_in") not in ("own-session", "lead-held"):
            errors.append(f"{name}: runs_in must be own-session or lead-held")
        if name in LEAD_HELD and r.get("runs_in") != "lead-held":
            errors.append(f"{name}: a lead-held role (docs/team-design.md §2)")
        if name in OWN_SESSION and r.get("runs_in") != "own-session":
            errors.append(f"{name}: an own-session role (docs/team-design.md §2)")
        if r.get("binding") and r["binding"] not in bindings.ROLES:
            errors.append(f"{name}: unknown binding '{r['binding']}'")
        if r.get("card"):
            card = (SKILL / r["card"]).resolve()
            if card.suffix != ".md" or not any(card.is_relative_to(root.resolve()) for root in CARD_ROOTS):
                errors.append(f"{name}: card {r['card']} is not a role card (a .md under skill/cards/ or hermes/)")
            elif not card.exists():
                errors.append(f"{name}: card {r['card']} not found")
        for e in r.get("evaluates") or []:
            if e == name:
                errors.append(f"{name}: a role cannot evaluate itself")
            elif e not in roles:
                errors.append(f"{name}: evaluates unknown role '{e}'")
    return errors


def issue_events(repo: pathlib.Path, issue: str) -> list[dict]:
    return [e for e in runlog.read(repo) if e.get("issue") == issue]


def gate_dispatch(events: list[dict], issue: str) -> str | None:
    if not any(e["kind"] == "spec-approved" for e in events):
        return f"no spec-approved for #{issue}"
    reviews = [e for e in events if e["kind"] == "plan-review"]
    if not reviews:
        return f"no plan review for #{issue}"
    if reviews[-1].get("verdict") != "APPROVE":
        return f"the last plan review of #{issue} is {reviews[-1].get('verdict')}, not APPROVE"
    return None


def gate_review(events: list[dict], issue: str) -> str | None:
    rounds = sum(e["kind"] == "review-round" for e in events)
    rulings = sum(e["kind"] == "ruling" for e in events)
    if rounds >= REVIEW_CAP + rulings:
        return f"BLOCKED: #{issue} reached the review cap ({REVIEW_CAP} rounds{f' + {rulings} by ruling' if rulings else ''})"
    return None


def gate_review_file(path: pathlib.Path) -> str | None:
    if not re.search(r"(?im)^[ \t]*candidate[ \t]*:[ \t]*\S[^\r\n]*$", path.read_text()):
        return f"{path.name} names no candidate (add a 'Candidate: <commit or tree>' line)"
    return None


def resolved_binding(role_binding: str, bindings_file: pathlib.Path):
    if not bindings_file.exists():
        return "unknown (no bindings file)"
    return bindings.resolve(role_binding, user=bindings.load(bindings_file).get("roles")) or "unknown (unbound)"


def assign(role: str, *, issue: str, repo: pathlib.Path, session: str, candidate: str | None, scope: str | None,
           checks: list[str], bindings_file: pathlib.Path) -> str | None:
    """Record the resolved assignment in the run log (team design §2: role + binding + session + candidate
    + scope + selected checks); return why it was refused, or None."""
    roles = load()["roles"]
    if role not in roles:
        return f"unknown role {role!r}"
    b = resolved_binding(roles[role]["binding"], bindings_file)
    record = {"role": role, "binding": b, "session": session,
              "candidate": candidate, "scope": scope, "checks": checks}
    return runlog.append(repo, "note", {"issue": issue, "text": "assignment " + json.dumps(record, sort_keys=True)})


def latest_assignment(events: list[dict], role: str) -> dict | None:
    for e in reversed(events):
        if e["kind"] == "note" and e.get("text", "").startswith("assignment "):
            record = json.loads(e["text"][len("assignment "):])
            if record.get("role") == role:
                return record
    return None


def packet(role: str, *, issue: str, repo: pathlib.Path, candidate: str | None, bindings_file: pathlib.Path) -> dict:
    """When an assignment was recorded at dispatch, the binding and candidate come from it and the bindings
    file is not read; an explicit candidate names a newer one (a fix changed it)."""
    r = load()["roles"][role]
    events = issue_events(repo, issue)
    progress = [e for e in events if e["kind"] in runlog.PROGRESS]
    assignment = latest_assignment(events, role)
    if assignment:
        binding = assignment.get("binding") or "unknown (none recorded at dispatch)"
        candidate = candidate or assignment.get("candidate")
    else:
        binding = resolved_binding(r["binding"], bindings_file)
    authored = r.get("evaluates") or []
    return {"role": role, "card": str(SKILL / r["card"]), "issue": issue,
            "step": progress[-1]["kind"] if progress else "unknown", "candidate": candidate or "unknown",
            "returns_to": r.get("returns_to", "the lead"),
            "independence": f"fresh context whatever pane or model; must not have authored: {', '.join(authored)}"
            if authored
            else "none required",
            "binding": binding, "may_not": r["may_not"],
            "assignment": assignment or "unknown (no assignment recorded)"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    asg = sub.add_parser("assign")
    asg.add_argument("role")
    asg.add_argument("--issue", required=True)
    asg.add_argument("--session", required=True)
    asg.add_argument("--candidate")
    asg.add_argument("--scope")
    asg.add_argument("--checks", default="")
    asg.add_argument("--bindings")
    asg.add_argument("--repo", default=".")
    pk = sub.add_parser("packet")
    pk.add_argument("role")
    pk.add_argument("--issue", required=True)
    pk.add_argument("--candidate")
    pk.add_argument("--bindings")
    pk.add_argument("--repo", default=".")
    g = sub.add_parser("gate")
    g.add_argument("which", choices=("dispatch", "review", "review-file"))
    g.add_argument("path", nargs="?")
    g.add_argument("--issue")
    g.add_argument("--repo", default=".")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        errors = validate(load())
        print("\n".join(errors) or "valid: skill/herd.yaml")
        return 2 if errors else 0
    if a.cmd == "assign":
        why = assign(a.role, issue=a.issue, repo=pathlib.Path(a.repo), session=a.session, candidate=a.candidate,
                     scope=a.scope, checks=[c for c in a.checks.split(",") if c],
                     bindings_file=pathlib.Path(a.bindings) if a.bindings else bindings.user_path())
        print(why or "recorded")
        return 2 if why else 0
    if a.cmd == "packet":
        p = packet(a.role, issue=a.issue, repo=pathlib.Path(a.repo), candidate=a.candidate,
                   bindings_file=pathlib.Path(a.bindings) if a.bindings else bindings.user_path())
        for k, v in p.items():
            print(f"{k}: {v}")
        return 0
    if a.which == "review-file":
        why = gate_review_file(pathlib.Path(a.path))
    else:
        events = issue_events(pathlib.Path(a.repo), a.issue)
        why = gate_dispatch(events, a.issue) if a.which == "dispatch" else gate_review(events, a.issue)
    print(why or "ok")
    return 2 if why else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **I11** `skill/SKILL.md` — the Roster section defers to the catalog and bindings

Find this exact text (it occurs exactly once):

```python
## Roster

```

Replace it with exactly:

```python
## Roster

Who plays each role is decided by two files, not by this table: the portable
role catalog `skill/herd.yaml` (roles, cards, what each evaluates, what it may
not do; no vendor names) and the machine's bindings file (#38; `herdsetup.py`,
#39). The table below is this machine's example profile
(`skill/profiles/example-claude-codex-pi.yaml`); `probe.py` still reads it
until #51 moves it to the bindings (#40).

```

- [ ] **I12** `skill/SKILL.md` — Roles and hand-offs points at the cards, packet and gates

Find this exact text (it occurs exactly once):

```python
## Roles and hand-offs

```

Replace it with exactly:

```python
## Roles and hand-offs

Each role's contract is its card in `skill/cards/` (the lead's five roles share
`cards/lead.md`). At dispatch, `python3 <herd>/tools/team.py assign <role>
--issue <id> --session <name> --candidate <commit> --scope <files> --checks
<gates>` records the assignment and must print `recorded`. Then, and after a
compaction, `team.py packet <role> --issue <id>` gives a session its card,
current step, return route, independence rule, and the binding and candidate
recorded at dispatch (an explicit `--candidate <commit>` names a newer one).
Before dispatch, `team.py gate dispatch --issue <id>` must print `ok`; before
each review round, `team.py gate review --issue <id>`; and a review file must
name its candidate (`team.py gate review-file <path>`). The gates check
structure only (#40).

```

- [ ] **I13** `skill/SKILL.md` — a reused pane gives an evaluator a fresh context (team design §4)

Find this exact text (it occurs exactly once):

```python
Same kind, next role: rename and
re-prompt. Different kind:
```

Replace it with exactly:

```python
Same kind, next role: rename and
re-prompt; an evaluator (plan reviewer, build reviewer, QA) first gets a
fresh context (`/new`, or a restart), as its card requires. Different kind:
```

- [ ] **I14** `skill/SKILL.md` — the Roster's own sentence defers to the bindings file (build review F5)

Find this exact text (it occurs exactly once):

```python
Change
a model here and nowhere else.
```

Replace it with exactly:

```python
Change
a model in the machine's bindings file; keep this table synchronized for
`probe.py` until #51 moves it to the bindings.
```

## 3. Gates

- Full suite at the base (`feat/41-context` after its build): `461 passed`. After: `495 passed` (33 in `tests/test_team.py` with parametrized cases, 1 new skill-text test). ~9 s.
- `ruff check tools tests` → `All checks passed!`; `openspec validate team` valid; `python3 tools/team.py check` → valid.

## 4. Mutations

Drive with `python3 tools/mutate.py openspec/changes/team/tasks.md <tree>`; every one KILLED.

- [ ] **M1** in `tools/team.py`: replace

```python
            if e == name:
```

with

```python
            if False:
```

Killer: `tests/test_team.py::test_an_invalid_catalog_is_rejected_with_a_reason`

- [ ] **M2** in `tools/team.py`: replace

```python
        if name in LEAD_HELD and r.get("runs_in") != "lead-held":
```

with

```python
        if False:
```

Killer: `tests/test_team.py::test_an_invalid_catalog_is_rejected_with_a_reason`

- [ ] **M3** in `tools/team.py`: replace

```python
    if reviews[-1].get("verdict") != "APPROVE":
```

with

```python
    if False:
```

Killer: `tests/test_team.py::test_dispatch_needs_an_approved_spec_and_an_approving_last_plan_review`

- [ ] **M4** in `tools/team.py`: replace

```python
    if rounds >= REVIEW_CAP + rulings:
```

with

```python
    if rounds >= REVIEW_CAP:
```

Killer: `tests/test_team.py::test_the_review_round_cap_escalates_and_a_ruling_grants_one_more`

- [ ] **M5** in `tools/team.py`: replace

```python
    if not re.search(r"(?im)^[ \t]*candidate[ \t]*:[ \t]*\S[^\r\n]*$", path.read_text()):
```

with

```python
    if False:
```

Killer: `tests/test_team.py::test_a_review_file_must_name_its_candidate`

- [ ] **M6** in `tools/team.py`: replace

```python
            else "none required",
```

with

```python
            else "fresh non-author context",
```

Killer: `tests/test_team.py::test_a_lead_held_role_resolves_the_lead_binding_and_unknowns_stay_unknown`

- [ ] **M7** in `tools/team.py`: replace

```python
    if not any(e["kind"] == "spec-approved" for e in events):
```

with

```python
    if False:
```

Killer: `tests/test_team.py::test_dispatch_needs_an_approved_spec_and_an_approving_last_plan_review`

- [ ] **M8** in `tools/team.py`: replace

```python
            if record.get("role") == role:
```

with

```python
            if True:
```

Killer: `tests/test_team.py::test_an_assignment_is_recorded_at_dispatch_and_recovered_by_the_packet`

- [ ] **M9** in `tools/team.py`: replace

```python
    if role not in roles:
```

with

```python
    if False:
```

Killer: `tests/test_team.py::test_an_unknown_role_cannot_be_assigned`

- [ ] **M10** in `tools/team.py`: replace

```python
KEYS = ("runs_in", "binding", "card", "activation", "purpose", "outputs", "may_not", "capabilities", "skip_when",
```

with

```python
KEYS = ("runs_in", "binding", "card", "activation", "purpose", "outputs", "may_not", "capabilities",
```

Killer: `tests/test_team.py::test_the_catalog_requires_the_policy_fields_of_team_design_section_2`

- [ ] **M11** in `tools/team.py`: replace

```python
              "candidate": candidate, "scope": scope, "checks": checks}
```

with

```python
              "candidate": candidate, "scope": scope, "checks": []}
```

Killer: `tests/test_team.py::test_an_assignment_is_recorded_at_dispatch_and_recovered_by_the_packet`

- [ ] **M13** in `tools/team.py`: replace

```python
    errors += [f"missing role {name}" for name in LEAD_HELD + OWN_SESSION if name not in roles]
```

with

```python

```

Killer: `tests/test_team.py::test_an_invalid_catalog_is_rejected_with_a_reason`

- [ ] **M14** in `tools/team.py`: replace

```python
        if name in OWN_SESSION and r.get("runs_in") != "own-session":
```

with

```python
        if False:
```

Killer: `tests/test_team.py::test_an_invalid_catalog_is_rejected_with_a_reason`

- [ ] **M15** in `tools/team.py`: replace

```python
    if assignment:
```

with

```python
    if False:
```

Killer: `tests/test_team.py::test_recovery_reads_the_recorded_assignment_not_the_current_bindings_file`

- [ ] **M16** in `tools/team.py`: replace

```python
        candidate = candidate or assignment.get("candidate")
```

with

```python
        pass
```

Killer: `tests/test_team.py::test_recovery_reads_the_recorded_assignment_not_the_current_bindings_file`

- [ ] **M17** in `tools/team.py`: replace

```python
        errors += [f"{name}: missing {k}" for k in KEYS if r.get(k) is None]
```

with

```python
        errors += [f"{name}: missing {k}" for k in KEYS if k not in r]
```

Killer: `tests/test_team.py::test_an_invalid_catalog_is_rejected_with_a_reason`

- [ ] **M18** in `tools/team.py`: replace

```python
            if card.suffix != ".md" or not any(card.is_relative_to(root.resolve()) for root in CARD_ROOTS):
```

with

```python
            if card.suffix != ".md":
```

Killer: `tests/test_team.py::test_an_invalid_catalog_is_rejected_with_a_reason`

- [ ] **M19** in `tools/team.py`: replace

```python
    record = {"role": role, "binding": b, "session": session,
```

with

```python
    record = {"role": role, "binding": b if isinstance(b, dict) else None, "session": session,
```

Killer: `tests/test_team.py::test_an_assignment_without_a_bindings_file_keeps_the_reason`

- [ ] **M12** in `tools/team.py`: replace

```python
    if not re.search(r"(?im)^[ \t]*candidate[ \t]*:[ \t]*\S[^\r\n]*$", path.read_text()):
```

with

```python
    if not re.search(r"(?im)^\s*candidate\s*:\s*\S+", path.read_text()):
```

Killer: `tests/test_team.py::test_a_blank_candidate_header_is_refused`
