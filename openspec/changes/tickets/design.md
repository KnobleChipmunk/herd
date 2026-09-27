# Design — tickets

**Event-sourced, append-only for committed records.** A ticket's state is
folded from its events, the same shape as the run log, so history and the page
come free. Committed lines are never changed; the only rewrite drops an
interrupted last line (see Durable records), and a crash can lose only the
write in flight.

**Lead ruling (plan review round 4).** Durability of `<git common dir>/herd`
itself is out of scope: the run log creates that directory at `run-start`
and owns its guarantees; the ticket store syncs its own file and directory
entries only.

**One lock for both stores.** The store lives beside the run log, so
`runlog.locked` serializes ticket writes and run-log writes with one lock and
one timeout; no second lock to reason about.

**Ids by count.** `T<n>` where n counts `create` and `handoff` records (a
handoff creates the successor), allocated inside the lock. Short ids are easy for agents and humans to type.

**The page is generated, never edited.** Status comes only from records; an
agent cannot claim PASS by writing prose.

**Durable records.** A line counts only with its newline. An interrupted last
line is ignored when read and dropped before the next write by writing the
complete lines to a temporary file (looping over short writes), syncing it,
renaming it over the store and syncing the directory; appends loop over short
writes and sync before success; a newly created store also syncs its directory.

## Rejected

- SQLite (OpenRig's choice): a second storage format and a dependency on
  migrations, for a store with a few hundred lines per run.
- GitHub issues as tickets: too heavy for internal review tasks; a GitHub issue
  stays the optional parent (roadmap row 6a).
