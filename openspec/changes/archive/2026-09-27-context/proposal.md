# Context % per Claude Code pane (#41)

## Why

Roadmap row 1b (3/5): show how full each Claude Code session's context is, so
the operator sees a lead near compaction, and so the later 7b decision
(delegating pre-execution) has measured lead context. Only harnesses that
publish it are covered; the rest stay `unknown`.

## What changes

- New `tools/context_collector.py`, which Claude Code runs as its `statusLine`
  command: it runs the saved original command first (same stdin, inherited
  stdout and stderr, its exit status), then records `{pane, session_id,
  used_percentage, ts}` under `$XDG_STATE_HOME/herd/context/<HERDR_PANE_ID>.json`.
  Errors never change the status line; outside Herdr nothing is recorded.
- `install` saves the original `statusLine.command` verbatim in
  `~/.local/share/herd/statusline-<hash of the settings path>.json`, copies the collector beside it, backs
  up `settings.json` under a new dated name (never overwriting one), and
  atomically sets the command to `python3 '<collector>' --meta '<json>'`. At
  each refresh the collector runs the saved command through the shell with the
  same stdin and inherited stdout and stderr, exits with its status (a signal
  death as 128 + the signal, as a shell reports it), and only then records (best effort; skipped over 1 MB); the sample is written after the
  status line has been produced. `uninstall` restores only when
  the setting is exactly the one install wrote. The monitor shows context only
  for Claude Code panes; invalid samples are skipped one by one (plan review
  round 1; pane moves ruled out of scope, see design.md).
- `attention.py monitor` shows `context NN% (Nm ago)` per pane, else
  `context unknown`.
- `skill/SKILL.md` Monitoring names the collector.

## Grounded facts

- Claude Code passes the status-line command JSON with
  `context_window.used_percentage`: the operator's existing script reads it
  (`~/.claude/statusline-command.sh:213`).
- `~/.claude/settings.json` has `statusLine: {type: command, command:
  /home/tusk/.claude/statusline-command.sh}` (read 2026-09-27).
- Live check (2026-09-27, after plan review round 1): the real script run
  through the saved-command flow gives byte-identical stdout and stderr to
  running it directly (778 bytes), and the sample is recorded afterwards.
- Herdr sets `HERDR_PANE_ID` in every pane's environment (herdr skill), which
  the status-line child inherits.
- Operator decision (sweep): wire it into `settings.json`, backing up first.

## Non-goals

- No context data for Codex or pi (no supported source); they show `unknown`.
- No alerting on high context yet.

## Impact

New `tools/context_collector.py`, `tests/test_context_collector.py`; edits to
`tools/attention.py`, `skill/SKILL.md`, `tests/test_skill_text.py`,
`pyproject.toml`. Stacked on `feat/39-setup`. After the PR is opened the lead
runs `install` once on this machine (operator decision).
