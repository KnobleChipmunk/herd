# Round 9 — portability across systems (new request from the operator)

The operator's request, verbatim:

> Last item. I want this update to the process to be durable across systems.
> Not all configs will use Claude and Codex combined with local model support.
> Some systems may only use one or the other, or different combinations of
> agent types/logins. There should be a configuration mode which either the
> user can specify or that can auto detect agentic systems on the device. If
> a user only runs Claude on their system this should be accounted for by
> prompting the user to set different model types based on role. Similarly
> the user should be encouraged to use different models based on model
> specialty per role, favoring a mixture of models where possible. Discuss
> this with codex please.

## Sources — read them yourself

- Our v3 consensus: `/mnt/c/Users/Tusk/Desktop/openrig-herd-consensus/CONSENSUS.md`
  (roles ≠ seats; herd.yaml defines roles, bindings resolve them — row 4, TD).
- Herd today: `/home/tusk/.claude/skills/herd/SKILL.md` (Roster table, "why the
  two reviewers differ", "the fallback is never Opus: an Opus reviewer checking
  an Opus lead is the same model checking itself", HERDR_ENV requirement),
  `/home/tusk/projects/herd/tools/probe.py` (probes each model in a role's
  fallback chain with a one-line prompt; harnesses hardcoded: Codex, Claude
  Code, pi), `/home/tusk/projects/herd/tools/preflight.py` (credentials: set or
  missing, never values).
- OpenRig's detection: `../openrig-src/packages/daemon/src/domain/kernel-boot.ts`
  (lines ~100-175: `claude auth status` / `codex login status` → selectVariant →
  rig.yaml / rig-claude-only.yaml / rig-codex-only.yaml), and
  `../openrig-src/packages/daemon/specs/rigs/launch/kernel/rig-claude-only.yaml`
  vs `rig.yaml`. Also `rig doctor` in `../openrig-src/docs/as-built/cli-reference.md:396`.
- This machine (context, not a requirement for others): Claude Code, Codex,
  pi on local Ollama and a llama.cpp/llama-swap server on :8080, opencode,
  Hermes. Herdr is the multiplexer.

## What to do

PART 1 — before opening CLAUDE-round-9.md, write your own independent design:
detection (what to detect, how, what counts as "available"), the configuration
mode (user-specified vs auto-detect, interactive prompts), the single-harness
case (e.g. Claude-only), how "model specialty per role" and "favor a mixture"
become recommendations without hardcoding unverified claims, where config
lives (portable vs machine-local), and anything that breaks portability that
the operator did not name. Rate each proposed implementation 1–5.

PART 2 — read CLAUDE-round-9.md, give AGREE / COUNTER per row with reason,
and say what this changes in v3 rows (esp. 4, TD, P, H, and the order).

Write both parts to `CODEX-round-9.md`, end with `CONSENSUS: yes` or
`CONSENSUS: no — <rows>`, reply with only the path.
