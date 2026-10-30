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


def test_the_baseline_suite_runs_in_its_own_clean_worktree():
    # Proposal baseline-suite-contaminated-by-edits (#459-4, #334): a baseline
    # run in the pre-execution tree read mid-build edits and was discarded.
    gates = paragraph(SKILL.read_text(), "- **Measure every gate before writing its expectation")
    assert "in its own clean worktree cut from the base commit (`base-<id>`)" in gates
    assert "never in the pre-execution tree or any worktree you will edit" in gates


CARDS = SKILL.parent / "cards"


def test_an_agent_starts_in_a_worktree_only_after_the_pane_cds_there():
    # Path A #113: `herdr agent start` has no --cwd, and the first attempt started nothing.
    start = paragraph(SKILL.read_text(), "**A Claude or pi agent starts where its pane already is.**")
    assert "`herdr agent start` has no `--cwd`" in start
    assert '`herdr pane run <pane> "cd <worktree>"`' in start
    assert "`herdr agent list`" in start


def test_each_shell_pane_runs_one_agents_commands_one_at_a_time():
    # Path A #113: a long local Spark run in a shared shell pane held a helper's commands for over an hour.
    panes = paragraph(SKILL.read_text(), "**One shell pane per long command.**")
    assert "the lead never types into a helper's pane" in panes
    assert "`herdr pane read <pane>`" in panes
    assert "never queue a command behind another" in panes
    assert "`logs/<helper>/`" in panes
    assert "until grep -q EXIT= <log>; do sleep 5; done" in panes


def test_an_offloaded_gate_runs_on_a_box_with_its_own_log():
    # Path A #113: local Apache Spark could not start in a Claude pane; every briefing needed a hand-written note.
    text = SKILL.read_text()
    gate = paragraph(text, "**Offloaded gates (Path A #113).**")
    assert "`offloaded: <box>, log <path>`" in gate
    assert "killer test id" in gate
    assert "Fold every finding before re-running" in gate
    roster = " ".join(text[text.index("## Roster"): text.index("## Before an unattended run")].split())
    assert "home LAN" in roster and "never by switching tailnets" in roster


def test_the_lead_makes_a_stack_merge_and_a_fresh_reviewer_reviews_it():
    # Path A #117, #118: the builder cannot author a merge commit.
    merge = paragraph(SKILL.read_text(), "- **A merge commit in a stack (Path A #117, #118).**")
    assert "The lead makes the merge" in merge
    assert "a fresh build reviewer reviews" in merge
    assert "whether it may `git add`" in merge
    assert "upstream rename" in merge
    assert "never in the candidate worktree" in merge
    assert "`fencecheck: not applicable`" in merge
    assert "nonzero pass count" in merge


def test_the_skill_runs_mkbrief_with_the_herd_interpreter():
    text = " ".join(SKILL.read_text().split())
    assert "--herd-python <herd venv python>" in text and "--cache-dir <writable dir>" in text


def test_a_helper_brief_names_each_killer_by_test_id():
    helpers = paragraph(SKILL.read_text(), "- **Helper briefs (Path A #113, #117).**")
    assert "test node id" in helpers and "never a file" in helpers
    assert "known red" in helpers
    assert "edits the fold file itself" in helpers


def test_the_build_reviewer_card_covers_a_review_with_no_fences():
    card = (CARDS / "build-reviewer.md").read_text()
    assert "`<herd>/tools/fencecheck.py`" in card
    assert "`fencecheck: not applicable`" in card
    assert "already at the base" in card


def test_the_plan_reviewer_card_asks_for_adversarial_values():
    card = (CARDS / "plan-reviewer.md").read_text()
    for value in ("None", "NaN", "infinity", "`Decimal(\"NaN\")`", "a string", "a bool"):
        assert value in card, value
