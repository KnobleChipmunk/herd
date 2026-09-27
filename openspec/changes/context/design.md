# Design — context collector

**Wrap, never replace.** The operator keeps their status line; the collector
sits in front of it and is invisible when it fails.

**Keyed by pane, not session.** Herdr panes are what the monitor lists;
`HERDR_PANE_ID` is inherited by the status-line child, so no mapping from
session ids to panes is needed.

**Installed outside the repo.** The setting points at a copy in
`~/.local/share/herd/`, so merging, rebasing or removing a worktree never
breaks the status line.

**The original command is data, not text to splice.** It is stored verbatim
in a metadata file and run through the shell, so no quoting can change it,
and uninstall restores it only when the setting is still ours.

**Lead rulings (plan review round 1, in the run log).** F3 NARROWED: the
wrapped command runs first; recording follows, best effort. F7 REJECTED:
resolving the current pane through Herdr on every refresh costs a process
spawn per status line; after a cross-workspace pane move, context shows unknown.

## Rejected

- Reading context from Claude transcripts: heavier and not needed while the
  status line supplies it.
