# Design — run recovery and loop scope

## Decisions

**Refuse, don't auto-close.** A second `run-start` while a run is open is refused
(exit 2), never silently closes the old run. An open run after a crash is state
the lead must see. Silently closing it would hide the crash from `status`
and the librarian.

**`close` is a subcommand, not a `run-start` flag.** Ending a crashed run is its
own recorded act with a reason (`run-end`, text `closed: <reason>`), so the
ledger can tell a clean finish from a crash close. Refused (exit 2) when no run
is open.

**Resume needs no command.** The run stays open, and the lead keeps appending.
`status` already shows it. Adding a `resume` verb would record nothing new.

**Events after `run-end` belong to the ended run.** merge_stack appends its
librarian note after `run-end` (`tools/merge_stack.py:189`). Binding stays
"latest `run-start`", unchanged. "Open" means only "no `run-end` after the latest
`run-start`", and it gates only `run-start` and `close`.

**Lock file, not a lock on the log.** `fcntl.flock` on
`<git common dir>/herd/run-log.lock`, held while `run-start` or `close` reads the
log and appends. Ordinary appends keep today's lock-free `O_APPEND` path. They
never read-then-decide on open/closed state. `fcntl` is POSIX. herd requires
Herdr, which runs on Linux and macOS, so this adds no new platform limit.

**Unique ids without a new format.** `run-start` uses microsecond timestamps,
and `run` still equals that event's `ts`, so `librarian.py` and the existing
test invariant hold. If the id already exists in the log (clock set back, or
a fixed clock in tests), append `+2`, `+3`, … . A `now()` seam in `runlog.py`
makes this testable.

**Cross-run decisions, not cross-run blocks.** `status` gets all events for the
OPEN-decision scan and the latest run for everything else. A decision from an
earlier run prints as `OPEN decision #426: <text> (from run <id>)`.

**`session` is a new kind with validated fields.** `--role` and `--outcome` are
new FIELDS. `--outcome` uses argparse `choices`. REQUIRED: agent, role,
outcome. It is a side channel, like `friction`, so it is not a PROGRESS kind.

**Scope lines, one per file.** Operator ruling on #32: scope the two loops, do
not merge them. The skill's line sits directly under its H1, so every run reads
it. DEVLOOP's line sits under its intro paragraph.

## Rejected

- An automatic stale-run timeout: a timeout guesses at a crash, and we
  decided the lead must see an open run and close it on purpose.
- A UUID run id: this would break `run == ts`, which the librarian's run
  header and one existing test rely on, and it gains nothing over the suffix.
- Carrying open blocks across runs: see Non-goals in proposal.md.
