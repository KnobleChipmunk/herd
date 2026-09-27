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

**Every append takes the lock (plan review #32 round 1, finding 1).**
`fcntl.flock` on `<git common dir>/herd/run-log.lock` is held by every append,
from reading the log (to find the run) through writing the line. Locking only
`run-start` and `close` leaves a race: an ordinary append that read run A, then
paused while `close` and B's `run-start` landed, would write A's event after
B's start, and a positional open-run check would then see B as ended. `close`
writes through an internal helper while it already holds the lock, because a
second `flock` from a separate `open()` in the same process blocks, so a nested
call would deadlock. The lock file is never unlinked. Reads go through
`runlog.read_file`. `fcntl` is POSIX.
herd requires Herdr, which runs on Linux and macOS, so this adds no new
platform limit. Cost: one extra `open` + `flock` per append, on a log that
gets a few hundred lines per run.

**The lock is tested directly, not by racing threads (plan review round 2,
finding 2).** A thread-and-sleep race test passes or fails on scheduling, and
it passed against the very implementation it was meant to reject (one that
locks only `run-start` and `close`). The test instead wraps `locked`,
`read_file` and `_write`, and at each read and write it probes the lock
from a second open file description with `LOCK_NB`. It then requires exactly
enter → read (held) → write (held) → exit for an ordinary append, `run-end`,
`run-start` and `close`. So `append` and `close` call those three through the
module, and each reads the log once.

**The lock gives up after `LOCK_TIMEOUT` = 30 s (plan review round 2, finding
4).** `locked` computes `deadline = _monotonic() + LOCK_TIMEOUT` once, then
tries `LOCK_NB`. On `BlockingIOError` it checks `_monotonic()` against the
deadline and otherwise sleeps `LOCK_POLL` (10 ms) through `_sleep`. When the
deadline passes, it raises `TimeoutError`, which `append` and `close` turn into
the refusal `run log is locked: <lock path>` (exit 2 on the CLI). A holder
stuck for 30 s on a millisecond operation is a fault; brief contention is
waited out. `_monotonic`/`_sleep` are module seams (`time.monotonic`,
`time.sleep`), and `LOCK_TIMEOUT`/`LOCK_POLL` are read at call time, so tests
drive retry and expiry on a controlled clock.

**The timeout bounds correct code; the tests bound regressions (plan review
round 3, finding 1).** A regression to blocking `LOCK_EX`, or a deadline reset
on every retry, would defeat the production timeout, so the tests do not rely
on it. An autouse fixture in `tests/test_runlog.py` arms a 60 s `SIGALRM` per
test, whose handler raises into the main thread, even through a blocked
`flock`. The eight-thread start test uses daemon threads with a 45 s join and
asserts none is alive, so a hung worker fails the test without blocking
interpreter exit. The expiry test's fake sleep fails after 100 polls, so a
deadline that never arrives fails instead of spinning. The alarm uses
`SIGALRM`, which is POSIX-only, matching `fcntl`.

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
