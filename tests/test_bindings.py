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


def test_an_override_works_without_a_bindings_file_and_without_consent(repo_with_worktree, tmp_path, monkeypatch,
                                                                         capsys):
    """Build review #38 (rounds 1-2): the override must not depend on a user file existing."""
    main, _ = repo_with_worktree
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))  # no user bindings file here
    seen = []
    monkeypatch.setattr(bindings, "readiness", lambda b, **kw: seen.append(kw.get("consent")) or
                        {"installed": True, "auth": "ok", "usable": "not-probed", "detail": "no probe consent"})
    assert bindings.main(["ready", "--role", "build_reviewer", "--harness", "claude", "--model", "fable",
                          "--repo", str(main)]) == 1
    out = capsys.readouterr().out
    assert "passed over claude fable: not-probed" in out and "NONE usable" in out
    assert seen == [False]

