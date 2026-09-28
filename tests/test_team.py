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


def test_plan_review_preserves_authorization_conditions():
    card = (SKILL_DIR / "cards" / "plan-reviewer.md").read_text()
    assert "compare its actor, action, scope, and authorization condition against the source skill" in card
    assert "tightened prohibitions" in card and "relaxed permissions" in card
    assert "focused assertion" in card and "surviving authorization condition" in card
    assert "cite an existing assertion" in card
    skill = (SKILL_DIR / "SKILL.md").read_text()
    assert "authority-rule check in `skill/cards/plan-reviewer.md`" in skill
