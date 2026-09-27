# Tasks — bindings (#38)

Tier: **full**. DEPENDS ON #36: the branch is stacked on `feat/36-tickets`.
Fences are generated from the lead's pre-executed tree; `tools/fencecheck.py` must print `FENCES OK (8 steps)`.

## 1. Tests first — apply T1, T2, then observe RED

- [ ] **T1** `tests/test_bindings.py` — acceptance tests: schema, precedence, adapters, readiness, fallback, diversity, preflight

Create this file with exactly this body (byte-exact, ends with one newline):

```python
import subprocess

import pytest

import bindings
import preflight

CLAUDE_ONLY = {"version": 1, "roles": {
    "lead": {"harness": "claude", "model": "claude-opus-5-5"},
    "builder": {"harness": "claude", "model": "sonnet"},
    "build_reviewer": {"harness": "claude", "model": "fable"},
    "plan_reviewer": {"harness": "claude", "model": "fable"}}}
MIXED = {"version": 1, "probe_consent": True, "roles": {
    "lead": {"harness": "claude", "model": "claude-opus-5-5"},
    "builder": {"harness": "pi", "provider": "ollama", "model": "swift15-qwen3.8-128k:latest"},
    "build_reviewer": {"harness": "codex", "model": "gpt-6-sol", "settings": {"reasoning_effort": "high"},
                       "fallback": [{"harness": "claude", "model": "fable"}]},
    "plan_reviewer": {"harness": "codex", "model": "gpt-6-astra", "settings": {"reasoning_effort": "high"}}}}


def proc(rc=0, out="", err=""):
    return subprocess.CompletedProcess([], rc, stdout=out, stderr=err)


def runner(replies: dict):
    """Answer a command by the first key (a substring of the joined argv) it contains."""
    calls = []

    def run(argv, timeout=None):
        calls.append(argv)
        joined = " ".join(argv)
        for key, reply in replies.items():
            if key in joined:
                if isinstance(reply, Exception):
                    raise reply
                return reply
        return proc(0, "OK")

    run.calls = calls
    return run


ALL_THERE = {"claude": "/bin/claude", "codex": "/bin/codex", "pi": "/bin/pi"}.get


# --- validation (U1) ----------------------------------------------------------

def test_a_valid_file_passes():
    assert bindings.validate(MIXED) == []


@pytest.mark.parametrize("doc, error", [
    ({"version": 2, "roles": {}}, "unsupported version 2"),
    ({"roles": {}}, "missing version"),
    ({"version": 1, "roles": {}, "colour": "blue"}, "unknown key 'colour'"),
    ({"version": 1, "roles": {"barista": {"harness": "claude", "model": "x"}}}, "unknown role 'barista'"),
    ({"version": 1, "roles": {"lead": {"harness": "claude", "model": "x", "api_key": "sk-1"}}},
     "lead: unknown key 'api_key'"),
    ({"version": 1, "roles": {"lead": {"harness": "claude"}}}, "lead: missing model"),
    ({"version": 1, "roles": {"lead": {"harness": "gemini", "model": "x"}}}, "lead: unsupported harness 'gemini'"),
    ({"version": 1, "roles": {"lead": {"harness": "claude", "model": "x", "fallback": [{"harness": "claude"}]}}},
     "lead fallback 1: missing model"),
    ({"version": 1, "roles": {"lead": {"harness": "claude", "model": "x",
                                       "fallback": [{"harness": "claude", "model": "y", "fallback": []}]}}},
     "lead fallback 1: unknown key 'fallback'"),
])
def test_an_invalid_file_is_rejected_with_a_reason(doc, error):
    assert error in bindings.validate(doc)


def test_load_reads_yaml_and_refuses_an_invalid_file(tmp_path):
    good = tmp_path / "bindings.yaml"
    good.write_text("version: 1\nroles:\n  lead: {harness: claude, model: opus}\n")
    assert bindings.load(good)["roles"]["lead"]["model"] == "opus"
    bad = tmp_path / "bad.yaml"
    bad.write_text("version: 1\nroles: {}\nextra: 1\n")
    with pytest.raises(bindings.BindingsError, match="unknown key 'extra'"):
        bindings.load(bad)


def test_the_user_file_lives_in_the_platform_config_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert bindings.user_path() == tmp_path / "herd" / "bindings.yaml"
    monkeypatch.delenv("XDG_CONFIG_HOME")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert bindings.user_path() == tmp_path / ".config" / "herd" / "bindings.yaml"


# --- precedence (U1) ------------------------------------------------------------

def test_a_flag_beats_the_user_file_which_beats_portable_defaults():
    user = {"harness": "codex", "model": "gpt-6-sol"}
    default = {"harness": "claude", "model": "sonnet"}
    flag = {"harness": "claude", "model": "fable"}
    assert bindings.resolve("builder", flag=flag, user={"builder": user}, defaults={"builder": default}) == flag
    assert bindings.resolve("builder", user={"builder": user}, defaults={"builder": default}) == user
    assert bindings.resolve("builder", defaults={"builder": default}) == default
    assert bindings.resolve("builder") is None


# --- adapters (U2) --------------------------------------------------------------

def test_each_adapter_probes_the_exact_tuple_it_will_launch():
    pi = MIXED["roles"]["builder"]
    codex = MIXED["roles"]["build_reviewer"]
    assert bindings.probe_argv(pi) == ["pi", "--provider", "ollama", "--model", "swift15-qwen3.8-128k:latest",
                                       "-p", bindings.PROMPT]
    assert bindings.launch_args(pi) == ["--provider", "ollama", "--model", "swift15-qwen3.8-128k:latest"]
    assert bindings.probe_argv(codex) == ["codex", "exec", "-m", "gpt-6-sol", "-c", "model_reasoning_effort=high",
                                          bindings.PROMPT]
    assert bindings.launch_args(codex) == ["-m", "gpt-6-sol", "-c", "model_reasoning_effort=high"]
    assert bindings.probe_argv({"harness": "claude", "model": "fable"}) == ["claude", "-p", "--model", "fable",
                                                                           bindings.PROMPT]


def test_preflight_needs_only_the_harnesses_the_bindings_use():
    assert bindings.required_tools(CLAUDE_ONLY) == ["claude", "gh", "git", "herdr", "openspec"]
    assert bindings.required_tools(MIXED) == ["claude", "codex", "gh", "git", "herdr", "openspec", "pi"]
    only_in_fallback = {"version": 1, "roles": {"build_reviewer": {"harness": "codex", "model": "x",
                                                                   "fallback": [{"harness": "claude", "model": "y"}]}}}
    assert "claude" not in bindings.required_tools(only_in_fallback)  # a fallback is not a prerequisite
    inactive = {"version": 1, "roles": {"lead": {"harness": "claude", "model": "x"},
                                        "dogfood": {"harness": "pi", "model": "y"}}}
    assert "pi" not in bindings.required_tools(inactive)
    assert "pi" in bindings.required_tools(inactive, ("lead", "dogfood"))


def test_preflight_derives_its_tools_from_a_bindings_file(tmp_path, monkeypatch, capsys):
    f = tmp_path / "bindings.yaml"
    f.write_text("version: 1\nroles:\n  lead: {harness: claude, model: opus}\n")
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setattr(preflight.shutil, "which", lambda t: None if t in ("pi", "codex") else "/bin/" + t)
    assert preflight.main(["--bindings", str(f)]) == 0
    out = capsys.readouterr().out
    assert "claude on PATH" in out and "pi on PATH" not in out and "codex on PATH" not in out


def test_preflight_without_bindings_keeps_the_fixed_list(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))  # no user file there
    monkeypatch.setattr(preflight.shutil, "which", lambda t: "/bin/" + t)
    assert preflight.main([]) == 0
    assert "pi on PATH" in capsys.readouterr().out


# --- readiness (U3) -------------------------------------------------------------

def test_readiness_keeps_install_auth_and_access_apart():
    r = bindings.readiness(MIXED["roles"]["build_reviewer"], which=ALL_THERE, run=runner({}), consent=True)
    assert r == {"installed": True, "auth": "ok", "usable": "ok", "detail": ""}


def test_a_local_provider_needs_no_login():
    r = bindings.readiness(MIXED["roles"]["builder"], which=ALL_THERE, run=runner({}), consent=True)
    assert r["auth"] == "not-required" and r["usable"] == "ok"


def test_stale_auth_is_needs_login_and_is_not_probed():
    run = runner({"login status": proc(1, "", "Not logged in")})
    r = bindings.readiness(MIXED["roles"]["plan_reviewer"], which=ALL_THERE, run=run, consent=True)
    assert (r["auth"], r["usable"]) == ("needs-login", "not-probed")
    assert not any("exec" in a for a in run.calls)


@pytest.mark.parametrize("reply, usable", [
    (proc(1, "", "error: 429 Too Many Requests: rate limit reached"), "rate-limited"),
    (proc(1, "", "You've hit your usage limit"), "rate-limited"),
    (proc(1, "", "The model 'gpt-6-astra' is not supported when using Codex with a ChatGPT account"), "model-denied"),
    (proc(1, "", "Error: connect ECONNREFUSED 127.0.0.1:11434"), "unreachable"),
    (subprocess.TimeoutExpired("codex", 180), "unknown"),
    (proc(0, "I cannot comply", ""), "unknown"),
    (proc(1, "", "something odd"), "unknown"),
])
def test_a_probe_failure_is_classified_never_flattened(reply, usable):
    r = bindings.readiness(MIXED["roles"]["plan_reviewer"], which=ALL_THERE, run=runner({"exec": reply}),
                           consent=True)
    assert r["usable"] == usable


def test_no_consent_means_no_active_probe():
    run = runner({})
    r = bindings.readiness(MIXED["roles"]["plan_reviewer"], which=ALL_THERE, run=run, consent=False)
    assert r["usable"] == "not-probed" and not any("exec" in a for a in run.calls)


def test_a_missing_harness_is_not_installed():
    r = bindings.readiness(MIXED["roles"]["builder"], which=lambda t: None, run=runner({}), consent=True)
    assert (r["installed"], r["usable"]) == (False, "not-probed")


def test_readiness_is_cached_per_exact_tuple_with_freshness(tmp_path):
    cache = tmp_path / "readiness.json"
    run = runner({})
    b = MIXED["roles"]["plan_reviewer"]
    first = bindings.cached_readiness(b, cache=cache, now=1000.0, ttl=3600, which=ALL_THERE, run=run, consent=True)
    again = bindings.cached_readiness(b, cache=cache, now=2000.0, ttl=3600, which=ALL_THERE, run=run, consent=True)
    other = bindings.cached_readiness({**b, "model": "gpt-6-sol"}, cache=cache, now=2000.0, ttl=3600,
                                      which=ALL_THERE, run=run, consent=True)
    stale = bindings.cached_readiness(b, cache=cache, now=9000.0, ttl=3600, which=ALL_THERE, run=run, consent=True)
    assert first == again == other == stale
    assert sum("exec" in a for a in run.calls) == 3  # first, other (new tuple), stale; `again` came from the cache


# --- fallback (U7) --------------------------------------------------------------

def test_fallback_uses_only_the_listed_chain_and_records_why():
    run = runner({"gpt-6-sol": proc(1, "", "429 rate limit")})
    chosen, tried = bindings.choose(MIXED["roles"]["build_reviewer"], which=ALL_THERE, run=run, consent=True)
    assert chosen == {"harness": "claude", "model": "fable"}
    assert tried == ["codex gpt-6-sol: rate-limited (transient)"]


def test_a_permanent_denial_is_labelled_permanent():
    run = runner({"gpt-6-sol": proc(1, "", "model is not supported")})
    _, tried = bindings.choose(MIXED["roles"]["build_reviewer"], which=ALL_THERE, run=run, consent=True)
    assert tried == ["codex gpt-6-sol: model-denied (permanent)"]


def test_none_usable_returns_nothing_and_every_reason():
    run = runner({"gpt-6-sol": proc(1, "", "429"), "fable": proc(1, "", "not logged in"),
                  "auth status": proc(1, "", "Not logged in")})
    chosen, tried = bindings.choose(MIXED["roles"]["build_reviewer"], which=ALL_THERE, run=run, consent=True)
    assert chosen is None and len(tried) == 2 and "needs-login" in tried[1]


def test_a_fallback_never_adds_an_unlisted_binding():
    run = runner({"gpt-6-astra": proc(1, "", "429")})
    chosen, tried = bindings.choose(MIXED["roles"]["plan_reviewer"], which=ALL_THERE, run=run, consent=True)
    assert chosen is None and tried == ["codex gpt-6-astra: rate-limited (transient)"]


# --- independence (U5) ----------------------------------------------------------

def test_model_diversity_is_reported_per_author_evaluator_pair():
    one_model = {"version": 1, "roles": {r: {"harness": "claude", "model": "opus"} for r in
                                         ("lead", "builder", "build_reviewer", "plan_reviewer")}}
    report = bindings.diversity(one_model["roles"])
    assert ("builder", "build_reviewer", "same") in report and ("lead", "plan_reviewer", "same") in report
    assert ("builder", "build_reviewer", "different") in bindings.diversity(MIXED["roles"])
    partial = bindings.diversity({"builder": {"harness": "claude", "model": "opus"}})
    assert ("builder", "build_reviewer", "unknown") in partial


def test_the_cli_validates_and_reports_diversity_warnings(tmp_path, capsys):
    f = tmp_path / "b.yaml"
    f.write_text("version: 1\nroles:\n  builder: {harness: claude, model: opus}\n"
                 "  build_reviewer: {harness: claude, model: opus}\n")
    assert bindings.main(["check", "--file", str(f)]) == 0
    out = capsys.readouterr().out
    assert "valid" in out and "WARNING builder -> build_reviewer: same model" in out
    f.write_text("version: 9\nroles: {}\n")
    assert bindings.main(["check", "--file", str(f)]) == 2


# --- plan review #38 round 1 -------------------------------------------------

@pytest.mark.parametrize("binding, error", [
    ({"harness": "codex", "model": "m", "endpoint": "http://x"}, "the codex adapter does not support endpoint yet"),
    ({"harness": "claude", "model": "m", "auth_profile": "work"}, "the claude adapter does not support auth_profile yet"),
    ({"harness": "claude", "model": "m", "provider": "bedrock"}, "the claude adapter does not support provider yet"),
    ({"harness": "codex", "model": "m", "settings": {"temperature": 0}}, "the codex adapter does not support setting 'temperature'"),
    ({"harness": "pi", "model": "m", "settings": {"x": 1}}, "the pi adapter does not support settings yet"),
])
def test_identity_fields_an_adapter_cannot_honor_are_rejected_not_ignored(binding, error):
    assert any(error in e for e in bindings.validate({"version": 1, "roles": {"builder": binding}}))


@pytest.mark.parametrize("value", ["false", "yes", 1, [], {}])
def test_probe_consent_must_be_a_boolean(value):
    assert "probe_consent must be true or false" in bindings.validate({"version": 1, "probe_consent": value,
                                                                       "roles": {}})


def test_a_status_timeout_is_unknown_and_the_probe_still_decides():
    run = runner({"login status": subprocess.TimeoutExpired("codex", 30)})
    r = bindings.readiness(MIXED["roles"]["plan_reviewer"], which=ALL_THERE, run=run, consent=True)
    assert (r["auth"], r["usable"]) == ("unknown", "ok")


def test_a_failed_status_is_needs_login_only_when_it_says_so():
    other = runner({"login status": proc(1, "", "error: unrecognized subcommand 'login'")})
    r = bindings.readiness(MIXED["roles"]["plan_reviewer"], which=ALL_THERE, run=other, consent=False)
    assert r["auth"] == "unknown"
    logged_out = runner({"login status": proc(1, "Not logged in", "")})
    assert bindings.readiness(MIXED["roles"]["plan_reviewer"], which=ALL_THERE, run=logged_out,
                              consent=True)["auth"] == "needs-login"


def test_only_an_exact_ok_reply_is_usable():
    r = bindings.readiness(MIXED["roles"]["plan_reviewer"], which=ALL_THERE,
                           run=runner({"exec": proc(0, "OK, but I am not the model you asked for", "")}), consent=True)
    assert r["usable"] == "unknown"


def test_a_result_taken_without_consent_does_not_block_a_consented_probe(tmp_path):
    cache = tmp_path / "readiness.json"
    run = runner({})
    b = MIXED["roles"]["plan_reviewer"]
    first = bindings.cached_readiness(b, cache=cache, now=1.0, ttl=3600, which=ALL_THERE, run=run, consent=False)
    later = bindings.cached_readiness(b, cache=cache, now=2.0, ttl=3600, which=ALL_THERE, run=run, consent=True)
    assert first["usable"] == "not-probed" and later["usable"] == "ok"


def test_ready_takes_an_override_and_records_the_chosen_binding(repo_with_worktree, tmp_path, monkeypatch, capsys):
    import runlog
    main, _ = repo_with_worktree
    runlog.main(["add", "run-start", "--repo", str(main)])
    f = tmp_path / "b.yaml"
    f.write_text("version: 1\nprobe_consent: true\nroles:\n  build_reviewer: {harness: codex, model: gpt-6-sol}\n")
    monkeypatch.setattr(bindings, "readiness", lambda b, **kw: {"installed": True, "auth": "ok", "usable": "ok",
                                                                 "detail": ""})
    assert bindings.main(["ready", "--role", "build_reviewer", "--file", str(f), "--repo", str(main),
                          "--harness", "claude", "--model", "fable", "--record"]) == 0
    assert "build_reviewer: claude fable" in capsys.readouterr().out
    assert runlog.read(main)[-1]["text"] == 'binding build_reviewer (override): {"harness": "claude", "model": "fable"}'


def test_an_explicit_missing_bindings_file_fails_preflight(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HERDR_ENV", "1")
    assert preflight.main(["--bindings", str(tmp_path / "nope.yaml")]) == 1
    assert "no bindings file at" in capsys.readouterr().out


# --- plan review #38 round 2 -------------------------------------------------

def test_the_record_keeps_every_identity_field_of_the_chosen_binding(repo_with_worktree, tmp_path, monkeypatch):
    import json as _json

    import runlog
    main, _ = repo_with_worktree
    runlog.main(["add", "run-start", "--repo", str(main)])
    f = tmp_path / "b.yaml"
    f.write_text("version: 1\nprobe_consent: true\nroles:\n  builder: {harness: pi, provider: ollama, model: m}\n")
    monkeypatch.setattr(bindings, "readiness", lambda b, **kw: {"installed": True, "auth": "not-required",
                                                                 "usable": "ok", "detail": ""})
    assert bindings.main(["ready", "--role", "builder", "--file", str(f), "--repo", str(main), "--record"]) == 0
    text = runlog.read(main)[-1]["text"]
    assert _json.loads(text.split(": ", 1)[1]) == {"harness": "pi", "provider": "ollama", "model": "m"}


def test_a_refused_record_fails_the_command(repo_with_worktree, tmp_path, monkeypatch, capsys):
    main, _ = repo_with_worktree  # no run-start: the run log refuses the note
    f = tmp_path / "b.yaml"
    f.write_text("version: 1\nroles:\n  builder: {harness: claude, model: m}\n")
    monkeypatch.setattr(bindings, "readiness", lambda b, **kw: {"installed": True, "auth": "ok", "usable": "ok",
                                                                 "detail": ""})
    assert bindings.main(["ready", "--role", "builder", "--file", str(f), "--repo", str(main), "--record"]) == 1
    assert "not recorded: no run-start" in capsys.readouterr().out


@pytest.mark.parametrize("args, message", [
    (["--harness", "claude"], "an override needs both --harness and --model"),
    (["--model", "fable"], "an override needs both --harness and --model"),
    (["--role", "barista"], "unknown role 'barista'"),
])
def test_a_malformed_invocation_is_refused_before_any_probe(tmp_path, monkeypatch, capsys, args, message):
    f = tmp_path / "b.yaml"
    f.write_text("version: 1\nroles:\n  builder: {harness: claude, model: m}\n")
    monkeypatch.setattr(bindings, "readiness", lambda b, **kw: pytest.fail("probed"))
    role = [] if "--role" in args else ["--role", "builder"]
    assert bindings.main(["ready", "--file", str(f), *role, *args]) == 2
    assert message in capsys.readouterr().out


@pytest.mark.parametrize("binding, key", [
    ({"harness": "claude", "model": 5}, "model"),
    ({"harness": ["claude"], "model": "m"}, "harness"),
    ({"harness": "pi", "provider": "", "model": "m"}, "provider"),
    ({"harness": "codex", "model": "m", "settings": "high"}, "settings"),
    ({"harness": "codex", "model": "m", "settings": {"reasoning_effort": 3}}, "settings.reasoning_effort"),
])
def test_wrong_types_are_diagnosed_not_crashed_on(binding, key):
    assert f"builder: {key} has the wrong type" in bindings.validate({"version": 1, "roles": {"builder": binding}})


def test_a_boolean_or_malformed_version_and_malformed_yaml_are_diagnosed(tmp_path):
    assert "unsupported version True" in bindings.validate({"version": True, "roles": {}})
    bad = tmp_path / "bad.yaml"
    bad.write_text("version: 1\nroles: {builder: [unclosed\n")
    with pytest.raises(bindings.BindingsError, match="not valid YAML"):
        bindings.load(bad)


def test_a_remote_pi_provider_is_not_assumed_logged_in():
    r = bindings.readiness({"harness": "pi", "provider": "openrouter", "model": "m"}, which=ALL_THERE,
                           run=runner({}), consent=False)
    assert r["auth"] == "unknown"

```

- [ ] **T2** `tests/test_skill_text.py` — the sweep names the bindings file

Append exactly this text at the END of the file. The fence below BEGINS with the blank lines that separate it from the existing last line — keep them. The file must end with one newline:

```python

def test_the_sweep_names_the_bindings_file_and_the_readiness_check():
    text = " ".join(SKILL.read_text().split())
    sweep = text[text.index("3. **Preflight.**"): text.index("4. **Decisions.**")]
    assert "~/.config/herd/bindings.yaml" in sweep and "bindings.py ready --role" in sweep
```

RED after T1–T2: `tests/test_bindings.py` fails to collect (no module `bindings`); the new skill-text test fails.

## 2. Implementation — apply I1–I5

- [ ] **I1** `pyproject.toml` — register the new module for isort

Find this exact text (it occurs exactly once):

```python
known-first-party = ["attention", "fencecheck",
```

Replace it with exactly:

```python
known-first-party = ["attention", "bindings", "fencecheck",
```

- [ ] **I2** `tools/bindings.py` — the resolver, adapters, readiness and fallback

Create this file with exactly this body (byte-exact, ends with one newline):

```python
"""Bindings: which harness, provider, model and login plays each role on this machine (#38).

usage: bindings.py check [--file PATH]          validate; report model diversity per author/evaluator pair
       bindings.py tools [--file PATH]          the tools preflight must find for these bindings
       bindings.py ready --role ROLE [--file PATH] [--repo PATH]
                                                readiness of the role's binding and its fallback chain

The file is machine-local (default $XDG_CONFIG_HOME/herd/bindings.yaml, else
~/.config/herd/bindings.yaml) and never committed. Its contract is
docs/team-design.md §5: a binding is harness + provider + endpoint + model +
auth_profile (a reference, never a secret) + settings, with an ordered,
user-listed fallback chain. Precedence: an invocation flag, then this file,
then portable defaults. Unknown keys and unsupported versions are rejected.

Readiness keeps separate observations: installed, auth (ok, needs-login,
not-required for a local provider), and usable (ok, rate-limited,
model-denied, unreachable, unknown, not-probed). A timeout is unknown, never
"no access", and a reply is never taken as proof of which model answered.
Active probes run only with `probe_consent: true`. A fallback uses only the
bindings listed in that role's chain, and never switches login or provider
unless that exact binding is listed.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

VERSION = 1
ROLES = ("lead", "builder", "plan_reviewer", "build_reviewer", "qa", "dogfood", "designer", "librarian")
TOP_KEYS = ("version", "probe_consent", "roles")
BINDING_KEYS = ("harness", "provider", "endpoint", "model", "auth_profile", "settings", "fallback")
BASE_TOOLS = ("git", "gh", "herdr", "openspec")
ADAPTERS = {"claude": {"binary": "claude", "status": ["claude", "auth", "status"]},
            "codex": {"binary": "codex", "status": ["codex", "login", "status"]},
            "pi": {"binary": "pi", "status": None}}
PAIRS = (("builder", "build_reviewer"), ("lead", "plan_reviewer"), ("builder", "qa"), ("lead", "qa"))
LOOP_ROLES = ("lead", "builder", "plan_reviewer", "build_reviewer")
# What each adapter can honor today; anything else in a binding is rejected, never silently ignored.
SUPPORTED = {"claude": {"harness", "model"}, "codex": {"harness", "model", "settings"},
             "pi": {"harness", "model", "provider"}}
SETTINGS = {"codex": {"reasoning_effort"}}
LOCAL_PROVIDERS = {"pi": {"ollama"}}  # a provider served on this machine needs no login
LOGIN_WORDS = ("not logged in", "log in", "login required", "unauthorized", "not authenticated")
PROMPT = "Reply with exactly: OK"
TIMEOUT = 180
TRANSIENT = ("rate-limited", "unreachable", "unknown", "not-probed")
PATTERNS = (("rate-limited", ("429", "rate limit", "usage limit", "too many requests")),
            ("model-denied", ("not supported", "does not exist", "not available", "unknown model",
                              "model not found", "no access")),
            ("unreachable", ("econnrefused", "connection refused", "unreachable", "could not connect",
                             "failed to connect")))


class BindingsError(ValueError):
    pass


def user_path() -> pathlib.Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(pathlib.Path(os.environ.get("HOME", "~")).expanduser() / ".config")
    return pathlib.Path(base) / "herd" / "bindings.yaml"


def _binding_errors(b, where: str, allow_fallback: bool) -> list[str]:
    if not isinstance(b, dict):
        return [f"{where}: a binding must be a mapping"]
    bad = [k for k in ("harness", "model", "provider") if k in b and not (isinstance(b[k], str) and b[k].strip())]
    if "settings" in b and not isinstance(b["settings"], dict):
        bad.append("settings")
    elif isinstance(b.get("settings"), dict) and "reasoning_effort" in b["settings"] and \
            not isinstance(b["settings"]["reasoning_effort"], str):
        bad.append("settings.reasoning_effort")
    if bad:
        return [f"{where}: {k} has the wrong type" for k in bad]
    allowed = BINDING_KEYS if allow_fallback else tuple(k for k in BINDING_KEYS if k != "fallback")
    errors = [f"{where}: unknown key '{k}'" for k in b if k not in allowed]
    errors += [f"{where}: missing {k}" for k in ("harness", "model") if not b.get(k)]
    if b.get("harness") and b["harness"] not in ADAPTERS:
        errors.append(f"{where}: unsupported harness '{b['harness']}'")
    elif b.get("harness"):
        h = b["harness"]
        errors += [f"{where}: the {h} adapter does not support {k} yet" for k in b
                   if k in allowed and k != "fallback" and k not in SUPPORTED[h]]
        errors += [f"{where}: the {h} adapter does not support setting '{s}'" for s in (b.get("settings") or {})
                   if "settings" in SUPPORTED[h] and s not in SETTINGS.get(h, set())]
    if allow_fallback and "fallback" in b:
        if not isinstance(b["fallback"], list):
            errors.append(f"{where}: fallback must be a list")
        else:
            for n, f in enumerate(b["fallback"], 1):
                errors += _binding_errors(f, f"{where} fallback {n}", False)
    return errors


def validate(doc) -> list[str]:
    if not isinstance(doc, dict):
        return ["the file must be a mapping"]
    errors = [f"unknown key '{k}'" for k in doc if k not in TOP_KEYS]
    if "version" not in doc:
        errors.append("missing version")
    elif type(doc["version"]) is not int or doc["version"] != VERSION:
        errors.append(f"unsupported version {doc['version']}")
    if "probe_consent" in doc and not isinstance(doc["probe_consent"], bool):
        errors.append("probe_consent must be true or false")
    roles = doc.get("roles", {})
    if not isinstance(roles, dict):
        return errors + ["roles must be a mapping"]
    for role, b in roles.items():
        if role not in ROLES:
            errors.append(f"unknown role '{role}'")
        else:
            errors += _binding_errors(b, role, True)
    return errors


def load(path: pathlib.Path) -> dict:
    try:
        import yaml
    except ImportError as exc:  # PyYAML is the one third-party module herd reads config with
        raise BindingsError("reading bindings needs PyYAML: pip install pyyaml") from exc
    try:
        doc = yaml.safe_load(pathlib.Path(path).read_text())
    except yaml.YAMLError as exc:
        raise BindingsError(f"not valid YAML: {exc}") from exc
    errors = validate(doc)
    if errors:
        raise BindingsError("; ".join(errors))
    return doc


def resolve(role: str, *, flag: dict | None = None, user: dict | None = None,
            defaults: dict | None = None) -> dict | None:
    """An invocation flag, else the user's binding, else the portable default, else None."""
    return flag or (user or {}).get(role) or (defaults or {}).get(role)


def probe_argv(b: dict) -> list[str]:
    effort = (b.get("settings") or {}).get("reasoning_effort")
    if b["harness"] == "claude":
        return ["claude", "-p", "--model", b["model"], PROMPT]
    if b["harness"] == "codex":
        return ["codex", "exec", "-m", b["model"]] + (["-c", f"model_reasoning_effort={effort}"] if effort else []) \
            + [PROMPT]
    return ["pi"] + (["--provider", b["provider"]] if b.get("provider") else []) + ["--model", b["model"], "-p", PROMPT]


def launch_args(b: dict) -> list[str]:
    """The native arguments `herdr agent start ... --` takes for this binding."""
    effort = (b.get("settings") or {}).get("reasoning_effort")
    if b["harness"] == "claude":
        return ["--model", b["model"]]
    if b["harness"] == "codex":
        return ["-m", b["model"]] + (["-c", f"model_reasoning_effort={effort}"] if effort else [])
    return (["--provider", b["provider"]] if b.get("provider") else []) + ["--model", b["model"]]


def required_tools(doc: dict, roles: tuple = LOOP_ROLES) -> list[str]:
    """Base tools plus the primary harness of each selected role. Fallbacks and inactive roles are not
    prerequisites; readiness reports whether they are usable."""
    tools = set(BASE_TOOLS)
    for role, b in doc.get("roles", {}).items():
        if role in roles:
            tools.add(ADAPTERS[b["harness"]]["binary"])
    return sorted(tools)


def _run(argv: list[str], timeout: float | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)


def _last_line(p: subprocess.CompletedProcess) -> str:
    lines = (p.stderr or p.stdout or "").strip().splitlines()
    return lines[-1][:160] if lines else ""


def classify(p: subprocess.CompletedProcess) -> str:
    lines = [ln.strip() for ln in (p.stdout or "").splitlines() if ln.strip()]
    if p.returncode == 0 and lines and lines[-1] == "OK":
        return "ok"
    text = f"{p.stdout or ''} {p.stderr or ''}".lower()
    for state, needles in PATTERNS:
        if any(n in text for n in needles):
            return state
    return "unknown"


def readiness(b: dict, *, which=shutil.which, run=_run, consent: bool) -> dict:
    adapter = ADAPTERS[b["harness"]]
    if which(adapter["binary"]) is None:
        return {"installed": False, "auth": "unknown", "usable": "not-probed", "detail": f"{adapter['binary']} not on PATH"}
    auth = "not-required" if b.get("provider") in LOCAL_PROVIDERS.get(b["harness"], set()) else "unknown"
    if adapter["status"]:
        try:
            s = run(adapter["status"], timeout=30)
        except subprocess.TimeoutExpired:
            s = None
        if s is None:
            auth = "unknown"
        elif s.returncode == 0:
            auth = "ok"
        elif any(w in f"{s.stdout or ''} {s.stderr or ''}".lower() for w in LOGIN_WORDS):
            return {"installed": True, "auth": "needs-login", "usable": "not-probed", "detail": _last_line(s)}
        else:
            auth = "unknown"
    if not consent:
        return {"installed": True, "auth": auth, "usable": "not-probed", "detail": "no probe consent"}
    try:
        p = run(probe_argv(b), timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"installed": True, "auth": auth, "usable": "unknown", "detail": f"no answer in {TIMEOUT}s"}
    usable = classify(p)
    return {"installed": True, "auth": auth, "usable": usable, "detail": "" if usable == "ok" else _last_line(p)}


def _key(b: dict, consent: bool) -> str:
    """The exact binding plus whether probing was allowed: a result taken without consent never stands in
    for a consented probe."""
    return json.dumps({"binding": {k: v for k, v in b.items() if k != "fallback"}, "consent": consent}, sort_keys=True)


def cached_readiness(b: dict, *, cache: pathlib.Path, now: float, ttl: float, **kw) -> dict:
    """Readiness of this exact binding, reused while younger than `ttl` seconds."""
    store = json.loads(cache.read_text()) if cache.exists() else {}
    key = _key(b, bool(kw.get("consent")))
    hit = store.get(key)
    if hit and now - hit["at"] < ttl:
        return hit["result"]
    result = readiness(b, **kw)
    store[key] = {"at": now, "result": result}
    cache.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_suffix(".tmp")
    tmp.write_text(json.dumps(store))
    os.replace(tmp, cache)
    return result


def state_of(r: dict) -> str:
    if not r["installed"]:
        return "not-installed"
    return "needs-login" if r["auth"] == "needs-login" else r["usable"]


def choose(b: dict, *, ready=None, **kw) -> tuple[dict | None, list[str]]:
    """The first usable binding of the role's own chain (the binding, then its listed fallbacks), and why
    each earlier one was passed over."""
    ready = ready or (lambda x: readiness(x, **kw))
    tried = []
    for x in [{k: v for k, v in b.items() if k != "fallback"}] + list(b.get("fallback") or []):
        state = state_of(ready(x))
        if state == "ok":
            return x, tried
        tried.append(f"{x['harness']} {x['model']}: {state} ({'transient' if state in TRANSIENT else 'permanent'})")
    return None, tried


def diversity(roles: dict) -> list[tuple[str, str, str]]:
    """(author, evaluator, same|different|unknown) for each pair where either side is bound."""
    out = []
    for a, e in PAIRS:
        if a in roles or e in roles:
            if a not in roles or e not in roles:
                out.append((a, e, "unknown"))
            else:
                out.append((a, e, "same" if roles[a]["model"] == roles[e]["model"] else "different"))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("check", "tools", "ready"))
    ap.add_argument("--file", default=None)
    ap.add_argument("--role")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--harness", help="with --model: an invocation override for the role (highest precedence)")
    ap.add_argument("--model")
    ap.add_argument("--record", action="store_true", help="record the chosen binding in the run log")
    a = ap.parse_args(argv)
    path = pathlib.Path(a.file) if a.file else user_path()
    try:
        doc = load(path)
    except (BindingsError, OSError) as exc:
        print(f"invalid: {path}: {exc}")
        return 2
    roles = doc.get("roles", {})
    if a.cmd == "check":
        print(f"valid: {path}")
        for author, evaluator, kind in diversity(roles):
            if kind == "same":
                print(f"WARNING {author} -> {evaluator}: same model ({roles[author]['model']}); "
                      f"a different model is recommended (docs/team-design.md §4)")
            elif kind == "unknown":
                print(f"note {author} -> {evaluator}: diversity unknown (one side is not bound)")
        return 0
    if a.cmd == "tools":
        print(" ".join(required_tools(doc)))
        return 0
    if a.role not in ROLES:
        print(f"unknown role {a.role!r}: one of {', '.join(ROLES)}")
        return 2
    if bool(a.harness) != bool(a.model):
        print("an override needs both --harness and --model")
        return 2
    flag = {"harness": a.harness, "model": a.model} if a.harness else None
    if flag and _binding_errors(flag, "override", False):
        print("; ".join(_binding_errors(flag, "override", False)))
        return 2
    binding = resolve(a.role, flag=flag, user=roles)
    if not binding:
        print(f"no binding for role {a.role}")
        return 2
    from herdtool import git_common_dir
    cache = git_common_dir(pathlib.Path(a.repo)) / "herd" / "readiness.json"
    chosen, tried = choose(binding, ready=lambda x: cached_readiness(
        x, cache=cache, now=time.time(), ttl=6 * 3600, consent=doc.get("probe_consent") is True))
    for line in tried:
        print(f"passed over {line}")
    print(f"{a.role}: {chosen['harness']} {chosen['model']}" if chosen else f"{a.role}: NONE usable")
    if chosen and a.record:
        import runlog
        why = runlog.append(pathlib.Path(a.repo), "note", {"text": f"binding {a.role}"
                                                           + (" (override)" if flag else "") + ": "
                                                           + json.dumps(chosen, sort_keys=True)})
        if why:
            print(f"not recorded: {why}")
            return 1
    return 0 if chosen else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **I3** `tools/preflight.py` — tools derived from the bindings file

REPLACE THE WHOLE FILE. Delete everything in it and write exactly this body (byte-exact, ends with one newline):

```python
"""Check a machine is ready for an unattended run, before the operator goes to bed.

usage: preflight.py [--need ISSUE:VARIABLE ...]

Checks that the run is inside Herdr, that every tool the herd calls is on
PATH, and that each environment variable an issue needs is set and not
empty. Variables are reported as set or missing, never by value. Exits 1
when anything is missing, so the question goes to the operator now rather
than at 3 a.m.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import sys

import bindings

TOOLS = ("git", "gh", "herdr", "pi", "codex", "claude", "openspec")


def need(spec: str) -> tuple[str, str]:
    issue, sep, var = spec.partition(":")
    if not sep or not issue or not var:
        raise SystemExit(f"--need takes ISSUE:VARIABLE, got {spec!r}")
    return issue, var


def tools_for(path: pathlib.Path | None, roles: tuple = bindings.LOOP_ROLES) -> tuple[str, ...]:
    """The tools the selected roles' bindings need (#38); the fixed list when the user has no bindings file.
    An explicitly named file that does not exist is an error, not a fallback."""
    if path is not None and not path.exists():
        raise bindings.BindingsError(f"no bindings file at {path}")
    path = path or bindings.user_path()
    return tuple(bindings.required_tools(bindings.load(path), roles)) if path.exists() else TOOLS


def checks(needs: list[tuple[str, str]], tools: tuple[str, ...] = TOOLS) -> list[tuple[bool, str]]:
    out = [(os.environ.get("HERDR_ENV") == "1", "inside Herdr (HERDR_ENV=1)")]
    out += [(shutil.which(t) is not None, f"{t} on PATH") for t in tools]
    out += [(bool(os.environ.get(var)), f"{var} for #{issue}") for issue, var in needs]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--need", action="append", default=[])
    ap.add_argument("--bindings", help="bindings file (default: the user's, when it exists)")
    ap.add_argument("--roles", default=",".join(bindings.LOOP_ROLES), help="the roles this run uses")
    a = ap.parse_args(argv)
    try:
        tools = tools_for(pathlib.Path(a.bindings) if a.bindings else None, tuple(a.roles.split(",")))
    except bindings.BindingsError as exc:
        print(f"MISSING valid bindings: {exc}")
        return 1
    results = checks([need(s) for s in a.need], tools)
    for ok, label in results:
        print(f"{'ok  ' if ok else 'MISSING'} {label}")
    return 0 if all(ok for ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **I4** `requirements.txt` — declare PyYAML, the one third-party dependency

Create this file with exactly this body (byte-exact, ends with one newline):

```python
# herd's only third-party runtime dependency: reading bindings.yaml and herd.yaml (#38).
pyyaml>=6
```

- [ ] **I5** `skill/profiles/example-claude-codex-pi.yaml` — this machine's roster as an example profile

Create this file with exactly this body (byte-exact, ends with one newline):

```python
# Example bindings: the machine herd was built on (Claude Code lead, a local
# pi builder, Codex reviewers). Copy to ~/.config/herd/bindings.yaml and edit,
# or run `herd setup` (#39). This is an example, not a requirement.
version: 1
# Set to true to allow one short diagnostic request per binding (it may use quota).
probe_consent: false
roles:
  lead:
    harness: claude
    model: claude-opus-5-5
  builder:
    harness: pi
    provider: ollama
    model: swift15-qwen3.8-128k:latest
  plan_reviewer:
    harness: codex
    model: gpt-6-astra
    settings: {reasoning_effort: high}
    fallback:
      - {harness: codex, model: gpt-6-sol, settings: {reasoning_effort: high}}
      - {harness: claude, model: fable}
  build_reviewer:
    harness: codex
    model: gpt-6-sol
    settings: {reasoning_effort: high}
    fallback:
      - {harness: claude, model: fable}
```

- [ ] **I6** `skill/SKILL.md` — the sweep reads the bindings file

Find this exact text (it occurs exactly once):

```python
   It reports set or missing, never values.
4. **Decisions.**
```

Replace it with exactly:

```python
   It reports set or missing, never values. When the machine has a bindings
   file (`~/.config/herd/bindings.yaml`; an example is in `skill/profiles/`),
   preflight checks only the harnesses it binds, and the Probe step uses
   `python3 <herd>/tools/bindings.py ready --role <role> --record` for each loop
   role instead of `probe.py` (it honors the file's `probe_consent`); `probe.py`
   and the Roster table remain only for machines without a bindings file,
   until #51 (#38).
4. **Decisions.**
```

## 3. Gates

- Full suite at the base (`feat/36-tickets` after its build): `335 passed`. After: `400 passed` (64 in `tests/test_bindings.py` with parametrized cases, 1 new skill-text test). ~8 s.
- `ruff check tools tests` → `All checks passed!`; `openspec validate bindings` valid.
- Live (lead-owned; run in pre-execution 2026-09-27): `bindings.py check --file skill/profiles/example-claude-codex-pi.yaml` → valid; `bindings.py ready --role build_reviewer` and `--role builder` on that file → both usable.

## 4. Mutations

Drive with `python3 tools/mutate.py openspec/changes/bindings/tasks.md <tree>`; every one KILLED.

- [ ] **M1** in `tools/bindings.py`: replace

```python
    elif type(doc["version"]) is not int or doc["version"] != VERSION:
```

with

```python
    elif False:
```

Killer: `tests/test_bindings.py::test_an_invalid_file_is_rejected_with_a_reason`

- [ ] **M2** in `tools/bindings.py`: replace

```python
    errors = [f"{where}: unknown key '{k}'" for k in b if k not in allowed]
```

with

```python
    errors = []
```

Killer: `tests/test_bindings.py::test_an_invalid_file_is_rejected_with_a_reason`

- [ ] **M3** in `tools/bindings.py`: replace

```python
    return flag or (user or {}).get(role) or (defaults or {}).get(role)
```

with

```python
    return (defaults or {}).get(role) or (user or {}).get(role) or flag
```

Killer: `tests/test_bindings.py::test_a_flag_beats_the_user_file_which_beats_portable_defaults`

- [ ] **M4** in `tools/bindings.py`: replace

```python
    return ["pi"] + (["--provider", b["provider"]] if b.get("provider") else []) + ["--model", b["model"], "-p", PROMPT]
```

with

```python
    return ["pi", "--model", b["model"], "-p", PROMPT]
```

Killer: `tests/test_bindings.py::test_each_adapter_probes_the_exact_tuple_it_will_launch`

- [ ] **M5** in `tools/bindings.py`: replace

```python
        if role in roles:
```

with

```python
        if True:
```

Killer: `tests/test_bindings.py::test_preflight_needs_only_the_harnesses_the_bindings_use`

- [ ] **M6** in `tools/bindings.py`: replace

```python
        elif any(w in f"{s.stdout or ''} {s.stderr or ''}".lower() for w in LOGIN_WORDS):
```

with

```python
        elif True:
```

Killer: `tests/test_bindings.py::test_a_failed_status_is_needs_login_only_when_it_says_so`

- [ ] **M7** in `tools/bindings.py`: replace

```python
    if not consent:
```

with

```python
    if False:
```

Killer: `tests/test_bindings.py::test_no_consent_means_no_active_probe`

- [ ] **M8** in `tools/bindings.py`: replace

```python
"usable": "unknown", "detail": f"no answer in {TIMEOUT}s"}
```

with

```python
"usable": "model-denied", "detail": f"no answer in {TIMEOUT}s"}
```

Killer: `tests/test_bindings.py::test_a_probe_failure_is_classified_never_flattened`

- [ ] **M9** in `tools/bindings.py`: replace

```python
    if hit and now - hit["at"] < ttl:
```

with

```python
    if hit:
```

Killer: `tests/test_bindings.py::test_readiness_is_cached_per_exact_tuple_with_freshness`

- [ ] **M10** in `tools/bindings.py`: replace

```python
{'transient' if state in TRANSIENT else 'permanent'}
```

with

```python
{'transient'}
```

Killer: `tests/test_bindings.py::test_a_permanent_denial_is_labelled_permanent`

- [ ] **M11** in `tools/bindings.py`: replace

```python
"same" if roles[a]["model"] == roles[e]["model"] else "different"
```

with

```python
"different"
```

Killer: `tests/test_bindings.py::test_model_diversity_is_reported_per_author_evaluator_pair`

- [ ] **M12** in `tools/preflight.py`: replace

```python
    return tuple(bindings.required_tools(bindings.load(path), roles)) if path.exists() else TOOLS
```

with

```python
    return TOOLS
```

Killer: `tests/test_bindings.py::test_preflight_derives_its_tools_from_a_bindings_file`

- [ ] **M13** in `tools/bindings.py`: replace

```python
    if "probe_consent" in doc and not isinstance(doc["probe_consent"], bool):
```

with

```python
    if False:
```

Killer: `tests/test_bindings.py::test_probe_consent_must_be_a_boolean`

- [ ] **M14** in `tools/bindings.py`: replace

```python
        except subprocess.TimeoutExpired:
            s = None
```

with

```python
        except ValueError:
            s = None
```

Killer: `tests/test_bindings.py::test_a_status_timeout_is_unknown_and_the_probe_still_decides`

- [ ] **M15** in `tools/bindings.py`: replace

```python
    if p.returncode == 0 and lines and lines[-1] == "OK":
```

with

```python
    if p.returncode == 0 and "OK" in (p.stdout or ""):
```

Killer: `tests/test_bindings.py::test_only_an_exact_ok_reply_is_usable`

- [ ] **M16** in `tools/bindings.py`: replace

```python
    key = _key(b, bool(kw.get("consent")))
```

with

```python
    key = _key(b, False)
```

Killer: `tests/test_bindings.py::test_a_result_taken_without_consent_does_not_block_a_consented_probe`

- [ ] **M18** in `tools/bindings.py`: replace

```python
    if bool(a.harness) != bool(a.model):
```

with

```python
    if False:
```

Killer: `tests/test_bindings.py::test_a_malformed_invocation_is_refused_before_any_probe`

- [ ] **M19** in `tools/bindings.py`: replace

```python
    if bad:
        return [f"{where}: {k} has the wrong type" for k in bad]
```

with

```python

```

Killer: `tests/test_bindings.py::test_wrong_types_are_diagnosed_not_crashed_on`

- [ ] **M20** in `tools/bindings.py`: replace

```python
    auth = "not-required" if b.get("provider") in LOCAL_PROVIDERS.get(b["harness"], set()) else "unknown"
```

with

```python
    auth = "not-required"
```

Killer: `tests/test_bindings.py::test_a_remote_pi_provider_is_not_assumed_logged_in`

- [ ] **M17** in `tools/bindings.py`: replace

```python
        errors += [f"{where}: the {h} adapter does not support {k} yet" for k in b
```

with

```python
        errors += [f"{where}: the {h} adapter does not support {k} yet" for k in ()
```

Killer: `tests/test_bindings.py::test_identity_fields_an_adapter_cannot_honor_are_rejected_not_ignored`
