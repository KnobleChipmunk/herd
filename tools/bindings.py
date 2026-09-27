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
        if a.cmd == "ready" and a.harness and a.model and not a.file and not path.exists():
            doc = {"version": VERSION, "roles": {}}  # an override alone, with no saved consent
        else:
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
