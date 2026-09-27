# OpenRig → herd: consensus (Claude Opus 5.5 + Codex GPT-6 Astra), 2026-09-27

Confidence: 5 = would bet on it; ≤2 = do not build yet. Both agents agreed every rating (see rounds/).

| # | Implementation | Conf. |
|---|---|---|
| 0 | Reconcile DEVLOOP vs herd contracts (Gate A vs plan-review authorization; 3 vs 2+1 review cap). Enforce one active run per repo: atomic check+append at run-start, explicit resume/close after crash, unique run ids, unresolved decisions visible across runs | 5 |
| 2 | Attention watcher: run-log + `herdr agent list` → `herdr notification show` (ntfy optional second sink). Operator triggers: decision-needed, permission `blocked`, pr-opened (batched). Worker BLOCKED → "lead intervention overdue" only. Dedup by (repo, log generation, byte offset); blocked panes tracked as episodes; "clear" = monitor state (Herdr has no clear command); one open decision per issue enforced at record time | 4 |
| 1a | Text monitor pane: agent × issue × workflow stage × Herdr state × open decisions, with observation age and artifact links; workflow stage kept separate from pane activity | 5 |
| 1b | Context % column via status-line scraping ("unknown" when absent) | 2 |
| 5 | Per-ticket folder at `<git common dir>/herd/<run>/<issue>/` with generated PROGRESS.md; existing HANDOFF/REVIEW/RETRO moved there; survives worktree cleanup | 5 |
| 6a | Run manifest: ordered issues, owner, dependencies, parked state | 4 |
| 6b | Durable agent-to-agent delivery queue with acknowledgments | 2 |
| 3 | Shared sentinel/evidence contract + short role cards; briefings generated from them | 4 |
| 4 | Validated `herd.yaml` roster (role, harness, model/options, fallback order, card ref); launch commands generated; live pane/session ids stay in the run record | 4 |
| 7a | Keep the herd lead as the single orchestrator | 5 |
| 7b | Delegate pre-execution to the slot-3 pane | 2 |
| X | Tool-enforced transitions: dispatch needs approved spec/evidence, review names its candidate, round cap triggers escalation | 5 |
| H | Keep herd's lifecycle ownership (4); adopt OpenRig (2). OpenRig's `--provider herdr` is display only; coexistence means picking ONE controller | 4 / 2 |
| W | Watchdog that reports stale/unresolved obligations; no automatic keep-awake prompts | 4 |

Order: 0 → 2 + 1a → 5 + 6a → 3 + 4 → X → W. Defer 1b, 6b, 7b until an observed need.
