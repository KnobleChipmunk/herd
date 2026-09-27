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
