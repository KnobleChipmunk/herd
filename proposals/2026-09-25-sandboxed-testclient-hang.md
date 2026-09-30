# Proposal: sandboxed Starlette TestClient hang

Status: applied https://github.com/KnobleChipmunk/herd/pull/28 2026-09-26

## Class

sandboxed-testclient-hang — Starlette TestClient hangs under the sandbox

Events (friction ledger):
- 2026-09-25: "Sandboxed Starlette TestClient hung on the first local request; tracing and rerunning the touched suite outside the sandbox cost about 3 minutes."
- 2026-09-25: "Round 1 touched pytest run stalled inside Starlette TestClient in the sandbox; the same 186 tests finished in 7.91s outside it, wasting the round's diagnosis time."

## Proposed change

Change a tool in `~/projects/herd/tools`, not a skill paragraph: extend the
reviewer preflight (where the reviewer's touched-suite run is scripted) to
detect the repo's test stack and, for repos whose tests use Starlette/FastAPI
`TestClient`, record a known-good execution mode in the reviewer brief:
run the touched suite with a short per-run timeout (e.g. 60s), and on the first
block do exactly one escalated (non-sandbox) retry before diagnosing. This
makes the failure mode a scripted two-step instead of a per-round discovery.

## Prediction

No `sandboxed-testclient-hang` events in the next run's friction lines; the
reviewer brief for a TestClient repo carries the known-good execution mode and
the touched suite completes in the first escalated attempt.
2026-09-26: missed — five events in the #459 run (459-3b ~6 min, 459-3e ~5 min,
459-3f ~7 min, 459-3g ~4 min, 459-4 ~100 s hang); class now at 7 events.

## Grading
- 2026-09-27: held
- 2026-09-29: missed — #333 codex_review: the round's test client would hang in the sandbox; running pytest and both scratch mutations outside the sandbox on the first attempt (per the explicit prompt rule) avoided a diagnostic detour
- 2026-09-30: held
