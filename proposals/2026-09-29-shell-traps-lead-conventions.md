# Proposal: lead shell conventions (zsh word-splitting, backgrounded herdr prompts) cost retries

Status: applied https://github.com/KnobleChipmunk/herd/pull/77 2026-09-30

## Class

shell-traps-lead-conventions — lead shell conventions (zsh word-splitting,
backgrounded herdr prompts) cost retries

Events (friction ledger):
- 2026-09-27 herd ##33 (windows): zsh does not word-split variables (, set -- ) and & on a herdr prompt gives no completion notification (run_in_background is needed); both cost time early in the run and belong in the skill's lead conventions.
- 2026-09-29 project-mera #333 (windows): Lead: zsh pitfalls hit twice — R='python3 …'; $R add … does not word-split in zsh (missing run-log entries, error text unobvious), and an unquoted heredoc containing backticks executed them.

## Proposed change

The same zsh traps recurred two runs later in two new forms (variable-expanded
command not word-split; unquoted heredoc executing embedded backticks). The
#33 event already proposed "belongs in the skill's lead conventions"; this
second occurrence makes it a standing rule.

Add to the skill's Pitfalls/lead conventions:
1. Call tools by full path on the command line — never store a command in a
   variable and expand it (`R="python3 …"; $R add …` does not word-split in
   zsh, and the resulting error does not point at the missing run-log entry).
2. Always quote heredocs: `<<'EOF'`, never `<<EOF` — an unquoted heredoc
   executes backticks and command substitutions in its body.
3. (carried from #33) Background a herdr prompt with the tool's background
   mode, not `&`, which gives no completion notification.

## Prediction

No `shell-traps-lead-conventions` events in the next run's friction lines;
lead transcripts show tools called by full path, quoted heredocs, and no
retries caused by zsh word-splitting or substitution.
