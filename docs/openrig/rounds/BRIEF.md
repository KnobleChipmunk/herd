# Brief: what should our "herd" workflow learn from OpenRig?

You are a peer reviewer in a design discussion with Claude (Opus 5.5), who
runs in the pane to your left. The operator (Nate) wants the two of you to
reach a CONSENSUS on which ideas to implement, each with a confidence rating
you BOTH agree on. This is a design review. Do NOT edit any file outside the
discussion folder named below, do not run builds, do not start agents.

Discussion folder: /tmp/claude-1000/-home-tusk-projects/0fc76281-c36a-45d9-a94c-5b4b3980d066/scratchpad/openrig/
Write your replies there as `CODEX-round-N.md` and reply in the pane with only the path.

## 1. OpenRig (the external system)

Source: YouTube video "I Run A Cross-Harness Fleet As A Software Factory"
(OpenRig channel, 2026-06-30), github.com/mvschwarz/openrig (Apache-2.0,
`npm i -g @openrig/cli`). A daemon + CLI + web UI on a laptop that runs
Claude Code and Codex agents as one team.

Four primitives (from the video):
- **Rig** — a whole team in one config file ("RigSpec": pods, members,
  edges, continuity policies, culture file). "Docker, but for agents."
  `rig up`, `rig down --snapshot`, `rig ps --nodes`, `rig grow/shrink`,
  `rig discover`/`rig adopt` for existing sessions.
- **Coordination** — each agent sits in a named tmux session ("seat").
  Observe: `rig capture` (capture-pane, live screen), `rig transcript`
  (pipe-pane, saved history). Durable handoff: `rig send` (send-keys) +
  `rig queue` (SQLite; every item has an owner and a status). "Not Jira."
- **Workflows** — YAML the daemon enforces. Example rail: Architect (sets
  shape) → Planner (writes spec) → Builder → Reviewer → Test QA → Dogfood
  → back to Architect. Agents write workflows themselves. A **watchdog**
  ("the clock") keeps agents awake for weeks, like /loop for both harnesses.
- **Workspaces** — a markdown control plane in a fixed folder convention,
  saved as a template so "agents don't invent their own mess":
  ```
  workspace/
    README.md  PROGRESS.md
    missions/<mission>/README.md
      slices/01-client-preview/{README.md, PROGRESS.md, proofs/, handoffs/}
    skills/
  ```
  `rig scope` creates a trackable ticket plus its workspace folder in one
  move. The markdown generates the web UI.

Other claims: Claude = "right hemisphere" (big picture, planning, design),
Codex = "left hemisphere" (precise, debugging, review). Steering "by
altitude": manage by exception, drop into a terminal when needed. The user
mostly talks to ONE orchestrator agent that rig-scopes work into missions
and slices, writes specs, and hands pieces to rigs. Ran a "recursive
self-improvement" setup for weeks (build rig + product-management rig +
dogfood rig, feedback routed to PM); author dialed it back for lack of
guardrails; got stuck on rate limits.

Screenshots of the web UI (paths are readable if you can view images:
/mnt/c/Users/Tusk/Pictures/Screenshots/Screenshot 2026-09-27 0523{16,28,41}.png):
- Graph view: pods (dev1 pod: design/impl/qa; rev1 pod: r1/r2; lead+peer).
  Each seat card shows harness (CLAUDE/CODEX), **context used % (5%, 73%,
  78%)**, token count (54k, 188k), "RESTORE: resumed", status dots, edges.
  Tabs: GRAPH / TABLE / TERMINAL / OVERVIEW.
- Mission page: tabs OVERVIEW / STEERING / STORY / PROGRESS / ARTIFACTS /
  PROOF / QUEUE / WORKFLOW. Overview lists slices with DONE / IN PROGRESS /
  QUEUED / ACTIVE.
- Story tab: "queue lineage as a git graph", one line per queue item:
  summary, owner seat (devl-design, rev1-r2, orch1-peer), state (Done /
  In progress / Handed off), date, qitem id.

NOT documented in the README (verified by Claude via fetch): the RigSpec
YAML example, the workflow YAML format, queue field names, the watchdog,
how the UI detects "needs a human", notifications. README says the React
web UI is in "maintenance mode"; a TUI is primary.

## 2. Our system: the herd skill + Herdr

Read these yourself (read-only):
- `/home/tusk/.claude/skills/herd/SKILL.md` (≈600 lines) — the loop
- `/home/tusk/.claude/DEVLOOP.md` — the older canonical loop (sentinels,
  gates, handoff payload)

Short version: Herdr is a terminal multiplexer that recognises agents in
panes (`herdr agent list/prompt/read/wait`, states idle/working/blocked/
done). The herd lead (Claude, the operator's session) writes an openspec
change, PRE-EXECUTES it in a scratch worktree, sends it to a Codex plan
reviewer, then a local pi builder builds in a worktree and round-robins with
a Codex build reviewer; the lead runs a final review and pushes a PR.
Durable state: `<git common dir>/herd/run-log.jsonl` via `tools/runlog.py`
(kinds: run-start, spec-approved, dispatched, review-round, blocked,
decision-needed, pr-opened, friction, ...). Per-ticket files
(BUILD-BRIEFING, HANDOFF, REVIEW-round-N, PLAN-REVIEW, RETRO) sit untracked
in the repo root. The Roster table in SKILL.md names models per role and is
parsed by `tools/probe.py`. A post-run "librarian" (Hermes, local model)
files friction into ledgers and writes proposals the operator accepts or
rejects — improvements reach the skill only via an operator-merged PR.
Sentinels: DONE / BLOCKED / ASK. Operator gates: merge, archive, retro signoff.

## 3. The operator's seven wanted concepts

1. A built-in monitor showing progress/status of all agents
2. A visual notification when human help is needed
3. A workflow loop that tells each agent its individual role in the team
4. A YAML config defining role and scope of each agent
5. A markdown status report for every ticket
6. A ticketing system agents can use to stay organized
7. An orchestrator agent the operator talks to, which relays to the team

## 4. Claude's initial proposals (challenge these)

Mapping: Rig ↔ Roster table; Coordination ↔ Herdr panes + prompt/read/wait;
Workflow ↔ prose rules + sentinels + runlog; Workspace ↔ loose files in
repo root; Web UI ↔ nothing (operator reads panes).

- **1 Monitor** — read-only page built from `herdr agent list` +
  `run-log.jsonl`; show per-seat context % (the most valuable signal in
  OpenRig's graph — warns before compaction). Medium.
- **2 Notification** — watcher on run-log + herdr agent states pushes ntfy
  (operator already uses ntfy) on decision-needed, BLOCKED, pane stuck
  `blocked`, pr-opened. Cheapest high-value item. Small.
- **3 Role cards** — split the 600-line SKILL.md into a thin lead file plus
  one role card per role (builder, build reviewer, plan reviewer) holding
  contract, sentinels, who it may talk to. Briefings point at the card.
- **4 herd.yaml** — replace the Roster table with YAML: role, harness,
  model, pane, fallback chain, allowed paths, may-message, round caps. One
  source for probe/preflight/briefing/monitor. Enabler for 1, 2, 6.
- **5 Ticket folder** — `.herd/<id>/` holding handoff, review rounds,
  retros, plus a PROGRESS.md generated from run-log. openspec change folder
  already plays OpenRig's slice README.
- **6 Queue** — caution against building Jira. GitHub issues = human layer,
  run-log = audit. Gap: agent-to-agent handoffs travel as ephemeral
  `herdr agent prompt` text lost if a pane dies. A small durable queue
  (id, from, to, kind, status, payload_path) — only if lost prompts are a
  real problem. Medium-large.
- **7 Orchestrator** — PUSHBACK: the herd lead already is the orchestrator,
  and it also pre-executes and final-reviews; retro #321 credits
  pre-execution for one-round clean reviews. A thin relay-only orchestrator
  would lose that. Cheaper fix for the real problem (lead context filling):
  delegate pre-execution to the slot-3 pane, keep the lead for routing and
  rulings.
- **Herdr + OpenRig together** — probably not; both own the seat/send
  layer (tmux vs Herdr), two sources of truth. Copy ideas, keep Herdr.
- **Extra** — move enforcement from prose into tools (herd already trends
  there: gates.py, mutate.py, runlog.py). The librarian→proposals→operator
  merge chain is already a guarded version of OpenRig's RSI loop.
- **Order**: 2, 4, 5, 1, 6.

## 5. What to do in round 1

Write `CODEX-round-1.md` with:
- For each numbered item (1–7, the Herdr+OpenRig question, the Extra, and
  the Order): AGREE / DISAGREE / MODIFY, your reasoning grounded in what
  you read in the herd files (cite file:line where it matters), and a
  confidence rating 1–5 (5 = would bet on it; ≤2 = do not build yet)
  that this is worth implementing as described or as you modify it.
- Anything Claude missed: ideas from OpenRig not listed, risks, or cases
  where herd already does it and the proposal is redundant.
- Mark any claim you did not verify from a file as UNVERIFIED.
Keep it tight: one short paragraph per item.
