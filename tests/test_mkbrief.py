import sys

import pytest

import mkbrief


def brief(repo_with_worktree, **overrides):
    main, wt = repo_with_worktree
    args = dict(id="42", worktree=wt, branch="fix/42-x", base="main", change="fix-x",
                gates="GATES\n", allowed="  - src/x.py", python="/py/bin/python",
                lead_pane="w9:p9Z", reviewer="codex_review", has_xdist=False)
    args.update(overrides)
    return main, wt, mkbrief.build_briefing(**args), mkbrief.build_reviewer_prompt(**args)


def test_briefing_names_the_derived_main_checkout(repo_with_worktree):
    main, _, briefing, _ = brief(repo_with_worktree)
    assert f"Do NOT touch `{main.resolve()}`" in briefing


def test_briefing_sends_rounds_to_the_named_reviewer_and_sentinels_to_the_lead_pane(repo_with_worktree):
    _, _, briefing, _ = brief(repo_with_worktree, reviewer="claude_review", lead_pane="w3:p7Q")
    assert 'herdr agent prompt claude_review "$(cat CODEX-PROMPT-42-round-N.md)"' in briefing
    assert "herdr agent wait claude_review --timeout 540000" in briefing
    assert 'herdr agent prompt w3:p7Q "DONE: build for 42' in briefing
    assert 'herdr agent prompt w3:p7Q "BLOCKED: 42' in briefing


def test_reviewer_prompt_signs_off_to_the_lead_pane(repo_with_worktree):
    _, _, _, prompt = brief(repo_with_worktree, lead_pane="w3:p7Q")
    assert 'herdr agent prompt w3:p7Q "REVIEW CLEAN for 42 after ROUND_N rounds"' in prompt


def test_briefing_and_prompt_use_the_given_python(repo_with_worktree):
    _, _, briefing, prompt = brief(repo_with_worktree, python="/venvs/x/bin/python")
    assert "`/venvs/x/bin/python`" in briefing
    assert "PYTHONPATH=src /venvs/x/bin/python -m pytest" in prompt


def test_briefing_says_xdist_is_missing_when_it_is(repo_with_worktree):
    _, _, briefing, _ = brief(repo_with_worktree, has_xdist=False)
    assert "`pytest-xdist` is NOT installed. Do not install anything." in briefing


def test_briefing_says_xdist_is_available_when_it_is(repo_with_worktree):
    _, _, briefing, _ = brief(repo_with_worktree, has_xdist=True)
    assert "`pytest-xdist` is installed" in briefing
    assert "NOT installed" not in briefing


def test_lead_pane_comes_from_herdr_pane_id(monkeypatch):
    monkeypatch.setenv("HERDR_PANE_ID", "w5:p5A")
    assert mkbrief.resolve_lead_pane(None) == "w5:p5A"


def test_explicit_lead_pane_wins_over_herdr_pane_id(monkeypatch):
    monkeypatch.setenv("HERDR_PANE_ID", "w5:p5A")
    assert mkbrief.resolve_lead_pane("w1:p1B") == "w1:p1B"


def test_missing_lead_pane_is_an_error_naming_both_sources(monkeypatch):
    monkeypatch.delenv("HERDR_PANE_ID", raising=False)
    with pytest.raises(SystemExit, match="--lead-pane.*HERDR_PANE_ID"):
        mkbrief.resolve_lead_pane(None)


def test_main_writes_both_files(repo_with_worktree, tmp_path, monkeypatch):
    _, wt = repo_with_worktree
    monkeypatch.setenv("HERDR_PANE_ID", "w5:p5A")
    monkeypatch.setenv("HERD_PYTHON", sys.executable)
    gates = tmp_path / "gates.txt"
    gates.write_text("G\n")
    allowed = tmp_path / "allowed.txt"
    allowed.write_text("  - src/x.py\n")
    mkbrief.main(["42", str(wt), "fix/42-x", "main", "fix-x", str(gates), str(allowed)])
    assert "w5:p5A" in (wt / "BUILD-BRIEFING-42.md").read_text()
    assert "codex_review" in (wt / "BUILD-BRIEFING-42.md").read_text()
    assert (wt / "CODEX-PROMPT-42.md").exists()
