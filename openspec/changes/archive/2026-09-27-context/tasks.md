# Tasks — context % (#41)

Tier: **full**. DEPENDS ON #39: the branch is stacked on `feat/39-setup`.
Fences are generated from the lead's pre-executed tree; `tools/fencecheck.py` must print `FENCES OK (6 steps)`.

## 1. Tests first — apply T1, T2, then observe RED

- [ ] **T1** `tests/test_context_collector.py` — acceptance tests for the collector, install and the monitor column

Create this file with exactly this body (byte-exact, ends with one newline):

```python
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
```

- [ ] **T2** `tests/test_skill_text.py` — the monitor names the collector

Append exactly this text at the END of the file. The fence below BEGINS with the blank lines that separate it from the existing last line — keep them. The file must end with one newline:

```python

def test_the_monitor_names_the_context_collector():
    text = " ".join(SKILL.read_text().split())
    monitoring = text[text.index("## Monitoring"): text.index("## Rulings")]
    assert "context_collector.py install" in monitoring and "uninstall" in monitoring

```

RED after T1–T2: `tests/test_context_collector.py` fails to collect (no module `context_collector`); the new skill-text test fails.

## 2. Implementation — apply I1–I4

- [ ] **I1** `pyproject.toml` — register the new module for isort

Find this exact text (it occurs exactly once):

```python
"bindings", "fencecheck",
```

Replace it with exactly:

```python
"bindings", "context_collector", "fencecheck",
```

- [ ] **I2** `tools/context_collector.py` — the status-line collector with install/uninstall

Create this file with exactly this body (byte-exact, ends with one newline):

```python
"""Record each Claude Code pane's context use for the monitor, around the existing status line (#41).

usage: context_collector.py --meta PATH              (Claude Code runs this as its statusLine command)
       context_collector.py install   [--settings PATH]
       context_collector.py uninstall [--settings PATH]

`install` saves the current `statusLine.command` verbatim in
~/.local/share/herd/statusline-<hash of the settings path>.json, copies this file beside it, backs
settings.json up under a new dated name, and atomically sets the command to
`python3 '<collector>' --meta '<statusline.json>'`. At each refresh the
collector first runs the saved command through the shell, exactly as Claude
Code would, with the same stdin and with stdout and stderr passed through
untouched, and exits with its status. Only then, best effort, it records
`{pane, session_id, used_percentage, ts}` from the same JSON (Claude Code's
`context_window.used_percentage`, which may be null) under
$XDG_STATE_HOME/herd/context/<HERDR_PANE_ID>.json. Input over 1 MB, a missing
HERDR_PANE_ID or any error skips recording and never touches the status line.
`uninstall` restores the saved command only if the setting is still exactly
the one install wrote. A pane moved to another workspace keeps its old id in
its environment, so its context shows unknown until it restarts.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
import os
import pathlib
import shlex
import shutil
import subprocess
import sys

MAX_INPUT = 1_000_000


def finite_number(value) -> bool:
    """A real, finite number (not a bool); never raises, even for huge integers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def state_dir() -> pathlib.Path:
    base = os.environ.get("XDG_STATE_HOME") or str(pathlib.Path.home() / ".local" / "state")
    return pathlib.Path(base) / "herd" / "context"


def record(stdin: bytes, now: datetime.datetime) -> None:
    pane = os.environ.get("HERDR_PANE_ID")
    if not pane or len(stdin) > MAX_INPUT:
        return
    try:
        data = json.loads(stdin)
        pct = (data.get("context_window") or {}).get("used_percentage")
        if not finite_number(pct):
            pct = None
        sample = {"pane": pane, "session_id": data.get("session_id"), "used_percentage": pct, "ts": now.isoformat()}
        d = state_dir()
        d.mkdir(parents=True, exist_ok=True)
        tmp = d / f".{pane}.{os.getpid()}.tmp"
        tmp.write_text(json.dumps(sample))
        os.replace(tmp, d / f"{pane}.json")
    except Exception:  # the status line must never break because of the collector
        return


def run(stdin: bytes, command: str | None, now: datetime.datetime) -> int:
    """Run the saved command through the shell with inherited stdout/stderr, then record."""
    code = 0
    if command:
        code = subprocess.run(command, shell=True, input=stdin, check=False).returncode
        code = code if code >= 0 else 128 - code  # killed by a signal: report it as a shell would
    record(stdin, now)
    return code


def samples(directory: pathlib.Path | None = None) -> dict[str, dict]:
    """Every valid recorded sample, keyed by pane; an invalid file is skipped."""
    d = directory or state_dir()
    out = {}
    for f in d.glob("*.json") if d.exists() else []:
        try:
            s = json.loads(f.read_text())
            pct = s.get("used_percentage")
            ts = datetime.datetime.fromisoformat(s["ts"])
            if not isinstance(s.get("pane"), str) or ts.tzinfo is None or (pct is not None and not finite_number(pct)):
                continue
            out[s["pane"]] = s
        except (ValueError, KeyError, TypeError, AttributeError, OSError):
            continue
    return out


def _write_atomic(path: pathlib.Path, text: str) -> None:
    """Replace the file atomically, keeping its mode; a symlink is followed, so the link itself survives."""
    path = path.resolve() if path.is_symlink() else path
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text)
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def _backup(settings: pathlib.Path, today: datetime.date) -> pathlib.Path:
    n, target = 1, settings.with_name(f"{settings.name}.bak-herd-{today.isoformat()}")
    while target.exists() or target.is_symlink():
        n += 1
        target = settings.with_name(f"{settings.name}.bak-herd-{today.isoformat()}-{n}")
    shutil.copy2(settings, target)
    return target


def meta_path(home: pathlib.Path, settings: pathlib.Path) -> pathlib.Path:
    """One metadata file per settings file, so installs into two settings files stay independent."""
    return home / f"statusline-{hashlib.sha1(str(settings.resolve()).encode()).hexdigest()[:10]}.json"


def installed_command(collector: pathlib.Path, meta: pathlib.Path) -> str:
    return f"python3 {shlex.quote(str(collector))} --meta {shlex.quote(str(meta))}"


def install(settings: pathlib.Path, *, home: pathlib.Path | None = None, today: datetime.date) -> int:
    doc = json.loads(settings.read_text())
    command = (doc.get("statusLine") or {}).get("command")
    if not command:
        print("no statusLine command to wrap; nothing changed")
        return 2
    home = home or pathlib.Path.home() / ".local" / "share" / "herd"
    collector, meta = home / "context_collector.py", meta_path(home, settings)
    if command == installed_command(collector, meta):
        print("already wrapped")
        return 0
    home.mkdir(parents=True, exist_ok=True)
    _write_atomic(collector, pathlib.Path(__file__).read_text())
    _write_atomic(meta, json.dumps({"original": command, "installed": installed_command(collector, meta)}))
    backup = _backup(settings, today)
    doc["statusLine"]["command"] = installed_command(collector, meta)
    _write_atomic(settings, json.dumps(doc, indent=2) + "\n")
    print(f"wrapped (backup {backup.name}): {doc['statusLine']['command']}")
    return 0


def uninstall(settings: pathlib.Path, *, home: pathlib.Path | None = None) -> int:
    home = home or pathlib.Path.home() / ".local" / "share" / "herd"
    meta = meta_path(home, settings)
    doc = json.loads(settings.read_text())
    command = (doc.get("statusLine") or {}).get("command")
    saved = json.loads(meta.read_text()) if meta.exists() else None
    if not saved or command != saved["installed"]:
        print("the status line is not the one install wrote; nothing changed")
        return 0 if not saved else 2
    doc["statusLine"]["command"] = saved["original"]
    _write_atomic(settings, json.dumps(doc, indent=2) + "\n")
    print(f"restored: {saved['original']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in ("install", "uninstall"):
        path = pathlib.Path(argv[2]) if len(argv) > 2 and argv[1] == "--settings" else \
            pathlib.Path.home() / ".claude" / "settings.json"
        return install(path, today=datetime.date.today()) if argv[0] == "install" else uninstall(path)
    command = None
    if len(argv) == 2 and argv[0] == "--meta":
        try:
            command = json.loads(pathlib.Path(argv[1]).read_text())["original"]
        except (OSError, ValueError, KeyError):
            command = None
    return run(sys.stdin.buffer.read(), command, datetime.datetime.now(datetime.timezone.utc))


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **I3** `tools/attention.py` — the monitor's context column

REPLACE THE WHOLE FILE. Delete everything in it and write exactly this body (byte-exact, ends with one newline):

```python
"""Tell the operator when a human is needed, and show every agent and ticket in one place (#33, #34).

usage: attention.py scan    [--repo PATH] [--tab TAB] [--json]
       attention.py watch   [--repo PATH] [--tab TAB] [--interval S] [--ntfy URL] [--once]
       attention.py monitor [--repo PATH] [--tab TAB] [--interval S] [--once]

One rule set, read by both the watcher and the monitor. It joins the run log
(what is owed) with `herdr agent list` (what each agent is doing), in the
spirit of OpenRig's state taxonomy: activity and obligations stay separate,
and a diagnosis is computed at read time, never stored.

- decision (operator): a `decision-needed` from any run with no later
  `decision-made` for the same issue.
- permission (operator): a pane Herdr reports `blocked` (an approval or
  question dialog), one alert per blocked episode.
- pr-ready (operator): each `pr-opened` of the latest run; the watcher batches them.
- run-end (info): the latest run ended.
- overdue (lead): a worker `blocked` event older than --overdue minutes. It is
  the lead's to rule on, so it is shown, never sent to the operator.
- parked (operator): the run is open, work is in flight, nobody in the run's
  tab is working, no agent there is of unknown or blocked state, and the log
  has been quiet for --stall minutes. An issue waiting on the operator is
  HELD: it keeps its decision alert and never raises a stall, and answering
  the decision makes it eligible again. An issue with an open `wait` (a
  deliberate wait with a reason: resource, peer, environment, auth,
  rate-limit, scheduled) is not a stall either. When `herdr agent list` fails
  or the run's tab is unknown, nothing is claimed about who is working.

The watcher sends each operator or info item once: its key is the log record's
byte offset plus a hash of the line, so a replaced log cannot suppress a new
alert at a reused offset. An item counts as sent only when the Herdr
notification succeeded; a failed one is retried on the next poll, and ntfy is
best effort. Sent keys live in <git common dir>/herd/attention-state.json,
written atomically. One watcher runs per repository: a second one exits at
once. The run's tab is the one its `run-start` recorded (`--tab`), re-read on
every poll, so one watcher follows successive runs.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

import runlog
from herdtool import git_common_dir

IN_FLIGHT = ("spec-approved", "plan-review", "worktree-created", "dispatched", "review-round")
DECISIONS = ("decision-needed", "decision-made")
STALL_MINUTES = 20
OVERDUE_MINUTES = 15


def read_events(path: pathlib.Path) -> list[dict]:
    """The log's events, each with `_id` = "<byte offset>:<12 hex of the line's sha1>"."""
    if not path.exists():
        return []
    events, at = [], 0
    for line in path.read_bytes().splitlines(keepends=True):
        if line.strip():
            events.append({"_id": f"{at}:{hashlib.sha1(line).hexdigest()[:12]}", **json.loads(line)})
        at += len(line)
    return events


def age_minutes(e: dict, now: datetime.datetime) -> float:
    return (now - datetime.datetime.fromisoformat(e["ts"])).total_seconds() / 60


def item(kind: str, audience: str, key: str, title: str, body: str, subject: str) -> dict:
    return {"kind": kind, "audience": audience, "key": key, "title": title, "body": body, "subject": subject}


def open_decisions(events: list[dict]) -> list[dict]:
    return [e for i, e in enumerate(events) if e["kind"] == "decision-needed"
            and not any(x["kind"] == "decision-made" and x.get("issue") == e.get("issue") for x in events[i + 1:])]


def latest_progress(run: list[dict], skip: tuple = ()) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for e in run:
        if e.get("issue") and e["kind"] in runlog.PROGRESS and e["kind"] not in skip:
            out[e["issue"]] = e
    return out


def diagnose(events: list[dict], agents: list[dict] | None, now: datetime.datetime, *, tab: str | None,
             stall_after: float = STALL_MINUTES, overdue_after: float = OVERDUE_MINUTES) -> list[dict]:
    """Every attention item, in a fixed order: decisions, permissions, PRs, run end, overdue blocks, stall.
    `agents` is None when `herdr agent list` failed: then no permission or stall is claimed."""
    run = runlog.latest(events)
    items = []
    decisions = open_decisions(events)
    for e in decisions:
        items.append(item("decision", "operator", e["_id"], f"Decision needed: #{e.get('issue', '?')}",
                          e.get("text", ""), f"#{e.get('issue', '?')}"))
    for a in agents or []:
        if a.get("agent_status") == "blocked":
            who = a.get("name") or a["pane_id"]
            items.append(item("permission", "operator", f"blocked:{a['pane_id']}:{a.get('state_change_seq')}",
                              f"Permission needed: {who}",
                              f"{a.get('agent', 'agent')} in {a['pane_id']} is waiting at an approval or question",
                              who))
    for e in run:
        if e["kind"] == "pr-opened":
            items.append(item("pr-ready", "operator", e["_id"], f"PR #{e['pr']} ready to merge",
                              f"#{e.get('issue', '?')} {e.get('branch', '')}".strip(), f"#{e.get('issue', '?')}"))
    ended = [e for e in run if e["kind"] == "run-end"]
    if ended:
        items.append(item("run-end", "info", ended[-1]["_id"], "Run ended", ended[-1].get("text", run[0]["run"]),
                          run[0]["run"]))
    for i, e in enumerate(run):
        if e["kind"] == "blocked" and age_minutes(e, now) >= overdue_after and not any(
                x["kind"] in ("done", "pr-opened") and x.get("issue") == e.get("issue") for x in run[i + 1:]):
            items.append(item("overdue", "lead", e["_id"], f"Lead intervention overdue: #{e.get('issue', '?')}",
                              e.get("text", ""), f"#{e.get('issue', '?')}"))
    if run and not ended and agents is not None and tab:
        held = {e.get("issue") for e in decisions}
        waiting = {i for i, e in latest_progress(run).items() if e["kind"] == "wait"}
        flying = [i for i, e in latest_progress(run, DECISIONS + ("wait",)).items()
                  if e["kind"] in IN_FLIGHT and i not in held and i not in waiting]
        mine = [a for a in agents if a.get("tab_id") == tab]
        quiet = age_minutes(run[-1], now)
        if flying and quiet >= stall_after and not any(a.get("agent_status") in ("working", "unknown", "blocked")
                                                       for a in mine):
            items.append(item("parked", "operator", f"parked:{run[-1]['_id']}", "Run may be stalled",
                              f"in flight: {' '.join('#' + i for i in flying)}; nobody working; "
                              f"last log event {int(quiet)}m ago", " ".join('#' + i for i in flying)))
    return items


def herdr_sink(title: str, body: str, sound: str) -> bool:
    """True only when Herdr reports the notification shown: it exits 0 even when it drops one as
    rate-limited (`"shown": false, "reason": "rate_limited"`), and a dropped one must be retried."""
    r = subprocess.run(["herdr", "notification", "show", title, "--body", body, "--sound", sound],
                       capture_output=True, text=True, check=False)
    try:
        return r.returncode == 0 and json.loads(r.stdout)["result"]["shown"] is True
    except (ValueError, KeyError, TypeError):
        return False


def ntfy_sink(url: str):
    def send(title: str, body: str, sound: str) -> bool:
        request = urllib.request.Request(url, data=body.encode(), method="POST",
                                         headers={"Title": title, "Priority": "high" if sound == "request" else "default"})
        with urllib.request.urlopen(request, timeout=10):
            pass
        return True
    return send


def run_tab(events: list[dict]) -> str | None:
    """The Herdr tab the current run recorded at run-start (`runlog.py add run-start --tab ...`)."""
    run = runlog.latest(events)
    return run[0].get("tab") if run else None


def state_path(repo: pathlib.Path) -> pathlib.Path:
    return git_common_dir(repo) / "herd" / "attention-state.json"


def load_state(repo: pathlib.Path) -> dict:
    p = state_path(repo)
    return json.loads(p.read_text()) if p.exists() else {"sent": []}


def save_state(repo: pathlib.Path, state: dict) -> None:
    p = state_path(repo)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state))
    os.replace(tmp, p)


@contextlib.contextmanager
def single_watcher(repo: pathlib.Path):
    """Hold the repository's watcher lock for the watcher's lifetime; yield False if another holds it."""
    lock = git_common_dir(repo) / "herd" / "attention-watch.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "a") as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        yield True


def watch_once(repo: pathlib.Path, agents: list[dict] | None, now: datetime.datetime, *, sink, tab: str | None,
               extra=(), stall_after: float = STALL_MINUTES, overdue_after: float = OVERDUE_MINUTES) -> list[dict]:
    """Send every operator/info item not sent before; return what was sent. `sink` is primary: an item
    counts as sent only when it returns True. `extra` sinks are best effort."""
    state = load_state(repo)
    events = read_events(runlog.log_path(repo))
    items = diagnose(events, agents, now, tab=tab or run_tab(events), stall_after=stall_after,
                     overdue_after=overdue_after)
    sent = set(state["sent"])
    new = [i for i in items if i["audience"] != "lead" and i["key"] not in sent]
    prs = [i for i in new if i["kind"] == "pr-ready"]
    batches = [([i for i in prs], f"{len(prs)} PRs ready to merge", " ".join(i["title"].split()[1] for i in prs),
                "request")] if len(prs) > 1 else []
    batches += [([i], i["title"], i["body"], "request" if i["audience"] == "operator" else "none")
                for i in new if i["kind"] != "pr-ready" or len(prs) == 1]
    delivered = []
    for group, title, body, sound in batches:
        if sink(title, body, sound):
            delivered += group
            for s in extra:
                try:
                    s(title, body, sound)
                except Exception as exc:  # optional push never stops the watcher
                    print(f"ntfy failed: {exc}", file=sys.stderr)
    if delivered:
        save_state(repo, {"sent": sorted(sent | {i["key"] for i in delivered})})
    return delivered


def context_label(sample: dict | None, now: datetime.datetime) -> str:
    """`context 64% (3m ago)` from a #41 collector sample, else `context unknown`."""
    pct = (sample or {}).get("used_percentage")
    import context_collector
    if not context_collector.finite_number(pct):
        return "context unknown"
    age = int((now - datetime.datetime.fromisoformat(sample["ts"])).total_seconds() // 60)
    return f"context {round(sample['used_percentage'])}% ({age}m ago)"


def monitor(events: list[dict], agents: list[dict] | None, now: datetime.datetime, *, tab: str | None,
            stall_after: float = STALL_MINUTES, overdue_after: float = OVERDUE_MINUTES,
            context: dict | None = None) -> list[str]:
    """The text monitor: every agent, every issue of the latest run, what the lead owes, what needs the operator.
    Data no producer supplies yet (binding provenance until #38) is shown as unknown, never guessed."""
    run = runlog.latest(events)
    roles = {e["agent"]: e["role"] for e in run if e["kind"] == "session"}
    worktrees = {e.get("issue"): e["worktree"] for e in run if e["kind"] == "worktree-created"}
    lines = [f"observed {now.isoformat(timespec='seconds')} · run tab {tab or 'unknown'}", "AGENTS"]
    if agents is None:
        lines.append("  unavailable: herdr agent list failed")
    for a in agents or []:
        who = a.get("name") or a["pane_id"]
        where = "  (run tab unknown)" if not tab else "" if a.get("tab_id") == tab else "  (outside run)"
        role = roles.get(a.get("name"))
        lines.append(f"  {who:<22} {a['pane_id']:<8} {a.get('agent', '?'):<7} {a.get('agent_status', 'unknown'):<8} "
                     f"role: {role or 'unknown'}{'' if role else ' (unassociated)'} · binding: unknown · "
                     f"{context_label((context or {}).get(a['pane_id']) if a.get('agent') == 'claude' else None, now)}{where}")
    lines.append("ISSUES")
    for issue, e in latest_progress(run).items():
        wait = f" [waiting: {e.get('reason')}]" if e["kind"] == "wait" else ""
        where = f" · {worktrees[issue]}" if issue in worktrees else ""
        lines.append(f"  #{issue} {runlog.describe(e)}{wait} ({int(age_minutes(e, now))}m ago){where}")
    items = diagnose(events, agents, now, tab=tab, stall_after=stall_after, overdue_after=overdue_after)
    lines.append("LEAD")
    lines += [f"  {i['title']}: {i['body']}" for i in items if i["audience"] == "lead"] or ["  nothing"]
    lines.append("NEEDS YOU")
    lines += [f"  {i['title']}: {i['body']}" for i in items if i["audience"] == "operator"] or ["  nothing"]
    return lines


def herdr_agents() -> list[dict] | None:
    """Every agent Herdr sees, or None when the observation failed."""
    r = subprocess.run(["herdr", "agent", "list"], capture_output=True, text=True, check=False)
    if r.returncode:
        print(f"herdr agent list failed: {r.stderr.strip()}", file=sys.stderr)
        return None
    try:
        return json.loads(r.stdout)["result"]["agents"]
    except (ValueError, KeyError):
        return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("scan", "watch", "monitor"))
    ap.add_argument("--repo", default=".")
    ap.add_argument("--tab", default=None, help="override the run's Herdr tab (default: the tab the current "
                                                  "run recorded at run-start, re-read on every poll)")
    ap.add_argument("--interval", type=float, default=30)
    ap.add_argument("--stall", type=float, default=STALL_MINUTES)
    ap.add_argument("--overdue", type=float, default=OVERDUE_MINUTES)
    ap.add_argument("--ntfy")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    repo = pathlib.Path(a.repo)
    if a.cmd == "watch":
        with single_watcher(repo) as mine:
            if not mine:
                print("a watcher is already running for this repository")
                return 0
            while True:
                now = datetime.datetime.now(datetime.timezone.utc)
                for i in watch_once(repo, herdr_agents(), now, sink=herdr_sink, tab=a.tab,
                                    extra=[ntfy_sink(a.ntfy)] if a.ntfy else [], stall_after=a.stall,
                                    overdue_after=a.overdue):
                    print(f"{now.isoformat(timespec='seconds')} sent {i['kind']}: {i['title']}", flush=True)
                if a.once:
                    return 0
                time.sleep(a.interval)
    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        events = read_events(runlog.log_path(repo))
        tab = a.tab or run_tab(events)
        if a.cmd == "scan":
            items = diagnose(events, herdr_agents(), now, tab=tab, stall_after=a.stall, overdue_after=a.overdue)
            print(json.dumps(items, indent=2) if a.json else
                  "\n".join(f"{i['audience']:<8} {i['kind']:<10} {i['title']}: {i['body']}" for i in items))
            return 0
        print("" if a.once else "\033[2J\033[H", end="")
        import context_collector
        print("\n".join(monitor(events, herdr_agents(), now, tab=tab, stall_after=a.stall,
                                overdue_after=a.overdue, context=context_collector.samples())))
        if a.once:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **I4** `skill/SKILL.md` — the monitor names the collector

Find this exact text (it occurs exactly once):

```python
both read the current run's tab from its `run-start` (#33, #34).
```

Replace it with exactly:

```python
both read the current run's tab from its `run-start` (#33, #34). Each Claude Code pane's
context use shows in the monitor once `python3 <herd>/tools/context_collector.py
install` has wrapped the status line (it backs up `settings.json` first, and
`uninstall` restores it); other harnesses show `context unknown` (#41).
```

## 3. Gates

- Full suite at the base (`feat/39-setup` after its build): `435 passed`. After: `461 passed` (25 in `tests/test_context_collector.py`, 1 new skill-text test). ~8 s.
- `ruff check tools tests` → `All checks passed!`; `openspec validate context` valid.
- Live (lead-owned): the real `~/.claude/statusline-command.sh` output through the collector is byte-identical to running it directly, stdout and stderr (checked in pre-execution after round 1, 778 bytes); after the PR the lead runs `context_collector.py install` once (operator decision) and confirms the status line still renders and a sample appears for the lead's pane.

## 4. Mutations

Drive with `python3 tools/mutate.py openspec/changes/context/tasks.md <tree>`; every one KILLED.

- [ ] **M1** in `tools/context_collector.py`: replace

```python
    if not pane or len(stdin) > MAX_INPUT:
```

with

```python
    if len(stdin) > MAX_INPUT:
```

Killer: `tests/test_context_collector.py::test_outside_herdr_nothing_is_recorded`

- [ ] **M2** in `tools/context_collector.py`: replace

```python
    except Exception:  # the status line must never break because of the collector
        return
```

with

```python
    except OSError:
        return
```

Killer: `tests/test_context_collector.py::test_bad_or_oversized_input_is_not_recorded`

- [ ] **M3** in `tools/context_collector.py`: replace

```python
    record(stdin, now)
    return code
```

with

```python
    record(stdin, now)
    return 0
```

Killer: `tests/test_context_collector.py::test_stdout_stderr_and_exit_code_pass_through_the_shell`

- [ ] **M4** in `tools/context_collector.py`: replace

```python
subprocess.run(command, shell=True, input=stdin, check=False)
```

with

```python
subprocess.run(command, shell=True, input=b"", check=False)
```

Killer: `tests/test_context_collector.py::test_stdout_stderr_and_exit_code_pass_through_the_shell`

- [ ] **M5** in `tools/context_collector.py`: replace

```python
    if command == installed_command(collector, meta):
        print("already wrapped")
        return 0
```

with

```python

```

Killer: `tests/test_context_collector.py::test_install_twice_neither_rewraps_nor_overwrites_a_backup`

- [ ] **M6** in `tools/context_collector.py`: replace

```python
    while target.exists() or target.is_symlink():
```

with

```python
    while False:
```

Killer: `tests/test_context_collector.py::test_install_twice_neither_rewraps_nor_overwrites_a_backup`

- [ ] **M17** in `tools/context_collector.py`: replace

```python
    while target.exists() or target.is_symlink():
```

with

```python
    while target.exists():
```

Killer: `tests/test_context_collector.py::test_a_dangling_symlink_at_the_backup_name_is_taken_not_written_through`

- [ ] **M7** in `tools/context_collector.py`: replace

```python
    if not saved or command != saved["installed"]:
```

with

```python
    if not saved:
```

Killer: `tests/test_context_collector.py::test_uninstall_restores_exactly_and_only_its_own_install`

- [ ] **M8** in `tools/attention.py`: replace

```python
if a.get('agent') == 'claude' else None
```

with

```python
if True else None
```

Killer: `tests/test_context_collector.py::test_the_monitor_shows_context_only_for_claude_panes_and_skips_bad_samples`

- [ ] **M9** in `tools/context_collector.py`: replace

```python
                continue
            out[s["pane"]] = s
```

with

```python
                pass
            out[s["pane"]] = s
```

Killer: `tests/test_context_collector.py::test_the_monitor_shows_context_only_for_claude_panes_and_skips_bad_samples`

- [ ] **M10** in `tools/context_collector.py`: replace

```python
    if not pane or len(stdin) > MAX_INPUT:
```

with

```python
    if not pane:
```

Killer: `tests/test_context_collector.py::test_bad_or_oversized_input_is_not_recorded`

- [ ] **M11** in `tools/context_collector.py`: replace

```python
        if not finite_number(pct):
            pct = None
```

with

```python

```

Killer: `tests/test_context_collector.py::test_a_missing_or_non_numeric_percentage_is_recorded_as_unknown`

- [ ] **M15** in `tools/context_collector.py`: replace

```python
    except OverflowError:
        return False
```

with

```python
    except ValueError:
        return False
```

Killer: `tests/test_context_collector.py::test_a_huge_integer_sample_is_skipped_not_crashed_on`

- [ ] **M16** in `tools/context_collector.py`: replace

```python
    path = path.resolve() if path.is_symlink() else path
```

with

```python

```

Killer: `tests/test_context_collector.py::test_a_symlinked_settings_file_stays_a_symlink`

- [ ] **M13** in `tools/context_collector.py`: replace

```python
        code = code if code >= 0 else 128 - code  # killed by a signal: report it as a shell would
```

with

```python

```

Killer: `tests/test_context_collector.py::test_a_signal_death_is_reported_as_a_shell_would`

- [ ] **M14** in `tools/context_collector.py`: replace

```python
    return home / f"statusline-{hashlib.sha1(str(settings.resolve()).encode()).hexdigest()[:10]}.json"
```

with

```python
    return home / "statusline.json"
```

Killer: `tests/test_context_collector.py::test_installs_into_two_settings_files_stay_independent`

- [ ] **M12** in `tools/context_collector.py`: replace

```python
    code = 0
    if command:
```

with

```python
    record(stdin, now)
    code = 0
    if command:
```

Killer: `tests/test_context_collector.py::test_the_sample_is_recorded_by_pane_after_the_command_runs`
