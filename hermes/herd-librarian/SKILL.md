---
name: herd-librarian
description: File a finished herd run into the vault ledgers.
version: 0.1.0
author: KnobleChipmunk, Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [herd, post-mortem, ledger, friction]
    related_skills: []
---

# Herd librarian

`merge_stack.py --apply` starts this in the background once a herd run's
PRs are merged and the workspace is clean; the operator can also start it
by hand. You turn the run log into ledger rows and friction
lines in the vault, and draft proposals when a friction class recurs. You
write records and proposals. You never change code, the herd skill, or git.

`<herd>` below is the herd checkout; the launch prompt names it, and its
tools live in `<herd>/tools`. The repo is the one the herd ran in, also named
in the prompt; pass it as `--repo`. The vault is `$HERD_VAULT` (the tools
default to `~/.local/share/herd` when it is unset). Every number you report
comes from a tool's output, never from your own counting.

## 1. Check the run is finished

    python3 <herd>/tools/librarian.py report --repo <repo>

- If any issue shows `outcome=open`, stop and tell the operator to run
  `python3 <herd>/tools/merge_stack.py --repo <repo>` first.
- The first line is the run and its description. If it says
  "reconstructed", the log has no review counts: step 2 will add no rows
  for it, and your report says so.

## 2. Ledger rows

    python3 <herd>/tools/librarian.py append-ledger --repo <repo>

It prints how many rows it added, and how many it skipped for having no
review counts. Rows already in the ledger are skipped, so running it twice
is safe.

## 3. Friction

    python3 <herd>/tools/librarian.py friction --repo <repo>

This lists the run's friction lines, its issue retro files (`retro`), and
retro files not tied to an issue (`retro?`, with their date). Include a
`retro?` file only if its date falls in the run. Read the classes already in
`$HERD_VAULT/knowledge/friction-ledger.md` (its `## `
headings).

Take each friction line, and each numbered item in each retro file, one at a
time:

- **It is a problem that cost time** and matches an existing class: file it
  under that class.
- **It is a problem that matches no class:** file it under a new class with a
  short kebab-case slug and a one-line title.
- **It is not a problem** (praise, "keep this", a question): skip it.

File each one with:

    python3 <herd>/tools/librarian.py friction-append --repo <repo> --class <slug> [--title "<title>"] --issue <id> --date <YYYY-MM-DD> --text "<one sentence: what happened and what it cost>"

`--date` is the day it happened: the issue's date in its ledger row, or the
retro file's date. Never today's date for an older run.

Two agents reporting the same problem are two events: file both. The tool
prints the class's event count.

## 4. Proposals

First, `python3 <herd>/tools/proposals.py sync`: it marks a
proposal applied once the PR that carries it has merged.

When `friction-append` prints `GRADUATES`, write
`<herd>/proposals/<date>-<slug>.md` with:

0. The title line, a blank line, then `Status: open`.
1. **Class** and the event lines, quoted from the ledger.
2. **Proposed change.** Prefer a change to a tool in `<herd>/tools`
   over a new paragraph in the skill: a problem that recurred after one
   wording fix belongs in code.
3. **RELAXATION** as the first line, if the change loosens a gate, widens
   what an agent may edit, or skips a check.
4. **Prediction**: what the next run's ledger or friction lines should show if
   the change works, e.g. "no reviewer-wrong-cwd events".

Grade only what landed: `python3 <herd>/tools/proposals.py list
--status applied` lists each applied proposal with its merge date. For each
one merged before this run, append one line: `<date>: held` or `<date>:
missed — <evidence>`. Never grade an `open`, `accepted` or `in-pr` proposal:
nothing changed, so a quiet run is not evidence. A class that recurs while
its proposal is still pending gets its new events in the ledger, not a
grade.

## 5. Close

    python3 <herd>/tools/runlog.py add note --repo <repo> --text "librarian: <rows> ledger rows, <n> friction lines, <m> proposals"

Tell the operator: the `OPEN` lines from step 1, rows added, friction lines
filed per class, classes that graduated, and the proposal paths.

## Never

- `git commit`, `git push`, `gh pr merge`, or any other git write.
- `merge_stack.py --apply`, removing a worktree, or deleting a branch.
- Editing the herd `SKILL.md`, anything in `<herd>/tools`, or a
  briefing. Proposals are files the operator reads.
- Writing run state or standing decisions to your memory. Your memory is
  nearly full, and standing decisions live in the herd skill's Roster.
- Running during a herd run. A local builder may share your GPU.
