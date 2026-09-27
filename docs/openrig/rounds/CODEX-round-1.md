# Codex — round 1

Build visibility and explicit human-attention signals first. Keep the existing lead and review loop. The largest correction to the brief: OpenRig now documents Herdr terminal integration, so incompatibility is not established. These are my proposed ratings, not yet consensus; 5 means high confidence the stated change is worthwhile, and ≤2 means do not build yet.

Citation key: **H** = [/home/tusk/.claude/skills/herd/SKILL.md](/home/tusk/.claude/skills/herd/SKILL.md); **D** = [/home/tusk/.claude/DEVLOOP.md](/home/tusk/.claude/DEVLOOP.md); **R** = [/home/tusk/projects/herd/tools/runlog.py](/home/tusk/projects/herd/tools/runlog.py); **P** = [/home/tusk/projects/herd/tools/probe.py](/home/tusk/projects/herd/tools/probe.py). Numbers below are source lines. Read both requested files completely and inspected the cited tool code. This is a design review: no builds, agents, runtime experiments, or edits outside this folder. Video/screenshot claims remain **UNVERIFIED** unless explicitly corroborated below; documented behavior is not a tested integration.

## 1. Monitor — MODIFY, 5/5

Start with a compact, read-only table: agent/role, issue, workflow stage, observed pane state, last observation time, unresolved decision, and evidence link. Keep workflow progress distinct from pane activity: herd explicitly treats idle without a sentinel as a stall (H:531–534; D:19–27). Show context percentage only when a harness supplies a trustworthy current sample; otherwise show unknown. Herdr's context-percentage API is **UNVERIFIED**, so it must not block the monitor. Also, `status` selects the latest run (R:49–56,136–138); an all-agent view needs explicit run/session associations and must label agents it cannot associate.

## 2. Human notification — MODIFY, 5/5

Use a persistent visible “needs you” indicator with the exact question and a link to its ticket/pane; ntfy can deliver the same alert. A worker's `BLOCKED` usually asks the lead to rule, not the operator (H:312–313,378–384); distinguish that from `decision-needed`, an operator gate, or a permission prompt requiring human action. Treat `pr-opened` as “ready for merge,” with assignment-level batching where appropriate. Deduplicate alerts across watcher restarts and clear them on explicit resolution. R:104–110 currently resolves decisions by issue, so multiple concurrent questions would need separate IDs. Nate's ntfy setup is **UNVERIFIED**.

## 3. Role cards — MODIFY, 4/5

Extract the existing contracts into one shared sentinel/evidence contract plus short role cards, and generate each assignment's briefing from those sources. The roles and communication edges already exist (H:216–230,370–396), and the briefing already specifies scope, gates, handoff evidence, and literal coordination commands (H:442–459). This improves delivery and maintenance of instructions; it does not create a missing workflow. Keep sequencing and operator gates with the lead, and require each card to state inputs, outputs, completion evidence, escalation target, and prohibited actions. Avoid copying the same rule into YAML, cards, and briefings.

## 4. `herd.yaml` — MODIFY, 4/5

Replace Markdown parsing with a small validated roster: role, harness, model/options, fallback order, and role-card reference. P:29–42 extracts model IDs from backticks in prose, while H:163–169 repeats model names in launch commands despite H:21–23 declaring a single source. Generate those commands too. Keep actual pane/session IDs, worktree paths, and ticket-specific allowed files in a resolved run record; slot 3 changes occupants (H:190–202). Validate fallback references and cycles. YAML permissions remain declarations unless a tool enforces them. This is useful configuration cleanup, but notifications and the first monitor do not depend on it.

## 5. Ticket folder and Markdown status — MODIFY, 5/5

Give each ticket one durable artifact directory keyed by run and ticket, with generated `PROGRESS.md` and links to its OpenSpec change, branch, reviews, proof, and next action. Prefer the existing shared `<git common dir>/herd/` root over independent `.herd/<id>/` copies in disposable worktrees (H:481–484,554–561). Keep human-authored evidence intact; regenerate only status. Existing handoffs already contain extensive proof (H:450–454), so standardize their address rather than inventing a second evidence format. Preserve the untracked policy (H:571–575), update every producer/consumer, and ensure the librarian can still read artifacts after worktree cleanup.

## 6. Ticketing and durable queue — MODIFY, 4/5 for a run manifest; 2/5 for a delivery queue

Persist the ordered issue list, owner, dependencies, and current assignment so agents can see queued and parked work as well as active work. The sweep already calls for this ordering (H:56–57,81–87), but R:23–34 has no queued-item/dependency fields and `status` sees only issues with progress events (R:91–103). Keep GitHub issues as ticket identity. The claim that handoff content exists only in ephemeral prompts is contradicted by prompt files, briefings, handoffs, and review files (H:204–206,442–459). Delivery acknowledgment is a separate gap; actual lost-work incidents are **UNVERIFIED**. Add persistent dispatch/acknowledgment only after demonstrating that failure, with duplicate-delivery handling before automatic retries.

## 7. Orchestrator — MODIFY, 5/5 for retaining the lead; 2/5 for delegating pre-execution now

The operator already talks to one orchestrator with spec, routing, dispute, and final-review authority (H:8–10,245–255). Preserve that contract. The documented #321 results support verified pre-execution and byte-synced fences (H:13–17,255–268); they do not establish that moving execution to slot 3 preserves those results or saves enough lead context. That benefit is **UNVERIFIED**. If later piloted, keep the lead responsible for spec corrections and evidence acceptance, and give the plan reviewer a fresh session after slot-3 execution. Reusing the executor's context would weaken the independent challenge described in H:216–228.

## Herdr + OpenRig — MODIFY, 4/5 for retaining herd while evaluating compatibility; 2/5 for adoption

The current [OpenRig getting-started file](https://github.com/mvschwarz/openrig/blob/main/docs/reference/getting-started.md#share-the-dashboard-and-return-to-it) explicitly documents `rig terminal open first-project --provider herdr` and identifies this as terminal integration. Thus “tmux versus Herdr” is insufficient grounds to reject coexistence. The real question is who owns session lifecycle, dispatch, and workflow state: herd currently starts, reuses, and shuts down its agents (H:153–158,358–367). Retain that ownership for now. Compatibility with the existing pi builder, native Herdr agent recognition, and herd's lifecycle commands is **UNVERIFIED**; documented terminal display alone proves none of those.

## Extra: enforcement and self-improvement — AGREE, 5/5 for narrow tool enforcement

Turn existing mechanical invariants into checked transitions: dispatch must reference approved spec/evidence, review completion must identify its reviewed candidate, and configured round caps must trigger the existing escalation. H:263–268 requires fence parity, H:378–395 requires bounded rounds and evidence, and H:461–477 describes shared mutation enforcement; R:59–80 currently checks required fields and appends events, not workflow legality. Build around these concrete contracts before considering a general YAML workflow engine. Preserve librarian proposal → acceptance → PR → operator merge (H:503–520), and prevent a running assignment from silently changing the rules used to judge itself.

## Order — MODIFY, 4/5

Sequence: first reconcile state/attention meanings and run identity; then ship item 2 with a minimal item 1 view; then item 5 plus the small run manifest from item 6; then items 3 and 4 together; finally enrich monitoring and reconsider queues or delegation only with observed failures and measured benefit. This brings the operator's two visibility requests forward without requiring a configuration migration first. Existing run-log checkpoints already supply much of the first view (H:486–501). Queue delivery, OpenRig adoption, and delegated pre-execution remain outside the initial implementation.

## What the proposals missed

**Conflicting contracts — reconcile before generating cards, 5/5.** D:41–44 gives the operator spec approval and D:73–77 reserves commits/pushes to the operator; H:301–310 and H:545–552 explicitly grant the lead those actions. D:58–60 caps reviews at three rounds; H:378–380 uses two plus a ruling. Encode the current herd rules for herd and make the older loop's applicability explicit, or automation will preserve contradictions. No broader rewrite is needed for this decision.

**Recovery, stable identity, and bounded wakeups — MODIFY, 4/5.** OpenRig's [getting-started file](https://github.com/mvschwarz/openrig/blob/main/docs/reference/getting-started.md#incomplete-setup-and-restart) distinguishes reattaching, resuming, and starting fresh. Herd already recovers from disk and records shutdown resume commands (H:358–368,481–484); make those references visible alongside run, role, session, worktree, and latest evidence. A watchdog should first report stale observations or unresolved obligations. Unconditional keep-awake prompts can interrupt intentional waits; any recovery action needs a bounded retry rule and preserved operator gates. D:104–105 mentions a watchdog, but its actual implementation is **UNVERIFIED**.

**Multiple runs and unresolved obligations — MODIFY, 4/5.** R:65–72 assigns later events to whichever run started most recently, and R:49–52 slices at that start. Inference from the implementation: overlapping runs in one repository can attribute events to the wrong run, while a latest-run-only dashboard can omit older unresolved decisions. Before claiming fleet-wide visibility, bind events to an explicit run or explicitly restrict the first version to one active run per repository and retain unresolved older obligations. Show dependency/blocked-by relationships from the manifest; a full graph can wait.

Context check: the `global-memory` skill retrieved the active simplicity preference, `mem_8551e775-fa2f-4644-ac96-9f2978dcb953`, Vault path `10 Global/Preferences/Orchestration complexity acid test--8551e775.md`. It supports trying a small deterministic tool before adding another orchestration layer; its historical examples are **UNVERIFIED** here. Project detection for `/home/tusk/projects` was unresolved, and the focused herd-history search returned no results; the cited files carry the technical conclusions.

Next action: Claude, start round 2 by accepting or challenging the revised Herdr-compatibility premise, then propose any changes to these ratings. Agreement is still pending.
