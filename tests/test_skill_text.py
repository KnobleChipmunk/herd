import pathlib
import re

SKILL = pathlib.Path(__file__).resolve().parent.parent / "skill" / "SKILL.md"


def paragraph(text: str, opening: str) -> str:
    start = text.index(opening)
    end = re.search(r"\n(?:- \*\*|\*\*|## |\n)", text[start + len(opening):])
    return " ".join(text[start: start + len(opening) + (end.start() if end else len(text))].split())


def test_the_plan_reviewer_is_never_told_to_run_tests():
    """Its tier-table row says it never executes; no other rule may send it to run tests (#459)."""
    text = SKILL.read_text()
    full_suite = paragraph(text, "- **The full suite runs once per build")
    runners = next(s for s in full_suite.split(". ") if "touched test files" in s)
    assert "plan reviewer" not in runners.lower()
    assert "The plan reviewer runs nothing" in full_suite


def test_the_plan_reviewer_brief_draws_the_read_only_line():
    brief = paragraph(SKILL.read_text(), "**Plan-reviewer brief")
    assert "never applies the plan" in brief
    assert "runs its tests or mutations" in brief
    assert "git blobs" in brief


def test_the_sweep_commits_what_the_librarian_and_sync_left_in_proposals():
    """sync and the librarian write files but never commit (#29): the sweep's PR carries them."""
    text = " ".join(SKILL.read_text().split())
    sweep = text[text.index("5. **Proposals.**"): text.index("6. **Ask once.**")]
    assert "chore/proposals-sweep-<date>" in sweep
    assert "git status" in sweep and "proposals/" in sweep


def test_the_skill_states_it_governs_herd_runs_over_devloop():
    """Operator ruling on #32: scope the two loops; the skill wins inside a /herd run."""
    text = SKILL.read_text()
    intro = paragraph(text, "One session — **the lead, this one**")
    scope = " ".join(text[text.index("# Herd"): text.index("One session — **the lead, this one**")].split())
    assert "DEVLOOP.md" in scope
    assert "wins" in scope and "/herd" in scope
    assert "DEVLOOP" not in intro


def test_the_lead_starts_the_attention_watcher_and_names_the_monitor():
    text = " ".join(SKILL.read_text().split())
    monitoring = text[text.index("## Monitoring"): text.index("## Rulings")]
    assert "attention.py watch --repo <repo>" in monitoring
    assert "attention.py monitor --repo <repo>" in monitoring
    assert "run-start" in monitoring


def test_the_skill_separates_messages_from_owned_work():
    text = " ".join(SKILL.read_text().split())
    tickets = text[text.index("## Tickets"): text.index("## Run log")]
    assert "A question goes as a message" in tickets and "goes as a ticket" in tickets
    assert "tickets.py create" in tickets and "handoff" in tickets and "never a PASS" in tickets


def test_the_sweep_names_the_bindings_file_and_the_readiness_check():
    text = " ".join(SKILL.read_text().split())
    sweep = text[text.index("3. **Preflight.**"): text.index("4. **Decisions.**")]
    assert "~/.config/herd/bindings.yaml" in sweep and "bindings.py ready --role" in sweep


def test_the_sweep_names_herd_setup():
    text = " ".join(SKILL.read_text().split())
    sweep = text[text.index("3. **Preflight.**"): text.index("4. **Decisions.**")]
    assert "herdsetup.py assisted" in sweep and "herdsetup.py validate" in sweep and "from-example" in sweep


def test_the_monitor_names_the_context_collector():
    text = " ".join(SKILL.read_text().split())
    monitoring = text[text.index("## Monitoring"): text.index("## Rulings")]
    assert "context_collector.py install" in monitoring and "uninstall" in monitoring


def test_the_skill_points_at_the_catalog_the_cards_and_the_gates():
    text = " ".join(SKILL.read_text().split())
    roster = text[text.index("## Roster"): text.index("## Before an unattended run")]
    roles = text[text.index("## Roles and hand-offs"): text.index("## The loop, end to end")]
    assert "skill/herd.yaml" in roster and "#51" in roster
    assert "skill/cards/" in roles and "team.py packet" in roles and "team.py gate dispatch" in roles
    assert "an evaluator (plan reviewer, build reviewer, QA) first gets a fresh context" in text
    assert "team.py assign" in roles and roles.index("team.py assign") < roles.index("team.py packet")



def test_the_skill_keeps_machine_specifics_in_the_roster_and_bindings():
    """A second operator runs this skill: the local builder model lives in the
    Roster's example row and the bindings file, and push/merge workarounds
    apply only when the session token lacks the scope."""
    text = SKILL.read_text()
    roster = text[text.index("## Roster"): text.index("## Before an unattended run")]
    rest = text.replace(roster, "")
    for personal in ("swift15", "/home/", "Exocortex", "Obsidian", "on this machine"):
        assert personal not in rest, personal
    assert "example" in paragraph(text, "Who plays each role")


def test_a_fold_that_changes_a_test_fence_re_observes_red_in_scratch():
    """Proposal fold-red-evidence-stale: section 0's RED expectation is re-measured by the lead."""
    fold = paragraph(SKILL.read_text(), "For an accepted fence change")
    assert "When the fold changes a test fence" in fold
    assert "runs that test file against the pinned base in scratch" in fold
    assert "records its new RED tail and `gates.py match` line in section 0" in fold


def test_a_fold_returns_to_review_with_its_outcome_checklist():
    """Proposal fold-coherence-gap (#460, #333): a fold names what it changed before review."""
    rereview = paragraph(SKILL.read_text(), "**Re-review prompts are disposition-numbered")
    for row in ("(1) the normal boundary", "(2) the late boundary",
                "(3) the absent-state behaviour", "(4) every mutation and killer pair it moved"):
        assert row in rereview
    assert "follows every branch of the helper" in rereview
    assert "bounded to the encoding actually observed" in rereview
