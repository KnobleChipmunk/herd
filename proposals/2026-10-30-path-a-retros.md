# Proposal: fold the PR #113 Path A herd retrospectives

Status: accepted

## Class

path-a-retros — a stacked, Spark-backed build in Claude panes outside the
loop's assumptions (pinned drive env, bare python3, /tmp caches, shared
shell panes, local full suite, builder-authored merges)

Events (retrospectives, 2026-10-29, `regrid-data-platform-poc/pr113-rework/reports/`):
- RETRO-path-a-lead.md 1: "`herdtool.py` `mutate_env` builds a minimal environment and drops `AWS_DEFAULT_REGION` ... Every drive would read NOT RUN."
- RETRO-path-a-lead.md 2: "`mkbrief.py` writes `python3 <herd tool>` commands, and a Claude pane's venv hook blocks bare `python3`."
- RETRO-path-a-lead.md 7: "a shell pane blocked by a long local Spark run held up a helper's later commands for over an hour."
- RETRO-path-a-claude_build_117.md 1: "It cost one full review round of the two-round cap."
- RETRO-path-a-opus_117_b.md 1: "One queued script (`logs/b-s4.sh`) would have mutated `bronze_to_silver0.py` whenever the pane freed up."

## Proposed change

Tools: `.herd-mutate-env` for per-repo drive variables; `lang_of` maps
`.json`, `.md`, `.yaml`; `mutate.py` ends with a count line; `mkbrief.py`
takes `--herd-python` and `--cache-dir`, puts the handoff before round 1,
shows the RED/GREEN redirects and lists untracked files. Skill and cards:
offloaded gates, agent start without `--cwd`, one shell pane per long
command, the merge commit in a stack, helper briefs, RED/GREEN as separate
commands, the no-fence review, adversarial value classes.

Approved by the operator 2026-10-30 ("Retros for herd approved"). Folded on
`chore/path-a-retros-fold`; the fold report lists each point.

## Prediction

The next stacked or offloaded run needs no hand patch to a generated
briefing, no `HERD_PYTHON` wrapper for drive env, and no review round spent
on a missing handoff.
