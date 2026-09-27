import subprocess

import pytest

import dispatch

TIMED_OUT = subprocess.CompletedProcess([], 1, stdout="", stderr='{"error":"timed out waiting for agent status"}')
SETTLED = subprocess.CompletedProcess([], 0, stdout='{"result":{"agent_status":"idle"}}', stderr="")


def scripted(*replies):
    calls = []
    it = iter(replies)

    def run(argv):
        calls.append(argv)
        return next(it)

    run.calls = calls
    return run


def test_a_prompt_that_settles_needs_no_extra_wait(capsys):
    run = scripted(SETTLED)
    assert dispatch.dispatch("codex_review", "go", runner=run) == 0
    assert run.calls == [["herdr", "agent", "prompt", "codex_review", "go", "--wait", "--timeout", "540000"]]
    assert "settled after 0 extra waits" in capsys.readouterr().out


def test_a_timed_out_wait_means_still_working_and_is_followed_by_agent_wait():
    run = scripted(TIMED_OUT, TIMED_OUT, SETTLED)
    assert dispatch.dispatch("codex_review", "go", timeout=1000, runner=run) == 0
    assert run.calls[1:] == [["herdr", "agent", "wait", "codex_review", "--timeout", "1000"]] * 2


def test_any_other_error_fails_without_waiting(capsys):
    run = scripted(subprocess.CompletedProcess([], 1, stdout="", stderr="agent_blocked"))
    assert dispatch.dispatch("pi_build", "go", runner=run) == 1
    assert len(run.calls) == 1 and "agent_blocked" in capsys.readouterr().out


def test_waiting_is_bounded(capsys):
    run = scripted(TIMED_OUT, TIMED_OUT, TIMED_OUT)
    assert dispatch.dispatch("pi_build", "go", max_waits=2, runner=run) == 3
    assert "still working after 2 extra waits" in capsys.readouterr().out


def test_the_prompt_can_come_from_a_file(tmp_path, monkeypatch):
    f = tmp_path / "p.md"
    f.write_text("review round 1")
    seen = []
    monkeypatch.setattr(dispatch, "dispatch", lambda agent, text, **kw: seen.append((agent, text)) or 0)
    assert dispatch.main(["codex_review", "--file", str(f)]) == 0
    assert seen == [("codex_review", "review round 1")]


def test_text_and_file_are_exclusive(tmp_path):
    with pytest.raises(SystemExit):
        dispatch.main(["codex_review", "text", "--file", str(tmp_path / "x")])
