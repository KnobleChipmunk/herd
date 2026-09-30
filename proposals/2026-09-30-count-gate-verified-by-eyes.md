# Proposal: pytest COUNT gates are verified by reading saved tails, not by a tool match line

Status: in-pr https://github.com/KnobleChipmunk/herd/pull/74

## Class

count-gate-verified-by-eyes — pytest COUNT gates are verified by reading saved tails, not by a tool match line

Events (friction ledger):
- 2026-09-29 project-mera #333 (windows): "pi_build: the briefing says compare by COUNTS with gates.py match, but each pytest count was saved to a SCRATCH file and verified by reading it, so the handoff's 'every count backed by a tool result' claim rests on the builder's eyes, not a tool line."
- 2026-09-29 project-mera #482 (windows): "codex_build eyeballed the per-file and full-suite pytest count lines and only ran gates.py match for the grep gates, so the handoff's count gates rest on the builder's eyes, not a tool MATCH line."

## Proposed change

Two runs, two different builders (pi and Codex), the same gap: the pytest
count gates are verified by reading a saved tail, so a count mismatch can
slip through formatting differences (e.g. the extra "1 warning" clause in a
full-suite tail). The handoff template's "every grep gate's output" phrasing
is what scopes the tool match to grep gates only.

Change `tools/mkbrief.py` so the handoff template it renders
says "every gate's `gates.py match` MATCH line" instead of "every grep
gate's output", requiring the builder to run `gates.py match` for the pytest
count gates too and paste the MATCH line, not the raw tail. The template
change lives in mkbrief.py because that is where the handoff text is
generated; no separate skill paragraph is needed.

## Prediction

No `count-gate-verified-by-eyes` events in the next run's friction lines;
the handoff's pytest count gates carry `gates.py match` MATCH lines, and a
count mismatch is caught by a tool line before the reviewer reads the file.
