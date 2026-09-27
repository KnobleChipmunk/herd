# Claude — round 9 (portability)

Grounded facts: OpenRig detects by login status only (kernel-boot.ts:139-173)
and swaps in a precomputed variant; no user prompt, no diversity guidance.
Herd's probe.py verifies availability of NAMED models, not what is installed.
Herd hard-requires Herdr (SKILL.md: `test "${HERDR_ENV:-}" = 1` or stop).

## Proposals

| # | Implementation | Conf. |
|---|---|---|
| M1 | Split config by portability: role catalog (roles, contracts, independence rules) is portable and ships with herd; **bindings** (role → harness + model + effort) are machine-local (`~/.config/herd/bindings.yaml`, never committed). Directly extends v3 "roles ≠ seats" | 5 |
| M2 | `herd setup` with two modes. **detect**: harness binaries on PATH (claude, codex, pi, opencode, …), login status via each harness's own status command, local model servers (Ollama API, OpenAI-compatible endpoints), multiplexer (Herdr/tmux); then proposes bindings. **manual**: user writes/edits bindings. Detect never writes silently; it shows the proposal and the user confirms or edits each role | 5 |
| M3 | Three separate checks, never conflated: *installed* (binary/endpoint exists) → *authenticated* (status command) → *usable* (probe.py's one-line prompt per chosen model). Setup does the first two plus a probe; every run still probes (the sweep), because logins and limits change | 5 |
| M4 | Independence ladder, computed per author/evaluator pair and shown at setup and in the run log: (a) different vendor, (b) same vendor different model, (c) same model different effort + fresh context, (d) same model same context. Setup warns below (b) for plan review, build review, QA; (d) is refused for evaluator roles. Generalises herd's "never Opus reviewing Opus" rule | 4 |
| M5 | Single-harness case (e.g. Claude-only): setup prompts per role with a proposed spread across that vendor's tiers (e.g. lead Opus, reviewers Fable, builder Sonnet), explains the independence level each choice gives, and accepts the user's answer. Same flow for Codex-only or local-only | 5 |
| M6 | "Model specialty" as a **recommendations file**, not code: per role, a ranked list of model families with a one-line reason, a source, and a date (e.g. "review: Codex family — operator experience, herd #321/#330"; the video's hemisphere claim marked anecdotal). Setup reads it to rank proposals; the user can edit it; stale entries (older than N months) are flagged. Mixing is the default recommendation, never forced | 4 |
| M7 | Portability of the seat layer: herd requires Herdr today. Other systems may have tmux only or neither. Define the minimum seat interface herd uses (start, prompt, read, wait, state) and implement Herdr first; tmux adapter and a degraded "in-session subagents" mode later. Flag this to the operator as the largest unnamed portability break | 3 |
| M8 | Portable tool assumptions: harness list in probe.py/preflight.py driven by the bindings file + a small per-harness adapter table (probe command, status command, launch command), not hardcoded branches | 4 |

Changes to v3: row 4 splits into catalog (portable) + bindings (M1); TD
includes the independence ladder (M4); P adds "OpenRig's variant selection vs
herd setup"; H unchanged. Order: M1 + M3 + M8 fold into step 4's work; M2/M5
setup comes right after TD; M7 after P.
