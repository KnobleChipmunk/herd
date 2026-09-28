# Herd on Orca: joint investigation

Status: final analysis, agreed by Codex and Claude after three draft revisions on 2026-09-27. No implementation is authorized by this document.

## Agreed assessment

Orca is a promising optional execution platform for Herd. The useful boundary is for Herd to define and verify the engineering workflow, and for Orca to run and observe its agents and managed workspaces. Keep Herdr supported while evaluating an Orca backend. Do not switch unattended builds to Orca on the evidence collected today: the live collaboration exposed launch and lifecycle-recovery problems.

The expected benefit is less manual supervision and better visibility. No build-speed, token-cost, or defect-rate improvement has been measured.

## Evidence and scope

We inspected Herd at `1a9ac3fe7d5050d9b087753cb75641420fe075c8` on `main`, the running Orca `1.4.215`, its version-matched CLI guides and help, and official Orca documentation. A real Claude Code agent was launched through Orca in the workspace associated with this checkout. Codex and Claude exchanged messages and investigated the same source tree. We did not modify repository files, configuration, credentials, branches, or proposals, and did not run a Herd build.

Codex ran the Herd baseline validation: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider` produced **509 passed in 10.46s**; `ruff check --no-cache tools tests` passed. No type-check command is configured in `pyproject.toml` or a repository CI workflow. These checks validate the current Herd baseline, not an Orca integration.

### Live observations

| Observation | What it establishes | What it does not establish |
|---|---|---|
| Orca status and worktree discovery succeeded | The installed runtime is reachable and knows this checkout | Correct launch directory or working agent supervision |
| A Claude terminal was created; initial receipt was `outcome_unknown`, `turn_start_unobserved` | Input acceptance and a live process are distinct from a proven started task | That the original task ran or that a duplicate should be launched |
| A follow-up orchestration message woke Claude; subsequent replies and transcript reads worked | The ordinary messaging/read path is usable here | Reliable original dispatch or authenticated lifecycle completion |
| Claude reported its initial working directory was `/home/tusk/projects`, which is not a Git repository, and verified the Herd repository after explicitly entering `/home/tusk/projects/herd` | The exercised launch did not give Claude the intended default working directory; both agents nevertheless inspected the intended source | Why Orca's workspace association and the actual directory diverged |
| A heartbeat was rejected for a missing dispatch capability; a regenerated preamble omitted the required flag | The exercised recovery path cannot supply the required lifecycle authority | That every normal Orca launch has the same problem |
| Coordinator-generated recovery preamble named the coordinator; Claude reported its worker-generated copy named itself | Recovery preamble behavior depends on who requests it | What the lost original injected preamble contained |
| Session-history indexing reports `enabled: false` | Search is unavailable in this installation as configured | That Orca has no history feature |

The first CLI call failed at the sandbox/WSL socket boundary and succeeded outside the sandbox. That is an access constraint of this session, not evidence of an Orca runtime defect. We did not restart or upgrade Orca to investigate these symptoms.

## Capabilities and value to a Herd build

| Area | Orca capability | Value and qualification |
|---|---|---|
| Agent execution | Supervised workers, tasks, dispatch attempts, durable messages, questions, explicit outcomes | Could replace prompt/wait glue and make ownership and incomplete work easier to recover. Lifecycle authority still needs validation here. |
| Workspaces | Real Git worktrees, parent relationships, setup hooks, scoped terminals and browser tabs | Could make build/reference worktrees and stacked work visible together. UI lineage and Git base are separate choices. |
| Operator visibility | Agent status, dashboard, workspace comments, diffs, hosted-review UI, mobile companion | Could reduce pane hunting and make an unattended run easier to inspect. A generic agent-finished notification does not prove a Herd decision was delivered to a human. |
| Product QA | Scriptable browser, screenshots, browser profiles, computer-use and mobile tooling | Useful evidence surfaces for the existing QA and designer roles, especially on UI projects. Tests still need an identified candidate and isolated data. These capabilities were read, not exercised. |
| Longer-lived work | Session restoration, optional transcript search, scheduled prompts, remote runtimes | Potential later improvements for supervision and recovery. Runtime/process restoration is different from resuming the correct Herd step. Remote and scheduled operation are not validated by this local investigation. |

Official references: [Orca overview](https://www.onorca.dev/docs), [orchestration](https://www.onorca.dev/docs/cli/orchestration), [worktrees](https://www.onorca.dev/docs/model/worktrees), [agent status](https://www.onorca.dev/docs/model/agents-sessions), [browser](https://www.onorca.dev/docs/browser/overview), [session restoration](https://www.onorca.dev/docs/model/session-restore), [automations](https://www.onorca.dev/docs/cli/automations), [mobile](https://www.onorca.dev/docs/mobile).

The clearest execution benefit targets a specific Herd mechanism: `tools/mkbrief.py` currently tells workers to send `DONE`, `BLOCKED` and `REVIEW CLEAN` by prompting the lead's Herdr pane. Durable messages, acknowledgments and attempt-specific authority could make those handoffs easier to track and recover. They still carry pointers to evidence that Herd must validate.

## Responsibilities must stay explicit

| Responsibility | Proposed owner on an Orca backend |
|---|---|
| Task selection, scope, role assignment, review rounds, disputes, operator decisions | Herd's lead and existing policy |
| Exact harness/provider/model/login choice and permitted fallback | Herd bindings, verified against the actual launch |
| Process start, prompt delivery, runtime identity, dispatch lifecycle, live observation | Orca |
| Managed worktree creation and resource cleanup | Orca performs the operation; Herd decides eligibility and preserves build/reference evidence |
| Specifications, pre-execution, fences, gate counts, mutation tests, independent review, candidate-specific QA | Herd |
| Domain history, ticket closure reasons, unresolved obligations, retrospectives and librarian | Herd's existing records and tools |
| UI status and navigation | Orca presents a projection of the relevant Herd and runtime facts |
| Merge, publication and other operator-reserved decisions | The operator under Herd's existing rules |

Three distinctions are essential. A settled process is not an accepted build. An Orca Task marked completed is not a Herd ticket with every promised check passed on one candidate. A reused terminal is not necessarily a fresh independent evaluator. An integration has to preserve each distinction in its data and recovery rules.

Orca's coordinator-owned decision gates can pause task dependencies. They do not authorize the coordinator to answer a decision Herd reserves for the user. Agent launch permission flags and role authority are also separate: a worktree is filesystem organization, not an OS security boundary. The observed Claude launch used the existing bypass-permissions configuration; we did not change it. [Orca launch defaults](https://www.onorca.dev/docs/agents/supported)

## Concrete integration seams

Herd already documents the required seat operations in [docs/seat-layer.md](seat-layer.md). This makes the evaluation tractable, but it is not an implemented transport interface.

| Files | Adaptation needed |
|---|---|
| `tools/preflight.py`, `tools/bindings.py` | Select and verify a backend instead of always requiring `HERDR_ENV=1` and the `herdr` binary; preserve exact binding readiness. |
| `tools/dispatch.py`, `tools/mkbrief.py`, `skill/SKILL.md` | Route tasks and replies through the selected backend; carry runtime identities and completion evidence; replace Herdr-specific topology and shutdown instructions. |
| `tools/attention.py`, `tools/context_collector.py` | Map runtime observations without treating unknown as idle; retain Herd obligation and alert semantics; establish available context/notification evidence. |
| `tools/runlog.py`, `tools/team.py`, `tools/tickets.py` | Preserve domain records and link them to Orca Run/Task/Dispatch identities. Define reconciliation after one side records progress and the other does not. |
| `tools/merge_stack.py` | Route managed-worktree cleanup through its owner while retaining merge ordering and protection of unmerged or dirty work. |

The deterministic build checks (`herdtool`, `fencecheck`, `gates`, `mutate`) largely concern files and test results. The investigation does not justify rewriting them. Existing role cards and current-step packets remain useful inputs to Orca task specifications.

One concrete flow would be: Herd approves a plan; Orca starts the bound builder in a managed build worktree; Herd receives and checks its candidate evidence; Orca starts a fresh reviewer; Herd evaluates that review and routes any next round. Orca completion would settle each delegated activity, while Herd advances the overall engineering workflow only after its own evidence requirements are satisfied.

## Risks that change the decision

| Risk | Required response |
|---|---|
| Partial launch and broken recovery preamble | Treat as a blocker for unattended adoption in this environment. Prove delivery, completion and cleanup on the installed version before implementation depends on them. |
| Binding mismatch | Pi is documented as supported, but `worker-start --model` does not support Pi overrides. Prove the local provider, endpoint, model and login mapping without silently using a default or changing global credentials. Exact Pi supervision was not exercised. |
| Two competing controllers or records | Assign one runtime owner per resource. Keep Herd domain facts and Orca execution facts separate, with stable links and replay/reconciliation rules. Never have Herdr and Orca both supervise the same worker. |
| Lost human obligations | Preserve decision, permission, intentional-wait, overdue and PR-ready distinctions. We found no demonstrated equivalent of Herdr's acknowledged notification `shown` result. |
| Portability and feature drift | The current Herd log uses POSIX `fcntl`; Orca on Windows does not make Herd natively Windows-compatible. Prefer installed CLI guides and negotiated capabilities; preserve unknown states across version/host boundaries. |

For remote workers, keep Herd's authoritative log on one coordinator host; transfer packets and evidence through explicit channels. Do not assume a shared JSONL file and local filesystem lock provide a distributed transaction. For browser QA, distinguish desktop-hosted pages from server-hosted pages when the desktop sleeps. For session reuse, preserve fresh non-author evaluation even if terminal reuse is convenient.

Orca reports this WSL workspace using a Windows UNC path, while Herd operates on Linux paths. The adapter must prove those identities refer to the same checkout. A verified mapping may solve this; it does not require Orca to change its public path format. Similarly, Orca's UI documents waiting-for-input states, but an equivalent machine-readable input to Herd's watcher remains unverified. We do not claim that Pi supervision or permission-state observation is impossible because a short CLI help list omits it.

## Alternatives and staged decision

| Choice | Assessment |
|---|---|
| Keep Herd on Herdr and use Orca for inspection | Lowest disruption; gets editor/diff/navigation benefits but little execution integration. |
| Add an optional Orca backend | Best candidate for further evaluation. Preserves Herd policy and the existing supported route while testing Orca's execution benefits. |
| Make Orca mandatory immediately | Premature given the observed lifecycle problems, exact-binding gaps and absence of an end-to-end Herd trial. |
| Reimplement Herd policy as Orca task configuration | No evidence that Orca replaces Herd's pre-execution, gates, independence, mutation or ticket contracts. High risk of losing those behaviors. |

The earlier [OpenRig evaluation](openrig-evaluation.md) rejected the operational cost of an additional controller and store. Orca is already installed here, which changes the marginal setup cost. It does not remove the cost of reconciling state, maintaining compatibility, or supporting other Herd installations.

An Orca backend would explicitly revise the recorded decisions to keep lifecycle ownership in Herd's current loop and to support Herdr alone. It cannot be treated as already supported by changing a preflight flag. The repository's own [seat-layer procedure](seat-layer.md#when-to-revisit) calls for an adapter against the documented operation contract, a fixture test for every row, and an untested label until a live run passes. A future implementation should present that support-envelope and ownership change in its own reviewed proposal/PR. [CLAUDE.md](../CLAUDE.md) specifically requires any gate relaxation, expansion of agent edit authority, or skipped check to be labelled and kept separate; adding an equivalent backend check should not silently relax those policies.

The proposed sequence starts with an isolated, read-only Claude/Codex evaluator trial in an existing checkout, after the launch/recovery problems are addressed. This checks fresh context, message delivery, outcome reporting, attention and recovery without creating or deleting worktrees. It is not a recommendation to split a live Herd run between two supervisors.

A full build pilot comes next only after exact builder bindings and complete watcher coverage are proven. It uses one selected backend for the run. For Orca-managed worktrees, Herd retains every existing eligibility and preservation check before asking Orca to perform cleanup. Dirty-tree and scratch-reference preservation must pass before that cleanup is enabled. Any deliberately unmanaged scratch resource stays with its explicitly recorded Git owner.

Only after a supervised Herd build passes should measured supervision benefits determine broader adoption. Browser QA, richer status views and evidence navigation can follow independently. Scheduling and multiple hosts should wait until local recovery is reliable. This investigation supplies neither an implementation time estimate nor a claim that adoption will be cheaper overall.

### Acceptance criteria for a later pilot

1. **Launch and identity:** correct directory and Git base; Windows UNC identity reconciled with the Linux checkout; intended harness, model, provider and login; fresh non-author reviewer; preserved launch policy.
2. **Delivery and settlement:** accepted input distinguished from started work; timeout produces no duplicate worker; valid capability permits the worker's outcome; a stale attempt cannot complete current work.
3. **Recovery and evidence:** coordinator/session interruption recovers the right step and candidate; missing or changed evidence blocks advancement; repeated delivery does not repeat side effects.
4. **Human attention and cleanup:** a blocked permission produces an acknowledged alert; a working Orca agent suppresses a false stall alarm; an operator decision remains visible; failed alert delivery is observable; cleanup preserves unrelated terminals, dirty work and unmerged evidence.
5. **Measured value:** record intervention count, recovery time, abandoned resources and end-to-end duration against a comparable Herdr run, while confirming identical Herd gates and independent evaluation.

These are proposed experiments for a separate authorized implementation or trial. None was silently treated as passed by this investigation.

Still unverified: the cause of the original launch failure; whether its original injected preamble contained a capability; exact Pi binding fidelity; the mapping of Orca effort preferences to the configured reviewer; equivalence of idle/done/blocked observations; machine-readable permission-state and notification delivery parity; and dirty/scratch preservation through Orca removal. These are shared uncertainties, not claims that the capabilities cannot work.

## Consensus record

Codex approves the full analysis. Claude explicitly approved every finding, qualification and recommendation in draft v3 at `2026-09-27T23:54:46Z`, message `msg_1bd20ff70a62`. No substantive disagreement remains; the uncertainties above are jointly acknowledged.

The discussion resolved three material points: an isolated evaluator trial precedes a complete build pilot; there is one execution backend per build run; and Herd retains cleanup eligibility while Orca performs removal of its managed resources only after parity is established. We also corrected unsupported claims that Pi could not be launched and that the initial launch used low-level dispatch. The actual command was the normal `worker-start` path; exact Pi binding behavior remains untested.

Investigation Run: `run_2f4437e76eb3`. Claude Task: `task_30eb7cb66949`. Dispatch: `ctx_f8714b53aead`. Ordinary consensus messages succeeded. Normal authenticated lifecycle settlement was unavailable because the recovery preamble lacked the required dispatch capability. Analytical completion must not be confused with successful Orca lifecycle validation.

After Claude's final turn was observed, the coordinator used the documented `worker-abandon` recovery to fence that unusable dispatch. Orca returned `state: abandoned`, `processAction: none`. It had classified the terminal as user-owned and retained; the terminal was preserved, and no process or worktree was stopped or deleted. This records failed lifecycle settlement honestly while preserving the completed analysis.

At the end of the investigation, both agents confirmed zero tracked changes and the same 44 pre-existing untracked PLAN-REVIEW/RETRO files. The report was originally delivered outside the repository; the operator subsequently authorized recording it here and merging it to main for future reference. That authorization covers this documentation record, not an Orca implementation.
