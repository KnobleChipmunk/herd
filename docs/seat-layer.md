# Seat layer — what herd needs from Herdr (#42)

Status: decision, 2026-09-27. Roadmap row U8 (3/5): inventory the lifecycle
herd needs from its seat layer, keep Herdr first, and decide other transports
only after the OpenRig evaluation (#35, PR #50), which kept herd on Herdr. An
unsupported transport is reported, never faked.

## What herd uses today

From `skill/SKILL.md` and `tools/` at the #39/#41 working state:

| Operation | Herdr command | Used for | Needs from any seat layer |
|---|---|---|---|
| Detect | `HERDR_ENV=1`, `HERDR_PANE_ID`, `HERDR_TAB_ID` | refuse to run outside Herdr (`preflight.py`); the lead's pane (`mkbrief.py`); the run's tab (`run-start --tab`, #33) | an identity for "this seat" and its group |
| Lay out | `pane split --no-focus --cwd`, `pane layout` | slots 1–3 beside the lead | a new seat with a working directory, without stealing focus |
| Start | `agent start <name> --kind <k> --pane <p> -- <args>` | builder, reviewers, specialist (args from `bindings.launch_args`, #38) | start a named agent of a given harness in a seat and wait until it is ready |
| Name | `agent rename`, `agent list` | reuse rule; target by name; the monitor (#34) | stable names; a list of every agent with its seat, group and state |
| Talk | `agent prompt <name> <text> [--wait --timeout <ms>]` | dispatch, review rounds, sentinels to the lead (these do not wait) | submit a prompt to a named agent, optionally waiting for a settled state |
| Wait | `agent wait <name> --timeout` | long turns, backgrounded | block until the agent settles, with a timeout |
| Read | `agent read --source visible|recent-unwrapped`, `pane read` | status lines (model check), stalls, resume commands | read the agent's screen and recent history |
| Keys | `agent send-keys <name> enter` | dismiss a permission dialog | send named keys |
| State | `agent_status` idle / working / blocked / done / unknown, `state_change_seq` | stall and permission rules (#33) | agent state, including "waiting at an approval or question", with a change counter |
| Notify | `notification show --body --sound` → `result.shown` | operator alerts (#33) | a visible notification, and whether it was shown |
| Replace | `agent prompt <name> "/quit"` (pi, Codex) or `"/exit"` (Claude), then `agent start` in the same pane | the specialist slot changing harness | end an agent and start another in the same seat |
| Shut down | `/quit` or `/exit`, then `agent list` (the agent is gone), `pane read --source visible` (the shell and the agent's resume command), then `pane close` | after the retrospective; the closing report lists each resume command | end an agent, confirm it ended, capture how to resume it, remove the seat |
| Recover | `agent get` and `agent read` after a failed or `blocked` wait; `runlog.py status`, git and gh after a crash or compaction; a `session` event with `resumed`, `fresh`, `failed` or `unknown` (#32) | a stalled or crashed agent; a compacted lead | inspect an agent's state and screen after a failure, and resume or restart it in its seat |

## Support envelope

- **Supported:** Herdr is the supported transport. The run-log lock requires
  POSIX (#32). Verified configuration: this machine's example profile on Linux
  under WSL2 only; macOS and other binding profiles remain unverified here.
- **Not supported:** tmux without Herdr, and in-session subagents. `preflight.py`
  refuses to run outside Herdr and says so; that refusal is the report.
- **Why not tmux now:** tmux can lay out, name, type into and read panes, but
  it has no agent state (idle / working / blocked with a change counter) and no
  notification with a "shown" result. Herd's dispatch waits and stall and
  permission diagnosis need agent lifecycle state; its operator-alert delivery
  and retry need a notification result that says whether the alert was shown. An adapter would have to rebuild
  Herdr's agent detection. OpenRig's tmux layer shows the size of that work.
- **Why not in-session subagents:** herd's contract is that every evaluator
  runs in its own session with a fresh context and can be read, prompted and
  shut down by the lead (team design §3–4); an in-session subagent is not
  observable to the watcher or the monitor.

## When to revisit

If herd must run where Herdr cannot, write an adapter against the table's last
column (the operations herd needs), with a fixture test per row, and label
it untested until one live run passes. Until then the envelope is Herdr only.
