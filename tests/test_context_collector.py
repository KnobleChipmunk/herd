import datetime
import json
import os
import pathlib

import pytest

import attention
import context_collector as cc

SAMPLE = {"session_id": "abc", "context_window": {"used_percentage": 37.5, "context_window_size": 1000000}}
NOW = datetime.datetime(2026, 9, 27, 12, 0, 0, tzinfo=datetime.timezone.utc)
TODAY = datetime.date(2026, 9, 27)


@pytest.fixture
def pane(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("HERDR_PANE_ID", "w1:p9")
    return tmp_path / "state" / "herd" / "context" / "w1:p9.json"


# --- the status line passes through untouched ------------------------------------

def test_stdout_stderr_and_exit_code_pass_through_the_shell(pane, capfd):
    stdin = json.dumps(SAMPLE).encode()
    code = cc.run(stdin, "printf 'LINE %s' $(wc -c); echo oops >&2; exit 3", NOW)
    out, err = capfd.readouterr()
    assert code == 3 and out == f"LINE {len(stdin)}" and err == "oops\n"


def test_shell_syntax_in_the_saved_command_is_kept(pane, capfd):
    assert cc.run(b"{}", "GREETING='hello there' sh -c 'echo \"$GREETING\"'", NOW) == 0
    assert capfd.readouterr().out == "hello there\n"


def test_a_missing_command_reports_the_shells_status(pane, capfd):
    assert cc.run(b"{}", "/nonexistent/statusline.sh", NOW) == 127


# --- recording ---------------------------------------------------------------

def test_the_sample_is_recorded_by_pane_after_the_command_runs(pane, capfd):
    order = []
    cc.run(json.dumps(SAMPLE).encode(), f"test ! -e '{pane}' && echo absent-while-running", NOW)
    order.append(capfd.readouterr().out)
    assert order == ["absent-while-running\n"]
    assert json.loads(pane.read_text()) == {"pane": "w1:p9", "session_id": "abc", "used_percentage": 37.5,
                                            "ts": NOW.isoformat()}


@pytest.mark.parametrize("stdin", [b"not json", b"[]", json.dumps({"x": "y" * (cc.MAX_INPUT + 1)}).encode()],
                         ids=["not-json", "a-list", "oversized"])
def test_bad_or_oversized_input_is_not_recorded(pane, stdin):
    assert cc.run(stdin, "true", NOW) == 0
    assert not pane.exists()


def test_outside_herdr_nothing_is_recorded(pane, monkeypatch):
    monkeypatch.delenv("HERDR_PANE_ID")
    cc.run(json.dumps(SAMPLE).encode(), "true", NOW)
    assert not pane.parent.exists() or list(pane.parent.iterdir()) == []


@pytest.mark.parametrize("pct", [None, True, "37", float("nan"), float("inf")])
def test_a_missing_or_non_numeric_percentage_is_recorded_as_unknown(pane, pct):
    cc.run(json.dumps({"session_id": "a", "context_window": {"used_percentage": pct}}).encode(), "true", NOW)
    assert json.loads(pane.read_text())["used_percentage"] is None


# --- install / uninstall -----------------------------------------------------

ORIGINAL = "FOO='a b' /home/u/.claude/statusline-command.sh --flag"


def settings(tmp_path, command=ORIGINAL):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"model": "opus", "statusLine": {"type": "command", "command": command}}, indent=2))
    os.chmod(p, 0o600)
    return p


def test_install_saves_the_original_verbatim_and_wraps_with_quoted_paths(tmp_path):
    s, home = settings(tmp_path), tmp_path / "share dir"
    assert cc.install(s, home=home, today=TODAY) == 0
    doc = json.loads(s.read_text())
    assert doc["model"] == "opus"
    assert doc["statusLine"]["command"] == cc.installed_command(home / "context_collector.py", cc.meta_path(home, s))
    assert "'" in doc["statusLine"]["command"]  # the paths with a space are quoted
    assert json.loads((cc.meta_path(home, s)).read_text())["original"] == ORIGINAL
    assert (home / "context_collector.py").read_text() == pathlib.Path(cc.__file__).read_text()
    assert json.loads((tmp_path / "settings.json.bak-herd-2026-09-27").read_text())["statusLine"]["command"] == ORIGINAL
    assert s.stat().st_mode & 0o777 == 0o600


def test_the_installed_command_runs_the_saved_original(tmp_path, pane, capfd, monkeypatch):
    home = tmp_path / "share"
    s = settings(tmp_path, command="echo from-the-original")
    cc.install(s, home=home, today=TODAY)
    capfd.readouterr()
    monkeypatch.setattr(cc.sys, "stdin", type("S", (), {"buffer": type("B", (), {"read": lambda self: b"{}"})()})())
    assert cc.main(["--meta", str(cc.meta_path(home, s))]) == 0
    assert capfd.readouterr().out == "from-the-original\n"


def test_install_twice_neither_rewraps_nor_overwrites_a_backup(tmp_path):
    s, home = settings(tmp_path), tmp_path / "share"
    cc.install(s, home=home, today=TODAY)
    once = s.read_text()
    assert cc.install(s, home=home, today=TODAY) == 0 and s.read_text() == once
    assert json.loads((cc.meta_path(home, s)).read_text())["original"] == ORIGINAL  # never the wrapper itself
    cc.uninstall(s, home=home)
    cc.install(s, home=home, today=TODAY)
    assert (tmp_path / "settings.json.bak-herd-2026-09-27-2").exists()


def test_uninstall_restores_exactly_and_only_its_own_install(tmp_path):
    s, home = settings(tmp_path), tmp_path / "share"
    cc.install(s, home=home, today=TODAY)
    assert cc.uninstall(s, home=home) == 0
    assert json.loads(s.read_text())["statusLine"]["command"] == ORIGINAL
    cc.install(s, home=home, today=TODAY)
    doc = json.loads(s.read_text())
    doc["statusLine"]["command"] = "my-new-line --uses context_collector.py -- somewhere"
    s.write_text(json.dumps(doc))
    assert cc.uninstall(s, home=home) == 2
    assert json.loads(s.read_text())["statusLine"]["command"] == "my-new-line --uses context_collector.py -- somewhere"


def test_install_refuses_when_there_is_no_status_line_to_wrap(tmp_path, capsys):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"model": "opus"}))
    assert cc.install(p, home=tmp_path / "share", today=TODAY) == 2
    assert "no statusLine command to wrap" in capsys.readouterr().out
    assert json.loads(p.read_text()) == {"model": "opus"}


# --- the monitor ---------------------------------------------------------------

def test_the_monitor_shows_context_only_for_claude_panes_and_skips_bad_samples(tmp_path):
    ts = (NOW - datetime.timedelta(minutes=3)).isoformat()
    (tmp_path / "a.json").write_text(json.dumps({"pane": "w1:p1", "session_id": "a", "used_percentage": 64.2, "ts": ts}))
    (tmp_path / "b.json").write_text(json.dumps({"pane": "w1:p2", "session_id": "b", "used_percentage": 80, "ts": ts}))
    (tmp_path / "bad1.json").write_text("{not json")
    (tmp_path / "bad2.json").write_text(json.dumps({"pane": "w1:p3", "used_percentage": True, "ts": ts}))
    (tmp_path / "bad3.json").write_text(json.dumps({"pane": "w1:p4", "used_percentage": 5, "ts": "2026-09-27T12:00:00"}))
    samples = cc.samples(tmp_path)
    assert sorted(samples) == ["w1:p1", "w1:p2"]
    agents = [{"name": "lead", "pane_id": "w1:p1", "agent": "claude", "agent_status": "working", "tab_id": "t"},
              {"name": "pi_build", "pane_id": "w1:p2", "agent": "pi", "agent_status": "idle", "tab_id": "t"}]
    out = "\n".join(attention.monitor([], agents, NOW, tab="t", context=samples))
    lead = next(ln for ln in out.splitlines() if ln.strip().startswith("lead"))
    build = next(ln for ln in out.splitlines() if ln.strip().startswith("pi_build"))
    assert "context 64% (3m ago)" in lead and "context unknown" in build


def test_a_signal_death_is_reported_as_a_shell_would(pane):
    assert cc.run(b"{}", "kill -TERM $$", NOW) == 143


def test_installs_into_two_settings_files_stay_independent(tmp_path):
    home = tmp_path / "share"
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    first, second = settings(tmp_path / "a", command="first-line"), settings(tmp_path / "b", command="second-line")
    cc.install(first, home=home, today=TODAY)
    cc.install(second, home=home, today=TODAY)
    assert cc.uninstall(first, home=home) == 0 and cc.uninstall(second, home=home) == 0
    assert json.loads(first.read_text())["statusLine"]["command"] == "first-line"
    assert json.loads(second.read_text())["statusLine"]["command"] == "second-line"


def test_a_non_finite_sample_shows_unknown_and_does_not_stop_the_monitor(tmp_path):
    (tmp_path / "x.json").write_text('{"pane": "w1:p1", "session_id": "a", "used_percentage": NaN, "ts": "2026-09-27T11:57:00+00:00"}')
    assert cc.samples(tmp_path) == {}
    lead = {"name": "lead", "pane_id": "w1:p1", "agent": "claude", "agent_status": "idle", "tab_id": "t"}
    out = "\n".join(attention.monitor([], [lead], NOW, tab="t", context={"w1:p1": {"used_percentage": float("inf"), "ts": NOW.isoformat()}}))
    assert "context unknown" in out


def test_a_huge_integer_sample_is_skipped_not_crashed_on(tmp_path):
    (tmp_path / "x.json").write_text('{"pane": "w1:p1", "used_percentage": 1' + "0" * 400 + ', "ts": "2026-09-27T11:57:00+00:00"}')
    assert cc.samples(tmp_path) == {}
    assert cc.finite_number(10 ** 400) is False and cc.finite_number(42.5) is True


def test_a_symlinked_settings_file_stays_a_symlink(tmp_path):
    real = settings(tmp_path)
    link = tmp_path / "linked-settings.json"
    link.symlink_to(real)
    home = tmp_path / "share"
    assert cc.install(link, home=home, today=TODAY) == 0
    assert link.is_symlink() and json.loads(real.read_text())["statusLine"]["command"].startswith("python3 ")
    assert cc.uninstall(link, home=home) == 0 and link.is_symlink()
    assert json.loads(real.read_text())["statusLine"]["command"] == ORIGINAL



def test_a_dangling_symlink_at_the_backup_name_is_taken_not_written_through(tmp_path):
    s, home = settings(tmp_path), tmp_path / "share"
    outside = tmp_path / "outside.json"
    (tmp_path / "settings.json.bak-herd-2026-09-27").symlink_to(outside)
    assert cc.install(s, home=home, today=TODAY) == 0
    assert not outside.exists()
    assert json.loads((tmp_path / "settings.json.bak-herd-2026-09-27-2").read_text())["statusLine"]["command"] == ORIGINAL
