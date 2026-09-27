# Bindings resolver, adapters, readiness and fallback (#38)

## Why

Roadmap step 4 (rows U1, U2, U3, U7, U9) and the team design §5
(`docs/team-design.md`, PR #48). Herd hard-codes its harnesses:
`tools/preflight.py:18` requires `pi`, `codex` and `claude` on every machine,
and `tools/probe.py` reads models from the skill's Roster table with three
hard-coded command shapes (its pi probe omits the provider the launch uses).

## What changes

- New `tools/bindings.py`:
  - **Schema (U1):** a machine-local YAML file (`$XDG_CONFIG_HOME/herd/bindings.yaml`,
    else `~/.config/herd/bindings.yaml`): `version: 1`, optional
    `probe_consent`, and `roles:` (lead, builder, plan_reviewer, build_reviewer,
    qa, dogfood, designer, librarian). A binding: harness, provider, endpoint,
    model, auth_profile (a reference), settings, and an ordered fallback list of
    bindings. Unknown keys, unknown roles, unsupported harnesses and
    unsupported versions are rejected with a reason.
  - **Precedence:** invocation flag, then the user file, then portable defaults.
  - **Adapters (U2):** one vetted argument shape per harness (claude, codex,
    pi) for the status check, the probe, and the launch arguments; the probe
    uses the exact tuple the launch will use.
  - **Readiness (U3):** installed; auth (ok, needs-login, not-required for a
    local provider); usable (ok, rate-limited, model-denied, unreachable,
    unknown, not-probed). A timeout is unknown; a reply is not proof of the
    model. Probes run only with `probe_consent: true`. Results are cached per
    exact tuple for 6 hours in `<git common dir>/herd/readiness.json`.
  - **Fallback (U7):** the first usable binding in the role's own chain, with
    a transient/permanent label for each one passed over; nothing unlisted.
  - **Diversity (U5):** same/different/unknown per author/evaluator pair,
    warned by `bindings.py check`.
- `tools/preflight.py` derives its tool list from the bindings file when one
  exists (`--bindings` or the user file): base tools plus the primary harness
  of each selected role (`--roles`, default the four loop roles); fallbacks
  and inactive roles are not prerequisites. A named file that does not exist
  is an error. Without a user file it keeps today's list.
- Plan review round 1 (5 findings; 2 narrowed by lead ruling): adapters reject
  identity fields they cannot honor yet (endpoint, auth_profile; provider for
  claude/codex; settings other than codex `reasoning_effort`); `probe_consent`
  must be a Boolean; a status timeout or an unrecognized status failure is
  `unknown` (only login wording is `needs-login`); a probe is usable only when
  its last line is exactly `OK`; a result cached without consent never stands
  in for a consented probe; `ready` takes `--harness/--model` as an invocation
  override and `--record` writes the chosen binding to the run log;
  `requirements.txt` declares PyYAML.
- Plan review round 2 (5 findings): the sweep's Probe step uses `bindings.py
  ready --record` whenever a bindings file exists (probe.py only without one,
  until #51); `--record` writes the full chosen binding as JSON and fails when
  the run log refuses it; pi's auth is `not-required` only for the local
  `ollama` provider; an override needs both `--harness` and `--model`, and an
  unknown role is refused before any probe; wrong field types, a Boolean
  version and malformed YAML are diagnosed, never crashed on.
- `skill/profiles/example-claude-codex-pi.yaml`: this machine's roster as an
  example profile.
- `skill/SKILL.md` sweep: the bindings file and `bindings.py ready`.

## Grounded facts

- `tools/preflight.py:18`: `TOOLS = ("git", "gh", "herdr", "pi", "codex", "claude", "openspec")`.
- `tools/probe.py:53-60`: probe commands for Codex, Claude Code and pi; the pi
  one has no `--provider`, while the skill launches pi with `--provider ollama`.
- `codex login status` prints `Logged in using ChatGPT` and exits 0; `claude
  auth status` prints JSON and exits 0 (both run live, 2026-09-27).
- Live probes on 2026-09-27 through `bindings.py ready`: `codex exec -m
  gpt-6-sol -c model_reasoning_effort=high` → ok; `pi --provider ollama --model
  swift15-qwen3.8-128k:latest -p` → ok.
- PyYAML 6.0.1 is installed on this machine and not declared by herd; it is
  imported lazily, and a missing PyYAML fails with the package name.

## Non-goals

- `probe.py` and the Roster table stay until #40 moves the skill to role
  cards and `herd.yaml`; this change does not remove them.
- No `herd setup` (#39) and no recommendations file (#39).
- No live smoke of single-harness machines (untested; fixtures only).
- Evaluator separation is a session rule, checked when roles are dispatched,
  not in this file.

## Impact

New `tools/bindings.py`, `tests/test_bindings.py`,
`skill/profiles/example-claude-codex-pi.yaml`; edits to `tools/preflight.py`,
`skill/SKILL.md`, `tests/test_skill_text.py`, `pyproject.toml`. Stacked on
`feat/36-tickets`.
