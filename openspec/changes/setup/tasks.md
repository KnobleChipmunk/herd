# Tasks — herd setup (#39)

Tier: **full**. DEPENDS ON #38: the branch is stacked on `feat/38-bindings`.
Fences are generated from the lead's pre-executed tree; `tools/fencecheck.py` must print `FENCES OK (6 steps)`.

## 1. Tests first — apply T1, T2, then observe RED

- [ ] **T1** `tests/test_setup.py` — acceptance tests for assisted setup, validation and recommendations

Create this file with exactly this body (byte-exact, ends with one newline):

```python
import datetime

import pytest
import yaml

import bindings
import herdsetup as setup

TODAY = datetime.date(2026, 9, 27)
RECS = {"version": 1, "roles": {
    "builder": [{"harness": "pi", "provider": "ollama", "model": "swift15-qwen3.8-128k:latest",
                 "reason": "local, no quota", "source": "observed", "date": "2026-09-27"},
                {"harness": "claude", "model": "sonnet", "reason": "reliable edits", "source": "preference",
                 "date": "2026-09-27"}],
    "build_reviewer": [{"harness": "codex", "model": "gpt-6-sol", "reason": "one-round clean reviews",
                        "source": "observed", "date": "2026-08-25"},
                       {"harness": "claude", "model": "fable", "reason": "a model other than the builder's",
                        "source": "preference", "date": "2026-09-27"}]}}


def only(*harnesses):
    return lambda binary: f"/bin/{binary}" if binary in harnesses else None


def scripted(*answers):
    """An input() that returns the scripted answers in order and records every prompt."""
    it = iter(answers)
    prompts = []

    def ask(prompt):
        prompts.append(prompt)
        return next(it)

    ask.prompts = prompts
    return ask


# --- discovery ----------------------------------------------------------------

def test_discovery_finds_only_installed_supported_harnesses():
    assert setup.discover(only("claude")) == ["claude"]
    assert setup.discover(only("claude", "codex", "pi")) == ["claude", "codex", "pi"]
    assert setup.discover(only()) == []


# --- recommendations (U6) -------------------------------------------------------

def test_the_shipped_recommendations_file_is_valid():
    assert setup.validate_recommendations(setup.load_recommendations()) == []


@pytest.mark.parametrize("entry, error", [
    ({"harness": "claude", "model": "x", "source": "observed", "date": "2026-09-27"}, "missing reason"),
    ({"harness": "claude", "model": "x", "reason": "r", "source": "benchmark", "date": "2026-09-27"},
     "source must be one of official, preference, observed"),
    ({"harness": "claude", "model": "x", "reason": "r", "source": "observed"}, "missing date"),
])
def test_every_recommendation_needs_a_reason_a_source_type_and_a_date(entry, error):
    errors = setup.validate_recommendations({"version": 1, "roles": {"builder": [entry]}})
    assert any(error in e for e in errors)


def test_recommendations_are_limited_to_the_usable_pool_and_flag_stale_ones():
    offers = setup.offers("build_reviewer", RECS, ["claude"], today=TODAY, stale_days=30)
    assert [(o["harness"], o["model"]) for o in offers] == [("claude", "fable")]
    stale = setup.offers("build_reviewer", RECS, ["codex"], today=TODAY, stale_days=30)
    assert stale[0]["stale"] is True
    assert setup.offers("designer", RECS, ["claude"], today=TODAY) == []


# --- assisted setup (U4) --------------------------------------------------------

def test_a_claude_only_machine_is_asked_per_role_and_warned_about_same_models(capsys):
    ask = scripted("claude opus", "1", "claude sonnet", "claude sonnet", "n", "y")
    doc = setup.assisted(RECS, which=only("claude"), existing=None, ask=ask, today=TODAY)
    out = capsys.readouterr().out
    assert [p.split(":")[0] for p in ask.prompts[:4]] == ["lead", "builder", "plan_reviewer", "build_reviewer"]
    assert {b["harness"] for b in doc["roles"].values()} == {"claude"}
    assert doc["roles"]["builder"] == {"harness": "claude", "model": "sonnet"}
    assert "WARNING builder -> build_reviewer: same model (sonnet)" in out
    assert doc["probe_consent"] is False
    assert bindings.validate(doc) == []


def test_the_consent_question_names_its_cost():
    ask = scripted("claude opus", "claude sonnet", "claude fable", "claude fable", "y", "y")
    doc = setup.assisted(RECS, which=only("claude"), existing=None, ask=ask, today=TODAY)
    consent = ask.prompts[4]
    assert "one short diagnostic request per selected binding" in consent and "quota" in consent
    assert doc["probe_consent"] is True


def test_nothing_is_saved_without_confirmation(tmp_path, capsys):
    target = tmp_path / "bindings.yaml"
    ask = scripted("claude opus", "claude sonnet", "claude fable", "claude fable", "n", "n")
    assert setup.run_assisted(RECS, target, which=only("claude"), ask=ask, today=TODAY) == 1
    assert not target.exists()
    assert "version: 1" in capsys.readouterr().out  # the preview was shown


def test_a_confirmed_setup_is_written_and_reloads(tmp_path):
    target = tmp_path / "herd" / "bindings.yaml"
    ask = scripted("claude opus", "claude sonnet", "claude fable", "claude fable", "n", "y")
    assert setup.run_assisted(RECS, target, which=only("claude"), ask=ask, today=TODAY) == 0
    assert bindings.load(target)["roles"]["lead"] == {"harness": "claude", "model": "opus"}


def test_a_saved_choice_is_the_default_and_rediscovery_never_overrides_it(tmp_path):
    target = tmp_path / "bindings.yaml"
    target.write_text(yaml.safe_dump({"version": 1, "roles": {"builder": {"harness": "pi", "provider": "ollama",
                                                                          "model": "saved-model"}}}))
    ask = scripted("claude opus", "", "claude fable", "claude fable", "n", "y")
    setup.run_assisted(RECS, target, which=only("claude", "pi"), ask=ask, today=TODAY)
    assert "[saved: pi saved-model]" in ask.prompts[1]
    assert bindings.load(target)["roles"]["builder"] == {"harness": "pi", "provider": "ollama", "model": "saved-model"}


def test_an_unusable_answer_is_asked_again():
    ask = scripted("codex gpt-6-sol", "claude opus", "claude sonnet", "claude fable", "claude fable", "n", "y")
    doc = setup.assisted(RECS, which=only("claude"), existing=None, ask=ask, today=TODAY)
    assert ask.prompts[1].startswith("lead") and doc["roles"]["lead"]["model"] == "opus"


# --- headless validation ----------------------------------------------------------

def test_validate_lists_what_is_missing_without_prompting(tmp_path, capsys):
    target = tmp_path / "bindings.yaml"
    assert setup.validate_machine(target, which=only("claude")) == 1
    assert "no bindings file" in capsys.readouterr().out
    target.write_text(yaml.safe_dump({"version": 1, "roles": {
        "lead": {"harness": "claude", "model": "opus"}, "builder": {"harness": "pi", "model": "m"}}}))
    assert setup.validate_machine(target, which=only("claude")) == 1
    out = capsys.readouterr().out
    assert "builder: pi is not installed" in out
    assert "plan_reviewer: not bound" in out and "build_reviewer: not bound" in out


def test_a_complete_machine_validates(tmp_path, capsys):
    target = tmp_path / "bindings.yaml"
    target.write_text(yaml.safe_dump({"version": 1, "roles": {
        r: {"harness": "claude", "model": m} for r, m in
        (("lead", "opus"), ("builder", "sonnet"), ("plan_reviewer", "fable"), ("build_reviewer", "fable"))}}))
    assert setup.validate_machine(target, which=only("claude")) == 0
    assert "ok" in capsys.readouterr().out


def test_from_example_copies_the_profile_only_after_confirmation(tmp_path):
    target = tmp_path / "bindings.yaml"
    assert setup.from_example(target, ask=scripted("n")) == 1 and not target.exists()
    assert setup.from_example(target, ask=scripted("y")) == 0
    assert bindings.load(target)["roles"]["builder"]["harness"] == "pi"
    assert setup.from_example(target, ask=scripted("y")) == 1  # never overwrites an existing file


# --- plan review #39 round 1 -------------------------------------------------

def test_a_local_only_machine_can_bind_every_role_with_a_custom_model(tmp_path):
    ask = scripted("pi m1 provider=ollama", "pi m2 provider=ollama", "pi m3 provider=ollama", "pi m4 provider=ollama",
                   "n", "y")
    target = tmp_path / "b.yaml"
    assert setup.run_assisted(RECS, target, which=only("pi"), ask=ask, today=TODAY) == 0
    roles = bindings.load(target)["roles"]
    assert roles["lead"] == {"harness": "pi", "model": "m1", "provider": "ollama"}
    assert roles["build_reviewer"]["model"] == "m4"


def test_a_typed_field_the_adapter_cannot_honor_is_asked_again(capsys):
    ask = scripted("claude opus provider=bedrock", "claude opus", "claude sonnet", "claude fable", "claude fable", "n")
    doc = setup.assisted(RECS, which=only("claude"), existing=None, ask=ask, today=TODAY)
    assert doc["roles"]["lead"] == {"harness": "claude", "model": "opus"}
    assert "does not support provider" in capsys.readouterr().out


def test_an_invalid_recommendation_is_left_out_with_a_reason(capsys):
    recs = {"version": 1, "roles": {"lead": [
        {"harness": "codex", "model": "x", "endpoint": "http://localhost:9999", "reason": "r", "source": "observed",
         "date": "2026-09-27"},
        {"harness": "codex", "model": "y", "reason": "r", "source": "observed", "date": "2026-09-27"}]}}
    ask = scripted("1", "codex a", "codex b", "codex c", "n")
    doc = setup.assisted(recs, which=only("codex"), existing=None, ask=ask, today=TODAY)
    assert doc["roles"]["lead"] == {"harness": "codex", "model": "y"}
    assert "recommendation lead 1 left out" in capsys.readouterr().out


def test_a_machine_with_no_supported_harness_ends_without_prompting(tmp_path, capsys):
    def never(prompt):
        raise AssertionError(f"prompted: {prompt}")
    target = tmp_path / "b.yaml"
    assert setup.run_assisted(RECS, target, which=only(), ask=never, today=TODAY) == 1
    assert not target.exists() and "no supported harness" in capsys.readouterr().out


def test_every_pairs_diversity_is_shown_before_the_consent_question(capsys):
    answers = iter(["claude opus", "claude sonnet", "claude fable", "claude fable", "n"])
    at_consent = {}

    def ask(prompt):
        if prompt == setup.CONSENT:
            at_consent["out"] = capsys.readouterr().out  # what was shown BEFORE the question
        return next(answers)

    setup.assisted(RECS, which=only("claude"), existing=None, ask=ask, today=TODAY)
    out = at_consent["out"]
    assert "builder -> build_reviewer: different model" in out
    assert "lead -> plan_reviewer: different model" in out
    assert "builder -> qa: unknown model" in out
    assert "selected:" in out and "lead: claude opus" in out


@pytest.mark.parametrize("doc", [None, [], {"version": 1, "roles": []}, {"version": 1, "roles": {"lead": {}}},
                                 {"version": 1, "roles": {"lead": ["x"]}},
                                 {"version": 1, "roles": {"lead": [{"harness": ["codex"], "model": "m"}]}}])
def test_a_malformed_recommendations_document_is_diagnosed_not_crashed_on(doc):
    assert setup.validate_recommendations(doc)


def test_malformed_recommendation_yaml_is_ignored_with_a_reason(tmp_path, capsys):
    f = tmp_path / "r.yaml"
    f.write_text("roles: [\n")
    recs = setup.load_recommendations(f)
    assert recs == {"version": 1, "roles": {}} and "is not valid YAML" in capsys.readouterr().out


def test_a_role_left_empty_in_the_recommendations_still_allows_typed_setup(capsys):
    recs = {"version": 1, "roles": {"lead": None}}
    assert setup.validate_recommendations(recs) == []
    ask = scripted("claude opus", "claude sonnet", "claude fable", "claude fable", "n")
    doc = setup.assisted(recs, which=only("claude"), existing=None, ask=ask, today=TODAY)
    assert doc["roles"]["lead"] == {"harness": "claude", "model": "opus"}
    assert "lead: no recommendation for the installed harnesses (unknown)" in capsys.readouterr().out

```

- [ ] **T2** `tests/test_skill_text.py` — the sweep names herd setup

Append exactly this text at the END of the file. The fence below BEGINS with the blank lines that separate it from the existing last line — keep them. The file must end with one newline:

```python


def test_the_sweep_names_herd_setup():
    text = " ".join(SKILL.read_text().split())
    sweep = text[text.index("3. **Preflight.**"): text.index("4. **Decisions.**")]
    assert "herdsetup.py assisted" in sweep and "herdsetup.py validate" in sweep and "from-example" in sweep

```

RED after T1–T2: `tests/test_setup.py` fails to collect (no module `herdsetup`); the new skill-text test fails.

## 2. Implementation — apply I1–I4

- [ ] **I1** `pyproject.toml` — register the new module for isort

Find this exact text (it occurs exactly once):

```python
"herdtool", "librarian",
```

Replace it with exactly:

```python
"herdsetup", "herdtool", "librarian",
```

- [ ] **I2** `skill/recommendations.yaml` — per-role recommendations with provenance

Create this file with exactly this body (byte-exact, ends with one newline):

```python
# Model recommendations per role, read by `herdsetup.py assisted` (#39).
# Each entry says why, what kind of evidence it rests on, and when it was
# written: `official` (vendor documentation), `preference` (the operator's
# choice), `observed` (a herd run's outcome, cited). Setup offers only entries
# whose harness is installed, flags entries older than 180 days, and never
# forces a choice; mixing models across an author and its evaluator is the
# recommendation (docs/team-design.md §4). Unknown is fine: leave a role out.
version: 1
roles:
  lead:
    - {harness: claude, model: claude-opus-5-5, source: preference, date: "2026-09-25",
       reason: "writes and pre-executes specs; the operator's lead since 2026-09-25"}
  builder:
    - {harness: pi, provider: ollama, model: "swift15-qwen3.8-128k:latest", source: observed, date: "2026-09-27",
       reason: "built herd #32 and #33 byte-identical to the lead's fences, local, no quota"}
    - {harness: claude, model: sonnet, source: preference, date: "2026-09-27",
       reason: "a hosted builder for machines without a local model"}
  plan_reviewer:
    - {harness: codex, model: gpt-6-astra, settings: {reasoning_effort: high}, source: observed, date: "2026-09-27",
       reason: "found the #32 lock race and the #33 wait/tab defects the lead missed"}
    - {harness: claude, model: fable, source: preference, date: "2026-09-27",
       reason: "a reviewer model other than an Opus lead's, when Codex is absent"}
  build_reviewer:
    - {harness: codex, model: gpt-6-sol, settings: {reasoning_effort: high}, source: preference, date: "2026-09-27",
       reason: "the operator's build reviewer; one-round clean reviews came with lead pre-execution (KnobleChipmunk/project-mera#321, PRs #377/#378, 2026-08-25)"}
    - {harness: claude, model: fable, source: preference, date: "2026-09-27",
       reason: "a model other than the builder's, when Codex is absent"}
  qa:
    - {harness: codex, model: gpt-6-sol, settings: {reasoning_effort: high}, source: preference, date: "2026-09-27",
       reason: "a model other than the builder's for independent executed checks (team design T1)"}
```

- [ ] **I3** `tools/herdsetup.py` — assisted setup, headless validation, from-example

Create this file with exactly this body (byte-exact, ends with one newline):

```python
"""Set up this machine's bindings: manual, assisted, or checked headless (#39).

usage: herdsetup.py assisted     [--file PATH]   ask per role from the installed pool; preview; save on "y"
       herdsetup.py validate     [--file PATH]   no prompts: list what is missing; exit 1 if anything is
       herdsetup.py from-example [--file PATH]   copy skill/profiles/example-claude-codex-pi.yaml, after "y"

Manual mode is editing the file yourself; `validate` checks it. Discovery looks
only for the supported harness binaries on PATH: no port scans, no token files,
no installs, no logins, no servers started. A saved choice is the default and
rediscovery never overrides it. Nothing is written without confirmation, and
an existing file is never overwritten by `from-example`.
"""
from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import shutil
import sys

import bindings

HERE = pathlib.Path(__file__).resolve().parent.parent
RECOMMENDATIONS = HERE / "skill" / "recommendations.yaml"
EXAMPLE = HERE / "skill" / "profiles" / "example-claude-codex-pi.yaml"
REQUIRED_ROLES = ("lead", "builder", "plan_reviewer", "build_reviewer")
SOURCES = ("official", "preference", "observed")
STALE_DAYS = 180
CONSENT = ("Allow one short diagnostic request per selected binding during setup and future preflight checks? "
           "These may consume quota or incur charges. [y/N] ")


def _yaml():
    try:
        import yaml
    except ImportError as exc:
        raise bindings.BindingsError("herd setup needs PyYAML: pip install pyyaml") from exc
    return yaml


def discover(which=shutil.which) -> list[str]:
    """The supported harnesses whose binary is on PATH; nothing else is looked at."""
    return sorted(h for h, a in bindings.ADAPTERS.items() if which(a["binary"]))


def load_recommendations(path: pathlib.Path = RECOMMENDATIONS):
    """The recommendations document; malformed YAML is reported and treated as no recommendations."""
    yaml = _yaml()
    try:
        return yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        print(f"recommendations ignored: {path} is not valid YAML ({exc})")
        return {"version": 1, "roles": {}}


def validate_recommendations(doc) -> list[str]:
    if not isinstance(doc, dict):
        return ["the recommendations file must be a mapping"]
    errors = [] if doc.get("version") == 1 and type(doc.get("version")) is int else ["unsupported or missing version"]
    roles = {} if doc.get("roles") is None else doc["roles"]
    if not isinstance(roles, dict):
        return errors + ["roles must be a mapping"]
    for role, entries in roles.items():
        if role not in bindings.ROLES:
            errors.append(f"unknown role '{role}'")
        entries = [] if entries is None else entries
        if not isinstance(entries, list):
            errors.append(f"{role}: entries must be a list")
            continue
        for n, e in enumerate(entries, 1):
            where = f"{role} {n}"
            if not isinstance(e, dict):
                errors.append(f"{where}: an entry must be a mapping")
                continue
            if not isinstance(e.get("harness"), str) or e["harness"] not in bindings.ADAPTERS or not e.get("model"):
                errors.append(f"{where}: needs a supported harness and a model")
            if not e.get("reason"):
                errors.append(f"{where}: missing reason")
            if e.get("source") not in SOURCES:
                errors.append(f"{where}: source must be one of {', '.join(SOURCES)}")
            if not e.get("date"):
                errors.append(f"{where}: missing date")
            else:
                try:
                    datetime.date.fromisoformat(str(e["date"]))
                except ValueError:
                    errors.append(f"{where}: date must be YYYY-MM-DD")
    return errors


def offers(role: str, recs: dict, pool: list[str], *, today: datetime.date, stale_days: int = STALE_DAYS) -> list[dict]:
    out = []
    for e in (recs.get("roles") or {}).get(role) or []:  # a role left empty (`lead:`) has no recommendations
        if e["harness"] in pool:
            age = (today - datetime.date.fromisoformat(str(e["date"]))).days
            out.append({**e, "stale": age > stale_days})
    return out


def binding_of(entry: dict) -> dict:
    return {k: entry[k] for k in bindings.BINDING_KEYS if k in entry and k != "fallback"}


def binding_problems(role: str, b: dict) -> list[str]:
    """#38's validation of one binding for one role."""
    return bindings.validate({"version": bindings.VERSION, "roles": {role: b}})


def usable_offers(role: str, recs: dict, pool: list[str], *, today: datetime.date) -> list[dict]:
    """Offers whose binding #38 accepts; an invalid entry is left out, with a visible reason."""
    out = []
    for n, o in enumerate(offers(role, recs, pool, today=today), 1):
        problems = binding_problems(role, binding_of(o))
        if problems:
            print(f"  (recommendation {role} {n} left out: {'; '.join(problems)})")
        else:
            out.append(o)
    return out


def parse_answer(answer: str) -> dict | None:
    """`<harness> <model> [provider=<p>] [effort=<e>]` -> a binding, or None."""
    parts = answer.split()
    if len(parts) < 2:
        return None
    b = {"harness": parts[0], "model": parts[1]}
    for extra in parts[2:]:
        key, sep, value = extra.partition("=")
        if not sep or not value or key not in ("provider", "effort"):
            return None
        if key == "provider":
            b["provider"] = value
        else:
            b["settings"] = {"reasoning_effort": value}
    return b


def describe(b: dict) -> str:
    return f"{b['harness']} {b['model']}"


def assisted(recs: dict, *, which=shutil.which, existing: dict | None, ask=input,
             today: datetime.date) -> dict | None:
    """Ask for each required role; return the bindings document (not yet saved)."""
    pool = discover(which)
    saved = (existing or {}).get("roles", {})
    roles = dict(saved)
    print(f"installed harnesses on this machine: {', '.join(pool) or 'none'} (installed is not proof of access)")
    if not pool and any(r not in saved for r in REQUIRED_ROLES):
        print("no supported harness (claude, codex, pi) is installed: install one, then run setup again")
        return None
    rec_errors = validate_recommendations(recs)
    if rec_errors:
        print("recommendations ignored: " + "; ".join(rec_errors))
        recs = {"version": 1, "roles": {}}
    for role in REQUIRED_ROLES:
        choices = usable_offers(role, recs, pool, today=today)
        if not choices:
            print(f"  {role}: no recommendation for the installed harnesses (unknown)")
        for n, o in enumerate(choices, 1):
            print(f"  {n}. {describe(o)} — {o['reason']} ({o['source']}, {o['date']}{', STALE' if o['stale'] else ''})")
        hint = f" [saved: {describe(saved[role])}]" if role in saved else ""
        while True:
            answer = ask(f"{role}: pick a number or type '<harness> <model> [provider=<p>] [effort=<e>]'{hint} > ").strip()
            if not answer and role in saved:
                break
            if answer.isdigit() and 1 <= int(answer) <= len(choices):
                roles[role] = binding_of(choices[int(answer) - 1])
                break
            typed = parse_answer(answer)
            if typed and typed["harness"] in pool and not binding_problems(role, typed):
                roles[role] = typed
                break
            why = "; ".join(binding_problems(role, typed)) if typed and typed["harness"] in pool else \
                f"installed: {', '.join(pool) or 'none'}"
            print(f"  not usable here: '{answer}' ({why})")
    print("selected:")
    for role in REQUIRED_ROLES:
        if role in roles:
            print(f"  {role}: {describe(roles[role])}" + "".join(f" {k}={v}" for k, v in roles[role].items()
                                                             if k not in ("harness", "model")))
    for author, evaluator, kind in bindings.diversity(roles):
        if kind == "same":
            print(f"WARNING {author} -> {evaluator}: same model ({roles[author]['model']}); a fresh session is "
                  f"still an independent evaluator, but a different model is recommended")
        else:
            print(f"  {author} -> {evaluator}: {kind} model")
    consent = ask(CONSENT).strip().lower() == "y"
    return {"version": bindings.VERSION, "probe_consent": consent, "roles": roles}


def write(target: pathlib.Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(text)
    os.replace(tmp, target)


def run_assisted(recs: dict, target: pathlib.Path, *, which=shutil.which, ask=input, today: datetime.date) -> int:
    existing = bindings.load(target) if target.exists() else None
    doc = assisted(recs, which=which, existing=existing, ask=ask, today=today)
    if doc is None:
        return 1
    problems = bindings.validate(doc)
    if problems:
        print("not saved: " + "; ".join(problems))
        return 1
    text = _yaml().safe_dump(doc, sort_keys=False)
    print(f"--- preview of {target}\n{text}---")
    if ask(f"Save to {target}? [y/N] ").strip().lower() != "y":
        print("not saved")
        return 1
    write(target, text)
    print(f"saved {target}")
    return 0


def validate_machine(target: pathlib.Path, *, which=shutil.which) -> int:
    if not target.exists():
        print(f"no bindings file at {target}: run `herdsetup.py assisted` or `from-example`")
        return 1
    try:
        doc = bindings.load(target)
    except bindings.BindingsError as exc:
        print(f"invalid {target}: {exc}")
        return 1
    roles, problems = doc.get("roles", {}), []
    for role in REQUIRED_ROLES:
        if role not in roles:
            problems.append(f"{role}: not bound")
        elif not which(bindings.ADAPTERS[roles[role]["harness"]]["binary"]):
            problems.append(f"{role}: {roles[role]['harness']} is not installed")
    for line in problems:
        print(line)
    for author, evaluator, kind in bindings.diversity(roles):
        if kind == "same":
            print(f"WARNING {author} -> {evaluator}: same model ({roles[author]['model']})")
    if not problems:
        print(f"ok: {target}")
    return 1 if problems else 0


def from_example(target: pathlib.Path, *, ask=input) -> int:
    if target.exists():
        print(f"{target} exists; not overwriting it")
        return 1
    print(f"--- {EXAMPLE}\n{EXAMPLE.read_text()}---")
    if ask(f"Copy this example profile to {target}? [y/N] ").strip().lower() != "y":
        print("not copied")
        return 1
    write(target, EXAMPLE.read_text())
    print(f"saved {target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("assisted", "validate", "from-example"))
    ap.add_argument("--file")
    a = ap.parse_args(argv)
    target = pathlib.Path(a.file) if a.file else bindings.user_path()
    if a.cmd == "validate":
        return validate_machine(target)
    if a.cmd == "from-example":
        return from_example(target)
    return run_assisted(load_recommendations(), target, today=datetime.date.today())


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **I4** `skill/SKILL.md` — the sweep names herd setup

Find this exact text (it occurs exactly once):

```python
   until #51 (#38).
```

Replace it with exactly:

```python
   until #51 (#38).
   A new machine gets its file from `python3 <herd>/tools/herdsetup.py
   assisted` (asks per role from what is installed; saves only on "y") or
   `from-example`; `herdsetup.py validate` lists what is missing without
   prompting (#39).
```

## 3. Gates

- Full suite at the base (`feat/38-bindings` after its build): `401 passed`. After: `430 passed` (28 in `tests/test_setup.py` with parametrized cases, 1 new skill-text test). ~8 s.
- `ruff check tools tests` → `All checks passed!`; `openspec validate setup` valid.
- Live (lead-owned): `python3 tools/herdsetup.py validate --file skill/profiles/example-claude-codex-pi.yaml` → `ok`.

## 4. Mutations

Drive with `python3 tools/mutate.py openspec/changes/setup/tasks.md <tree>`; every one KILLED.

- [ ] **M1** in `tools/herdsetup.py`: replace

```python
    return sorted(h for h, a in bindings.ADAPTERS.items() if which(a["binary"]))
```

with

```python
    return sorted(bindings.ADAPTERS)
```

Killer: `tests/test_setup.py::test_discovery_finds_only_installed_supported_harnesses`

- [ ] **M2** in `tools/herdsetup.py`: replace

```python
            if e.get("source") not in SOURCES:
```

with

```python
            if False:
```

Killer: `tests/test_setup.py::test_every_recommendation_needs_a_reason_a_source_type_and_a_date`

- [ ] **M3** in `tools/herdsetup.py`: replace

```python
        if e["harness"] in pool:
```

with

```python
        if True:
```

Killer: `tests/test_setup.py::test_recommendations_are_limited_to_the_usable_pool_and_flag_stale_ones`

- [ ] **M4** in `tools/herdsetup.py`: replace

```python
"stale": age > stale_days}
```

with

```python
"stale": False}
```

Killer: `tests/test_setup.py::test_recommendations_are_limited_to_the_usable_pool_and_flag_stale_ones`

- [ ] **M5** in `tools/herdsetup.py`: replace

```python
            if not answer and role in saved:
```

with

```python
            if False:
```

Killer: `tests/test_setup.py::test_a_saved_choice_is_the_default_and_rediscovery_never_overrides_it`

- [ ] **M6** in `tools/herdsetup.py`: replace

```python
            if typed and typed["harness"] in pool and not binding_problems(role, typed):
```

with

```python
            if typed:
```

Killer: `tests/test_setup.py::test_an_unusable_answer_is_asked_again`

- [ ] **M7** in `tools/herdsetup.py`: replace

```python
    if ask(f"Save to {target}? [y/N] ").strip().lower() != "y":
```

with

```python
    if False:
```

Killer: `tests/test_setup.py::test_nothing_is_saved_without_confirmation`

- [ ] **M8** in `tools/herdsetup.py`: replace

```python
    consent = ask(CONSENT).strip().lower() == "y"
```

with

```python
    consent = True
```

Killer: `tests/test_setup.py::test_a_claude_only_machine_is_asked_per_role_and_warned_about_same_models`

- [ ] **M9** in `tools/herdsetup.py`: replace

```python
    if target.exists():
        print(f"{target} exists; not overwriting it")
        return 1
```

with

```python

```

Killer: `tests/test_setup.py::test_from_example_copies_the_profile_only_after_confirmation`

- [ ] **M11** in `tools/herdsetup.py`: replace

```python
    if not pool and any(r not in saved for r in REQUIRED_ROLES):
```

with

```python
    if False:
```

Killer: `tests/test_setup.py::test_a_machine_with_no_supported_harness_ends_without_prompting`

- [ ] **M12** in `tools/herdsetup.py`: replace

```python
        if problems:
            print(f"  (recommendation {role} {n} left out: {'; '.join(problems)})")
```

with

```python
        if False:
            print(f"  (recommendation {role} {n} left out: {'; '.join(problems)})")
```

Killer: `tests/test_setup.py::test_an_invalid_recommendation_is_left_out_with_a_reason`

- [ ] **M13** in `tools/herdsetup.py`: replace

```python
        else:
            print(f"  {author} -> {evaluator}: {kind} model")
```

with

```python

```

Killer: `tests/test_setup.py::test_every_pairs_diversity_is_shown_before_the_consent_question`

- [ ] **M14** in `tools/herdsetup.py`: replace

```python
    except yaml.YAMLError as exc:
        print(f"recommendations ignored: {path} is not valid YAML ({exc})")
        return {"version": 1, "roles": {}}
```

with

```python
    except ValueError:
        return {"version": 1, "roles": {}}
```

Killer: `tests/test_setup.py::test_malformed_recommendation_yaml_is_ignored_with_a_reason`

- [ ] **M15** in `tools/herdsetup.py`: replace

```python
            if not isinstance(e, dict):
                errors.append(f"{where}: an entry must be a mapping")
                continue
```

with

```python

```

Killer: `tests/test_setup.py::test_a_malformed_recommendations_document_is_diagnosed_not_crashed_on`

- [ ] **M10** in `tools/herdsetup.py`: replace

```python
        elif not which(bindings.ADAPTERS[roles[role]["harness"]]["binary"]):
```

with

```python
        elif False:
```

Killer: `tests/test_setup.py::test_validate_lists_what_is_missing_without_prompting`
