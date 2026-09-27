# Design — tickets

**Event-sourced, append-only.** A ticket's state is folded from its events, the
same shape as the run log: nothing is rewritten, so history and the page come
free, and a crash can only lose the write in flight.

**One lock for both stores.** The store lives beside the run log, so
`runlog.locked` serializes ticket writes and run-log writes with one lock and
one timeout; no second lock to reason about.

**Ids by count.** `T<n>` where n counts `create` and `handoff` records (a
handoff creates the successor), allocated inside the lock. Short ids are easy for agents and humans to type.

**The page is generated, never edited.** Status comes only from records; an
agent cannot claim PASS by writing prose.

**Durable records.** A line counts only with its newline. An interrupted last
line is ignored when read and dropped before the next write by writing the
complete lines to a temporary file, syncing it, renaming it over the store and
syncing the directory; appends loop over short writes and sync before success.

## Rejected

- SQLite (OpenRig's choice): a second storage format and a dependency on
  migrations, for a store with a few hundred lines per run.
- GitHub issues as tickets: too heavy for internal review tasks; a GitHub issue
  stays the optional parent (roadmap row 6a).
