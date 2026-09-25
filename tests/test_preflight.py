import pytest

import preflight

ALL_TOOLS = {name: f"/usr/bin/{name}" for name in preflight.TOOLS}


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setattr(preflight.shutil, "which", ALL_TOOLS.get)
    return monkeypatch


def test_a_ready_machine_passes_with_one_line_per_check(env, capsys):
    assert preflight.main([]) == 0
    out = capsys.readouterr().out.splitlines()
    assert "ok   inside Herdr (HERDR_ENV=1)" in out
    assert all(f"ok   {t} on PATH" in out for t in preflight.TOOLS)


def test_a_missing_tool_fails_and_is_named(env, capsys):
    env.setattr(preflight.shutil, "which", {**ALL_TOOLS, "codex": None}.get)
    assert preflight.main([]) == 1
    assert "MISSING codex on PATH" in capsys.readouterr().out


def test_outside_herdr_fails(env, capsys):
    env.delenv("HERDR_ENV")
    assert preflight.main([]) == 1
    assert "MISSING inside Herdr (HERDR_ENV=1)" in capsys.readouterr().out


def test_a_needed_variable_is_reported_by_issue_without_its_value(env, capsys):
    env.setenv("WCL_CLIENT_ID", "secret-value-123")
    env.delenv("ANTHROPIC_API_KEY", raising=False)
    assert preflight.main(["--need", "426:ANTHROPIC_API_KEY", "--need", "421:WCL_CLIENT_ID"]) == 1
    out = capsys.readouterr().out
    assert "MISSING ANTHROPIC_API_KEY for #426" in out
    assert "ok   WCL_CLIENT_ID for #421" in out
    assert "secret-value-123" not in out


def test_an_empty_variable_counts_as_missing(env, capsys):
    env.setenv("ANTHROPIC_API_KEY", "")
    assert preflight.main(["--need", "426:ANTHROPIC_API_KEY"]) == 1
    assert "MISSING ANTHROPIC_API_KEY for #426" in capsys.readouterr().out


def test_a_need_without_an_issue_is_refused(env):
    with pytest.raises(SystemExit, match="--need takes ISSUE:VARIABLE"):
        preflight.main(["--need", "ANTHROPIC_API_KEY"])
