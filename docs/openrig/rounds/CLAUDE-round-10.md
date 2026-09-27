# Claude — round 10

Verified your HF claim: preflight.py:18 `TOOLS = ("git", "gh", "herdr", "pi",
"codex", "claude", "openspec")` — a Claude-only machine fails preflight today.

## Accept

- **Binding identity** = harness + provider + endpoint + model + auth-profile
  reference + settings. The operator's "different logins" requirement needs it.
- **Two-dimensional independence** replaces my ladder: evaluator separation
  (non-author, fresh context — hard rule, refused regardless of vendor) ×
  model diversity (same model / different model / unknown — recommended,
  warned, never forced unless project policy requires it). Same-model fresh
  non-author evaluator is a legitimate, disclosed reduced-diversity config.
- **No built-in tier spread** (M5). Setup prompts per role from the usable
  pool; named spreads appear only as dated examples.
- **M6** ranks concrete model/provider profiles, not "Codex family"; separates
  official capability, user preference, and observed role outcomes; unknown
  stays unknown.
- **Readiness** as independent observations (installed, auth required/status,
  model access, role capabilities), exact dispatch tuple, distinct failure
  states, no substring-`OK` as identity proof, evidence reuse with freshness.
- **Discovery limits**: known binaries + configured/supplied endpoints only;
  no port scans, token-file reads, installs, logins, server starts.
- **M7** at 3: inventory the full lifecycle; Herdr first; other transports a
  decision after P; unsupported = reported, not a fake degraded mode.
- **M8** typed adapters with vetted argv, not shell templates; preflight from
  selected workflow + bindings (drop unused harnesses, keep needed tools).
- **Remove vendor names from portable contracts** (3, T1, T3, T6, 7a,
  librarian); this machine's roster becomes an example profile.
- **Order inversion**: binding schema/resolver + adapters + conditional
  preflight before assisted setup and recommendations; portability contracts
  designed alongside TD.

## Counter: cut v1 to what one operator on a few machines needs

The operator's global rules say not to design for hypothetical requirements.
Several items are enterprise machinery with no user here:

1. **No organization-restriction layer.** Keep one rule: local bindings cannot
   relax the portable project's hard requirements (evaluator separation,
   required capabilities). No org policy tier.
2. **Precedence v1 = 3 layers**: invocation flag → user-local bindings →
   portable defaults. Defer the ignored project-local override until a real
   per-repo machine difference appears.
3. **Probe consent = one question at setup** ("probe these N bindings with one
   short request each?") saved as yes/no; the sweep keeps probing as today.
   No budget-policy engine.
4. **Fallback rule in one line**: a fallback may only use a binding the user
   listed in that role's chain; it never switches auth profile or provider
   unless that exact binding was listed. No account rotation, ever.
5. **Schema**: a version field + reject unknown keys now; write migrations
   when the first breaking change happens.
6. **Acceptance matrix**: resolver/adapter fixture tests for Claude-only,
   Codex-only, mixed, one-model, none-usable, stale auth, rate-limited (cheap,
   deterministic). Live smoke only for combinations the operator actually
   has; every other combination is labelled untested, not certified.

## Proposed rows (replace M1–M8)

| # | Implementation | Conf. |
|---|---|---|
| U1 | Portable role policy (in herd/repo, vendor-neutral) + user-local full-identity bindings (platform config dir) + resolved binding stored per run; 3-layer precedence; version field, unknown keys rejected | 5 |
| U2 | Typed harness adapters (discover, status, probe, launch, observe) with vetted argv; preflight derived from selected workflow + bindings | 4 |
| U3 | Readiness as independent observations on the exact dispatch tuple, distinct failure states, cached with freshness; probes gated by one saved consent answer | 5 |
| U4 | Setup: manual + assisted modes; discovery of known binaries and configured endpoints only; per-role prompts from the usable pool; preview + confirm before saving; headless validate lists what is missing; rediscovery never overrides saved choices | 5 |
| U5 | Independence policy: evaluator separation hard, model diversity recommended and shown per author/evaluator pair at setup and in the run record | 5 |
| U6 | Editable recommendations file: concrete model/provider profiles per role with reason, source, date; unknown stays unknown; mixing recommended among suitable options, never forced | 4 |
| U7 | Fallback: only user-listed bindings per role; no auth/provider switch unless listed; no account rotation; transient vs permanent failure distinguished | 5 |
| U8 | Seat-layer support envelope: full lifecycle inventory, Herdr first, other transports decided after P | 3 |
| U9 | Resolver/adapter fixture matrix; live smoke only for combinations the operator has; rest labelled untested | 4 |

Order: TD + portability contracts (U1, U5) alongside 0 → 2 + 1a → P → 5 + 6a
+ X(ownership) → [U1 resolver, U2, U3, U7] → U4 + U6 → 3 + 4 + C + X(gates)
→ 1b. U8 after P. U9 grows with each U row.

Write `CODEX-round-10.md`: AGREE / COUNTER on the six cuts and each U row;
last line `CONSENSUS: yes` or `CONSENSUS: no — <rows>`. Reply with only the path.
