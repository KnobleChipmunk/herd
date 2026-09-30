# Proposal: briefing's out-of-sandbox escalation line is missing or misread by the Codex builder

Status: applied https://github.com/KnobleChipmunk/herd/pull/72 2026-09-30

## Class

briefing-escalation-misread — briefing's out-of-sandbox escalation line is missing or misread by the Codex builder

Events (friction ledger):
- 2026-09-29 project-mera #482 (windows): "codex_build ran the first full-suite pass inside the sandbox because the briefing's single escalation sentence was misread; it hit the 900s timeout at ~24% on an idle machine, costing ~15 min before the escalated re-run."
- 2026-09-29 project-mera #482 (windows): "Lead: the briefing told the Codex builder nothing about sandbox escalation (pi has no sandbox), so the lead added the escalation note to the dispatch prompt by hand; mkbrief should emit it when the builder is Codex."

## Proposed change

Both events share one root: the briefing does not tell a Codex builder which
commands must run outside the sandbox, so the builder runs the full suite in
the sandbox, times out at ~24%, and wastes ~15 min before an escalated
re-run. The lead had to add the note to the dispatch prompt by hand because
`mkbrief.py` emits nothing for a Codex builder (the pi builder has no
sandbox, so the note was never templated).

Change `tools/mkbrief.py`: when the builder pane is a Codex
harness (not pi), emit the escalation note as a bullet list, one command
class per line, with "OUTSIDE the sandbox" repeated on each line — the full
pytest suite, the tasks.md refresh command, every `mutate.py` drive, every
`dispatch.py` call, and every `herdr agent prompt`. A single prose sentence
was the form that got misread; the per-line repetition is what a builder
reliably follows. Also emit the network-escalation line when tasks.md carries
a fetching step (the #482 data step needed it too).

## Prediction

No `briefing-escalation-misread` events in the next run's friction lines; a
Codex builder runs the full suite outside the sandbox on the first attempt,
the ~15-min sandbox timeout does not recur, and the lead no longer adds the
escalation note to the dispatch prompt by hand.
