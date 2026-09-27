# herd setup and the model recommendations file (#39)

## Why

Roadmap step 5 (rows U4, U6) and the operator's portability request: a
machine with only Claude, only Codex, or another mix must be able to bind each
role, be prompted per role, and be encouraged toward different models for an
author and its evaluator, without hard-coded vendor claims. #38 gives the
bindings file; nothing yet writes one.

## What changes

- New `tools/herdsetup.py`:
  - `assisted`: discovers only the supported harness binaries on PATH (no port
    scans, token files, installs, logins or servers), asks per required role
    (lead, builder, plan_reviewer, build_reviewer) offering recommendations
    limited to what is installed, accepts a number or `<harness> <model>
    [provider=<p>] [effort=<e>]`,
    re-asks on an unusable answer, keeps a saved choice as the default (Enter),
    warns per author/evaluator pair on a same-model choice, asks the probe
    consent question naming its cost, shows a preview, and saves only on "y"
    (atomic write).
  - `validate`: no prompts; lists a missing file, an invalid file, unbound
    required roles and uninstalled harnesses; exit 1 if anything is missing.
  - `from-example`: copies `skill/profiles/example-claude-codex-pi.yaml` after
    "y", never over an existing file.
- New `skill/recommendations.yaml`: per role, concrete harness/model entries,
  each with a reason, a source type (`official`, `preference`, `observed`) and a
  date; entries older than 180 days are flagged stale; roles may be absent.
- Plan review round 1 (5 findings; F1 narrowed by lead ruling): a typed answer
  may carry `provider=` and `effort=`, validated by #38 (endpoints are
  discovered only once an adapter accepts one; #38 rejects `endpoint` today);
  recommendations are validated on load and an invalid entry is left out with
  its reason; the finished document is validated before the save question; a
  machine with no supported harness ends without prompting and writes nothing
  when a required role is unbound;
  the selected bindings and every author/evaluator pair's diversity (same,
  different, unknown) are shown before the consent question; a role with no
  recommendation says so; the build-review citation now names
  KnobleChipmunk/project-mera#321.
- `skill/SKILL.md` sweep names `herdsetup.py`.

## Grounded facts

- `tools/bindings.py` (#38): `ADAPTERS`, `ROLES`, `BINDING_KEYS`, `VERSION`,
  `load`, `diversity`, `user_path`.
- Observed outcomes cited in the recommendations: #32 and #33 built
  byte-identical by pi (this run); the plan reviewer's catches on #32/#33 (this
  run's PLAN-REVIEW files); #321's one-round clean reviews (SKILL.md).
- Live: `herdsetup.py validate --file skill/profiles/example-claude-codex-pi.yaml`
  → `ok` on this machine (2026-09-27).

## Non-goals

- No automatic model enumeration from providers; the user types a model when
  no recommendation fits.
- No probing during setup (readiness is `bindings.py ready`, gated by consent).
- No new roles beyond the four required; optional roles (qa, designer, dogfood,
  librarian) are edited by hand until #40's role cards use them.

## Impact

New `tools/herdsetup.py`, `tests/test_setup.py`, `skill/recommendations.yaml`;
edits to `skill/SKILL.md`, `tests/test_skill_text.py`, `pyproject.toml`.
Stacked on `feat/38-bindings`.
