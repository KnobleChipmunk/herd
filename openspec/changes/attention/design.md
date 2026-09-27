# Design — attention

**One module, three commands.** The watcher and the monitor must agree on what
needs a human (roadmap row 2: "shared rules with the watcher"), so both call
one pure `diagnose(events, agents, now, tab=...)`. Only the CLI touches Herdr,
the clock and the network.

**Run-level stalls.** The run log does not yet say which agent owes what, so
the stall rule is per run: work in flight and nobody working in the run's tab.
An agent in `unknown` or `blocked` state prevents a stall claim (unknown beats
a confident wrong answer; blocked already raises a permission alert). #36
tickets can refine this per agent later.

**Record ids from content.** Byte offset alone collides when a log is replaced
(an inode can be reused too). Offset plus 12 hex of the line's sha1 is unique
per record and stable across watcher restarts.

**The lead is not paged.** Worker blocks go to the lead (the monitor shows
them as overdue after 15 min); the operator hears only what needs a human.

**The watcher runs as the lead's background task**, not in a fifth pane: the
seat layout stays as the team design fixes it.

**Delivery means shown.** Herdr's `notification show` exits 0 even when it drops
a notification as rate-limited, so the watcher reads `result.shown`. Only a
shown item is recorded; a dropped one is retried on the next poll.

**Unknown beats a confident wrong answer.** A failed agent observation or an
unknown run tab disables the stall claim; decisions and PRs, which come from
the log alone, still alert.

## Rejected

- A pane per watcher: adds a seat for a script (team design §2: the watcher is
  not a role).
- Inode as log generation: reused inodes would suppress alerts.
