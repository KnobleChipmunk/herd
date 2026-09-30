import pathlib
import subprocess

import pytest

import probe
import runlog

SKILL = pathlib.Path(probe.__file__).resolve().parent.parent / "skill" / "SKILL.md"


def ok(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(cmd, 0, "OK\n", "")


def refuse(*models: str):
    def run(cmd: list[str]) -> subprocess.CompletedProcess:
        if any(m in cmd for m in models):
            return subprocess.CompletedProcess(cmd, 1, "", "model is not supported when using Codex with a ChatGPT account")
        return ok(cmd)
    return run


def test_the_shipped_roster_gives_the_plan_reviewer_its_whole_chain():
    roster = probe.parse_roster(SKILL.read_text())
    assert probe.chain(roster, "Plan reviewer") == [
        ("Codex", "gpt-6-astra"), ("Codex", "gpt-6-sol"), ("Claude Code", "fable"), ("Claude Code", "sonnet")]


def test_the_shipped_roster_gives_the_build_reviewer_sol_then_claude():
    roster = probe.parse_roster(SKILL.read_text())
    assert probe.chain(roster, "Build reviewer") == [
        ("Codex", "gpt-6-sol"), ("Claude Code", "fable"), ("Claude Code", "sonnet")]


def test_the_shipped_roster_builds_with_codex_on_the_local_profile_then_pi():
    # The builder's model is local in both harnesses; Codex reaches it
    # through its swift15 profile (project-mera #380: four builds, each
    # byte-identical to the reference).
    roster = probe.parse_roster(SKILL.read_text())
    assert roster["Builder"]["models"] == ["swift15-codex"]
    assert roster["Builder"]["panes"] == ["codex_build"]
    assert probe.chain(roster, "Builder") == [
        ("Codex, profile `swift15`", "swift15-codex"), ("pi", "swift15-qwen3.8-128k:latest")]


@pytest.mark.parametrize("harness, model, cmd", [
    ("Codex", "gpt-6-sol", ["codex", "exec", "-m", "gpt-6-sol", probe.PROMPT]),
    ("Claude Code", "fable", ["claude", "-p", "--model", "fable", probe.PROMPT]),
    ("pi", "swift15-qwen3.8-128k:latest", ["pi", "--model", "swift15-qwen3.8-128k:latest", "-p", probe.PROMPT]),
    ("Codex, profile `swift15`", "swift15-codex",
     ["codex", "--profile", "swift15", "exec", "--skip-git-repo-check", "-m", "swift15-codex", probe.PROMPT]),
])
def test_each_harness_is_probed_with_its_own_command(harness, model, cmd):
    assert probe.probe_command(harness, model) == cmd


def test_an_unknown_harness_is_an_error():
    with pytest.raises(SystemExit, match="no probe for harness 'Gemini'"):
        probe.probe_command("Gemini", "x")


def test_choose_takes_the_first_candidate_that_answers_ok():
    chosen, tried = probe.choose([("Codex", "gpt-6-astra"), ("Codex", "gpt-6-sol")], refuse("gpt-6-astra"))
    assert chosen == ("Codex", "gpt-6-sol")
    assert tried == ["gpt-6-astra: model is not supported when using Codex with a ChatGPT account"]


def test_an_answer_without_ok_is_not_a_pass():
    def chatty(cmd):
        return subprocess.CompletedProcess(cmd, 0, "I cannot help with that.\n", "")
    chosen, tried = probe.choose([("Codex", "gpt-6-astra")], chatty)
    assert chosen is None
    assert tried == ["gpt-6-astra: no OK in the reply"]


def test_a_timeout_moves_to_the_next_candidate():
    def slow(cmd):
        if "gpt-6-astra" in cmd:
            raise subprocess.TimeoutExpired(cmd, 180)
        return ok(cmd)
    chosen, tried = probe.choose([("Codex", "gpt-6-astra"), ("Codex", "gpt-6-sol")], slow)
    assert chosen == ("Codex", "gpt-6-sol")
    assert tried == ["gpt-6-astra: no answer in 180s"]


def test_main_reports_each_role_and_logs_a_fallback(repo_with_worktree, capsys, monkeypatch):
    main, _ = repo_with_worktree
    runlog.main(["add", "run-start", "--repo", str(main)])
    monkeypatch.setattr(probe, "run", refuse("gpt-6-astra"))
    assert probe.main(["--skill", str(SKILL), "--log", "--repo", str(main)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert "Builder: swift15-codex (Codex, profile `swift15`)" in out
    assert "Plan reviewer: gpt-6-sol (Codex) — FALLBACK; gpt-6-astra: model is not supported when using Codex" \
           " with a ChatGPT account" in out
    assert "Build reviewer: gpt-6-sol (Codex)" in out
    fallbacks = [e for e in runlog.latest_run(main) if e["kind"] == "fallback"]
    assert [(e["agent"], e["model"]) for e in fallbacks] == [("codex_plan_reviewer", "gpt-6-sol")]


def test_main_exits_one_when_a_role_has_no_working_model(capsys, monkeypatch):
    monkeypatch.setattr(probe, "run", refuse("gpt-6-sol", "fable", "sonnet"))
    assert probe.main(["--skill", str(SKILL), "--role", "Build reviewer"]) == 1
    assert "Build reviewer: NONE" in capsys.readouterr().out


def test_the_roster_is_exactly_the_first_table_after_its_heading():
    roster = probe.parse_roster(SKILL.read_text())
    assert list(roster) == ["Lead", "Builder", "Fallback builder", "Plan reviewer", "Build reviewer",
                            "Fallback reviewer"]
