import json
import pathlib
import subprocess

import pytest

import librarian

LEDGER_HEAD = """# Herd build ledger

Intro prose.

| date | repo | ticket | pr | variant | tier | plan rounds | rounds | findings | rulings | blocked | gate miss | lead | outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-20 | work | TICKET-2 | 63 | A | small | 0 | 1/2 | 0 | 0 | 0 | 2 | 0 | merged |
"""

FRICTION = """# Friction ledger

Intro.

## gam-daemon-stall (GAM MCP call hangs, then connection closes)
- 2026-08-12 project-mera devloop audit (windows): memory_context hung 120s.

## false-out-of-scope (builder defers an in-scope fix)
- 2026-08-19 work TICKET-1 (mac): builder left the docstring.
- 2026-08-20 work TICKET-2 (mac): builder reported the gap. **GRADUATES at 2.**
- 2026-08-20 **outcome: accepted, installed.** Destination: SKILL.md:456.
"""


def ev(kind: str, issue: str | None = None, **fields) -> dict:
    return {"kind": kind, "run": "2026-09-21T00:10:00+00:00", **({"issue": issue} if issue else {}), **fields}


RUN = [
    ev("run-start"),
    ev("spec-approved", "421", tier="small"),
    ev("plan-review", "421", round="1", verdict="REVISE"),
    ev("plan-review", "421", round="2", verdict="APPROVE"),
    ev("dispatched", "421"),
    ev("fallback", "421", agent="codex_review", model="fable"),
    ev("review-round", "421", round="1", verdict="FINDINGS: 3"),
    ev("ruling", "421", text="persistence is out of scope"),
    ev("review-round", "421", round="2", verdict="FINDINGS: 1"),
    ev("review-round", "421", round="3", verdict="REVIEW CLEAN"),
    ev("gate-miss", "421", text="mypy count measured in the main checkout"),
    ev("lead-finding", "421", text="stale docstring"),
    ev("pr-opened", "421", pr="429", branch="fix/421-x"),
    ev("spec-approved", "422", tier="full"),
    ev("dispatched", "422"),
    ev("review-round", "422", round="1", verdict="REVIEW CLEAN"),
    ev("pr-opened", "422", pr="431", branch="fix/422-x"),
    ev("spec-approved", "427", tier="small"),
    ev("decision-needed", "427", text="input budget?"),
    ev("spec-approved", "426", tier="small"),
    ev("dispatched", "426"),
    ev("blocked", "426", text="needs an Anthropic key"),
]


def gh_states(states: dict[str, str]):
    def gh(args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(args, 0, json.dumps({"state": states[args[2]]}), "")
    return gh


def test_rows_count_every_ledger_column_from_the_run_log():
    rows = librarian.rows(RUN, "project-mera", gh_states({"429": "MERGED", "431": "OPEN"}))
    assert rows[0] == {"date": "2026-09-21", "repo": "project-mera", "ticket": "#421", "pr": "429",
                       "variant": "fallback", "tier": "small", "plan rounds": "2", "rounds": "3/3",
                       "findings": "3,1,0", "rulings": "1", "blocked": "0", "gate miss": "1", "lead": "1",
                       "outcome": "merged"}


def test_a_full_tier_build_reviewed_by_codex_has_cap_three_and_no_fallback():
    row = librarian.rows(RUN, "project-mera", gh_states({"429": "MERGED", "431": "OPEN"}))[1]
    assert (row["variant"], row["tier"], row["rounds"], row["findings"], row["outcome"]) == (
        "codex", "full", "1/3", "0", "open")


def test_an_issue_parked_on_a_decision_or_blocked_gets_that_outcome():
    rows = {r["ticket"]: r for r in librarian.rows(RUN, "project-mera", gh_states({"429": "MERGED", "431": "OPEN"}))}
    assert rows["#427"]["outcome"] == "parked" and rows["#427"]["rounds"] == "0/2"
    assert rows["#426"]["outcome"] == "blocked" and rows["#426"]["blocked"] == "1"


def test_a_build_past_its_cap_with_no_pr_is_capped():
    run = [ev("run-start"), ev("spec-approved", "9", tier="small"), ev("review-round", "9", round="1", verdict="FINDINGS: 2"),
           ev("review-round", "9", round="2", verdict="FINDINGS: 1"), ev("review-round", "9", round="3", verdict="FINDINGS: 1")]
    assert librarian.rows(run, "r", gh_states({}))[0]["outcome"] == "capped"


def test_a_row_renders_in_the_ledger_column_order():
    row = librarian.rows(RUN, "project-mera", gh_states({"429": "MERGED", "431": "OPEN"}))[0]
    assert librarian.render_row(row) == (
        "| 2026-09-21 | project-mera | #421 | 429 | fallback | small | 2 | 3/3 | 3,1,0 | 1 | 0 | 1 | 1 | merged |")


def test_append_rows_adds_rows_under_the_table_and_skips_ones_already_there(tmp_path):
    ledger = tmp_path / "herd-ledger.md"
    ledger.write_text(LEDGER_HEAD + "\nA note after the table.\n")
    rows = librarian.rows(RUN, "project-mera", gh_states({"429": "MERGED", "431": "OPEN"}))
    assert librarian.append_rows(ledger, rows) == 4
    assert librarian.append_rows(ledger, rows) == 0
    lines = ledger.read_text().splitlines()
    table_end = max(i for i, ln in enumerate(lines) if ln.startswith("|"))
    assert lines[table_end - 3].startswith("| 2026-09-21 | project-mera | #421 |")
    assert lines[-1] == "A note after the table."


def test_friction_append_files_a_line_under_an_existing_class_and_counts_its_events(tmp_path):
    ledger = tmp_path / "friction-ledger.md"
    ledger.write_text(FRICTION)
    n = librarian.friction_append(ledger, "gam-daemon-stall", "", "- 2026-09-21 project-mera #421 (windows): hung again.")
    assert n == 2
    text = ledger.read_text()
    assert text.index("memory_context hung 120s") < text.index("hung again") < text.index("## false-out-of-scope")


def test_friction_append_does_not_count_outcome_lines(tmp_path):
    ledger = tmp_path / "friction-ledger.md"
    ledger.write_text(FRICTION)
    assert librarian.friction_append(ledger, "false-out-of-scope", "", "- 2026-09-21 project-mera #423 (windows): again.") == 3


def test_friction_append_starts_a_new_class_at_the_end(tmp_path):
    ledger = tmp_path / "friction-ledger.md"
    ledger.write_text(FRICTION)
    n = librarian.friction_append(ledger, "reviewer-wrong-cwd", "reviewer pane opens in another worktree",
                                  "- 2026-09-21 project-mera #423 (windows): cd on every command.")
    assert n == 1
    assert ledger.read_text().endswith("\n## reviewer-wrong-cwd (reviewer pane opens in another worktree)\n"
                                       "- 2026-09-21 project-mera #423 (windows): cd on every command.\n")


def test_a_new_class_needs_a_title(tmp_path):
    ledger = tmp_path / "friction-ledger.md"
    ledger.write_text(FRICTION)
    with pytest.raises(SystemExit, match="new class reviewer-wrong-cwd needs --title"):
        librarian.friction_append(ledger, "reviewer-wrong-cwd", "", "- 2026-09-21 x (windows): y.")


def test_friction_lines_are_built_in_the_ledger_format():
    assert librarian.friction_line("2026-09-21", "project-mera", "423", "cd on every command") == (
        f"- 2026-09-21 project-mera #423 ({librarian.machine()}): cd on every command")


def test_retros_are_the_run_issues_retro_files_in_the_main_checkout(tmp_path):
    for name in ("RETRO-421-pi_build.md", "RETRO-422-codex_review.md", "RETRO-300-pi_build.md", "RETRO-lead.md"):
        (tmp_path / name).write_text("x\n")
    found = [p.name for p in librarian.retros(tmp_path, RUN)]
    assert found == ["RETRO-421-pi_build.md", "RETRO-422-codex_review.md"]


def test_a_row_is_dated_by_its_issue_first_event_not_the_run_start():
    run = [{"kind": "run-start", "run": "2026-09-20T23:50:00+00:00", "ts": "2026-09-20T23:50:00+00:00"},
           {"kind": "spec-approved", "issue": "427", "tier": "small", "run": "2026-09-20T23:50:00+00:00",
            "ts": "2026-09-21T14:02:00+00:00"}]
    assert librarian.rows(run, "r", gh_states({}))[0]["date"] == "2026-09-21"


def test_run_level_retros_are_listed_apart_from_issue_retros(tmp_path):
    for name in ("RETRO-421-pi_build.md", "RETRO-lead-fable.md", "RETRO-day2-opus_plan_reviewer.md",
                 "RETRO-321-pi_build.md"):
        (tmp_path / name).write_text("x\n")
    assert [p.name for p in librarian.run_level_retros(tmp_path)] == [
        "RETRO-day2-opus_plan_reviewer.md", "RETRO-lead-fable.md"]


def test_append_rows_skips_rows_with_no_review_counts(tmp_path):
    ledger = tmp_path / "herd-ledger.md"
    ledger.write_text(LEDGER_HEAD)
    run = [ev("run-start"), ev("pr-opened", "420", pr="428", branch="fix/420")]
    assert librarian.append_rows(ledger, librarian.rows(run, "r", gh_states({"428": "MERGED"}))) == 0
    assert "#420" not in ledger.read_text()


def test_report_opens_with_the_run_header(repo_with_worktree, capsys, monkeypatch):
    import runlog
    main, _ = repo_with_worktree
    runlog.main(["add", "run-start", "--repo", str(main), "--text", "reconstructed from the state file"])
    monkeypatch.setattr(librarian, "gh_runner", lambda repo: gh_states({}))
    assert librarian.main(["report", "--repo", str(main)]) == 0
    first = capsys.readouterr().out.splitlines()[0]
    assert first.startswith("run ") and first.endswith(": reconstructed from the state file")


def test_append_ledger_says_how_many_rows_it_skipped(repo_with_worktree, capsys, monkeypatch, tmp_path):
    import runlog
    main, _ = repo_with_worktree
    runlog.main(["add", "run-start", "--repo", str(main)])
    runlog.main(["add", "pr-opened", "--repo", str(main), "--issue", "420", "--pr", "428", "--branch", "fix/420"])
    ledger = tmp_path / "herd-ledger.md"
    ledger.write_text(LEDGER_HEAD)
    monkeypatch.setattr(librarian, "gh_runner", lambda repo: gh_states({"428": "MERGED"}))
    librarian.main(["append-ledger", "--repo", str(main), "--ledger", str(ledger)])
    assert capsys.readouterr().out.strip() == "appended 0 rows; skipped 1 with no review counts (no spec-approved)"


def test_a_ledger_with_nothing_to_add_is_left_byte_identical(tmp_path):
    ledger = tmp_path / "herd-ledger.md"
    ledger.write_text(LEDGER_HEAD.rstrip("\n"))
    before = ledger.read_bytes()
    run = [ev("run-start"), ev("pr-opened", "420", pr="428", branch="fix/420")]
    librarian.append_rows(ledger, librarian.rows(run, "r", gh_states({"428": "MERGED"})))
    assert ledger.read_bytes() == before


def test_the_vault_is_herd_vault_when_set(tmp_path):
    assert librarian.vault({"HERD_VAULT": str(tmp_path), "HOME": "/h"}) == tmp_path


def test_the_default_vault_is_the_xdg_data_dir_not_a_personal_one():
    assert librarian.vault({"XDG_DATA_HOME": "/x", "HOME": "/h"}) == pathlib.Path("/x/herd")
    assert librarian.vault({"HOME": "/h"}) == pathlib.Path("/h/.local/share/herd")
