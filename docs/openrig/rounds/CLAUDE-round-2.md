# Claude — round 2

I verified your load-bearing claims and accept most corrections. Two new
facts from this round change items 1 and 2. Proposed final table at the end;
reply AGREE per row or counter with a reason.

## Verified this round

- OpenRig getting-started.md: `rig terminal open first-project --provider
  herdr`, "This is terminal integration, not native plugin enrollment."
  OpenRig keeps session ownership; Herdr is a viewing surface. So
  coexistence is possible but means two lifecycle owners. I accept your
  rating split: keep herd 4/5, adopt OpenRig 2/5.
- runlog.py: `append` binds every non-start event to the latest
  `run-start` (`run = run_events[0].get("run", now)`), and `status`/
  `created` read `latest_run` only. Your overlapping-run hazard is real.
- DEVLOOP.md Gate A ("Approval authorizes an unattended build") vs
  SKILL.md "Plan-review APPROVE is the authorization; the user does not
  hold a gate here"; DEVLOOP Stage 2 "Cap 3 rounds" vs SKILL "Cap 2
  rounds (+1 on a ruling)". Real contradictions. Agree 5/5.
- **NEW: Herdr has native notifications.** `herdr notification show
  <title> [--body TEXT] [--position ...] [--sound none|done|request]`
  (from `herdr notification` help). That is the operator's "visual
  notification" requirement, built in, on the screen he already watches.
  ntfy becomes the away-from-desk channel, not the primary one.
- **NEW: no context field in Herdr.** `herdr agent get` returns name,
  status, cwd, pane, title — no context/token data. Context % is only on
  harness status lines (your own pane shows "Context 100% left"; Claude
  Code and pi have their own formats). So context % = scraping visible
  status lines per harness. Fragile. I split it out as its own row.

## Concessions

- Item 6: you are right that handoff CONTENT is on disk (briefings,
  CODEX-PROMPT files, HANDOFF, REVIEW files). The only unproven gap is
  delivery acknowledgment. Accept: run manifest 4/5, delivery queue 2/5.
- Item 7: accept 2/5 for delegating pre-execution. No evidence it keeps
  the #321 result; the lead-context problem is also unmeasured.
- Item 5 location: accept `<git common dir>/herd/<run>/<issue>/` over
  per-worktree `.herd/`, because worktrees are deleted by merge_stack.

## Remaining points

- **Item 2 shape.** Proposed: a small watcher (one process per repo in a
  spare pane, or run from a hook) that reads run-log + `herdr agent list`
  and emits Herdr notifications, with ntfy as an optional second sink.
  Triggers split by who must act, per your point: OPERATOR = decision-
  needed, pane `blocked` on a permission dialog, pr-opened ("ready to
  merge", batched per assignment), run-end; LEAD-ONLY = worker BLOCKED
  (no operator alert unless unresolved for N minutes). Dedup key =
  (run, event ts). Is the per-issue decision resolution in runlog.py
  (closers matched by issue) a blocker, or acceptable for v1 with one
  open decision per issue? I say acceptable for v1, fixed with a
  decision id later.
- **Item 1 v1 = text first.** A `runlog.py`-adjacent `herd status --watch`
  table in a pane (role, agent name, herdr state, issue, last progress
  event, open decisions) before any web page. Web page later if wanted.
  Agree?
- **Item 0 (new, from you): reconcile contracts + run identity** before
  cards/yaml. Run identity: add an explicit `--run` (default latest) so
  overlapping runs do not merge; or declare one active run per repo and
  enforce it at `run-start`. I prefer enforcing one active run per repo
  for v1 (cheaper, matches how the operator runs herd). Your view?

## Proposed consensus table

| # | Implementation | Confidence |
|---|---|---|
| 0 | Reconcile DEVLOOP vs herd contracts; one active run per repo enforced at run-start | 5 |
| 2 | Attention watcher → `herdr notification show` (+ optional ntfy), operator vs lead triggers, dedup, clear on resolution | 5 |
| 1a | Text monitor pane: agents × issues × stage × open decisions, from run-log + herdr agent list | 5 |
| 1b | Context % column via status-line scraping, "unknown" when absent | 2 |
| 5 | Per-ticket folder under `<git common dir>/herd/<run>/<issue>/`, generated PROGRESS.md, existing artifacts moved there | 5 |
| 6a | Run manifest: ordered issues, owner, dependencies, parked state | 4 |
| 6b | Durable delivery queue with acknowledgments | 2 |
| 3 | Shared sentinel/evidence contract + short role cards; briefings generated from them | 4 |
| 4 | herd.yaml roster (role, harness, model/options, fallback order, card ref), validated; launch commands generated | 4 |
| 7a | Keep the lead as the single orchestrator | 5 |
| 7b | Delegate pre-execution to slot 3 | 2 |
| X | Tool-enforced transitions (dispatch needs approved spec, review names candidate, round cap escalates) | 5 |
| H | Keep herd's lifecycle ownership; OpenRig adoption | 4 / 2 |
| W | Watchdog that reports stale/unresolved obligations (no keep-awake prompts) | 4 |

Order: 0 → 2 + 1a → 5 + 6a → 3 + 4 → X → W; 1b, 6b, 7b only on observed need.

Write `CODEX-round-2.md`: AGREE / COUNTER per row (counter = new rating +
one-line reason), answers to the three questions above, and a final line
`CONSENSUS: yes` or `CONSENSUS: no — <rows still open>`. Reply with only
the path.
