# OpenRig evaluation — extend herd, or reuse OpenRig? (#35)

Status: decision, 2026-09-27. A 60-minute desk study from the OpenRig source
(`github.com/mvschwarz/openrig`, commit `f137f11`, v0.5.17), with no install on
this machine (operator decision on #35). It decides build vs reuse for the
ticket steps (#36, #37) and records the questions roadmap row P named.

## Verdict

**Extend herd: copy OpenRig's queue contracts into our own ticket tool.** Of the
four ways to reuse the queue (below), only copying the contracts adds no new
runtime to every herd machine. The operator's rule for #35 ("if it recommends
reusing OpenRig for #36–#37, park them") does not trigger: the recommendation
is to build in herd.

## Four ways to reuse OpenRig's queue

| Option | What it takes | Cost for herd | Verdict |
|---|---|---|---|
| A. Adopt OpenRig as the controller | run the daemon; register herd's agents as OpenRig seats (`rig adopt ... --bind <logicalId=tmuxSession>`, `cli-reference.md:768`) | requires transferring agent lifecycle to OpenRig, or conflicts with herd if both keep ownership (consensus row H, 2/5); sessions stay tmux-backed, with Herdr only as a display | no |
| B. The daemon's queue, with herd delivering | run the daemon; register a rig so destinations validate (the check is on the rig, not on a live seat: `packages/daemon/src/startup.ts:307-339`); create items with `--no-nudge` (delivery is skipped without a nudge or a transport, `queue-repository.ts:1187-1198`); herd still prompts agents itself | a separately operated service: a Node 20+ daemon with its own SQLite store and transaction boundary, apart from herd's run log and lock; rig registration and a mapping from herd's roles to queue addresses; daemon start and restart become part of the loop. An operational dependency we choose to avoid. Untested live. | no |
| C. Extract `QueueRepository` | its constructor takes a database, an event bus and optional hooks (`queue-repository.ts:648-687`; the tests build it without seats) | TypeScript inside a Python toolkit; not exported by `packages/daemon/package.json`; needs OpenRig's SQLite migrations | no |
| D. Copy the contracts | the claim step, the closure reasons with targets, the transactional handoff, in Python on herd's run-log lock (#32) | two local event files (the run log and `tickets.jsonl`) under herd's existing lock and runtime; a few hundred lines (`tools/tickets.py`, #36) | **yes** |

B is the closest real alternative. It would reuse tested code, but its price
is a separately operated service and a second store to keep consistent with
the run log.

## The seven capabilities

| Capability | Herd after this roadmap | OpenRig | Reuse? |
|---|---|---|---|
| Monitor of all agents | `attention.py monitor` over `herdr agent list` + run log (#34) | TUI mission control | no: Herdr already owns the panes |
| Notification when a human is needed | `attention.py watch` → `herdr notification show`, optional ntfy (#33) | attention view, plus configurable ntfy or webhook push for human-gate queue arrivals, disabled by default (`mission-control.md:118-123`; `startup.ts:1478-1513`) | no: herd's alerts come from its run log and Herdr, which OpenRig's dispatcher does not see |
| Loop that tells each agent its role | role cards + current-step packet (#40, team design §2) | AgentSpec guidance + workflow step | no: contract copied in the team design |
| YAML defining role and scope | portable `herd.yaml` + local bindings (#38, #40) | RigSpec + AgentSpec | no: schemas differ (roles vs seats) |
| Markdown status report per ticket | one page per ticket (#37) | mission/slice PROGRESS.md | no: we build it on our records |
| Tickets agents can use | our ticket tool (#36) | `rig queue` (daemon-only) | **contracts only** (below) |
| Orchestrator the operator talks to | the lead (row 7a) | the orchestrator seat | no |

## What #36 copies from `rig queue`

From the implementation at `f137f11` (the CLI reference lags it):

- **Claim.** An item stays `pending` until its receiver claims it
  (`claim <id> --destination <session>` → `in-progress`,
  `cli-reference.md:1277`). The claim is the acknowledgment row 6b said was missing.
- **Closure reasons.** `CLOSURE_REASONS` has seven values: `handed_off_to`,
  `blocked_on`, `denied`, `canceled`, `no-follow-on`, `escalation`, and
  `superseded` (a row corrected by cancel-and-replace;
  `packages/daemon/src/domain/hot-potato-enforcer.ts:18-28`). A reason is
  required only when the state becomes `done` (`:59-65`), and a target only for
  `handed_off_to`, `blocked_on` and `escalation` (`:86-95`). Herd's adaptation:
  every close needs a reason (herd has one terminal state); `handed_off_to`
  comes only from `handoff`, and `blocked_on` only from `block`, which keeps the
  ticket open; `close` takes `no-follow-on`, `denied`, `canceled`, `superseded`
  (optionally naming the successor) or `escalation` (with a target).
- **Transactional handoff.** `handoff` closes the source as handed off and
  creates the successor in one operation (`cli-reference.md:1281`). In herd
  this is one locked write, using the run-log lock from #32.

## Row P's named questions

| Question | Finding |
|---|---|
| Pi runtime | OpenRig's adapter runs pi through its own runner as `pi --mode rpc` (`packages/daemon/src/adapters/pi-runtime-adapter.ts:1-10`), not the interactive pi herd drives. Moot with the verdict. |
| Shared-seat lifecycle | OpenRig adopts and restores seats itself; herd keeps its reuse and shutdown rules. The team design (§3) fixes how a shared slot changes role. |
| Independent QA | Not a daemon feature in either system; it is a role contract (team design §2). |
| Safe dogfood scheduling | OpenRig's `factory-rsi` dogfood guidance specifies ungated feedback; its workflow leaves the continuous runtime mechanism for later refinement. Herd requires an operator-authorized session (team design). |
| Single-harness resolution | OpenRig picks a prebuilt variant from `claude auth status` / `codex login status` (`kernel-boot.ts:139-176`); herd's setup (#39) asks per role. |
| Conditional preflight | OpenRig separates host health (`rig doctor`, `cli-reference.md:396`), a spec's requirements (`rig requirements <spec>`, `:474-483`, which probes what the rig's spec needs) and member preflight (`rigspec-preflight.ts:93-108`, the runtimes the spec selects). Herd's #38 matches the middle one: preflight derives its tools from the machine's bindings. OpenRig checks runtimes, not the exact provider, model and login; herd's readiness (#38) does. Single-harness and local-only machines are untested in both, from source reading alone. |
| Transport | OpenRig needs tmux; `--provider herdr` is display only. Herd stays on Herdr (#42). |
| Identity-safe fallback | Not addressed by OpenRig's variant selector; herd's rules are in the team design §5. |
| One controller | Herd keeps lifecycle ownership; queue-only reuse (option B) would not need a second controller, but adds the service above. |

## When to revisit

Revisit if herd ever needs to span several hosts (OpenRig has cross-host queue
routing, `cli-reference.md:1108`) or to run without Herdr, or if our ticket
tool grows toward OpenRig's size. Until then, copying contracts keeps the ticket
tool in Python and avoids operating a separate queue service.
