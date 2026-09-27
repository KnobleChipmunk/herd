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
DOC_ERRORS = ("the recommendations file must be a mapping", "unsupported or missing version", "roles must be a mapping")
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


def entry_problems(role: str, e: dict) -> list[str]:
    """The provenance problems of one recommendation entry, from validate_recommendations."""
    prefix = f"{role} 1: "
    return [p[len(prefix):] for p in validate_recommendations({"version": 1, "roles": {role: [e]}})
            if p.startswith(prefix)]


def usable_offers(role: str, recs: dict, pool: list[str], *, today: datetime.date) -> list[dict]:
    """Offers whose provenance is complete and whose binding #38 accepts; an invalid entry is left out, with a visible reason."""
    out = []
    entries = (recs.get("roles") or {}).get(role) or []  # a role left empty (`lead:`) has no recommendations
    for n, e in enumerate(entries, 1):  # validate before reading any key: one bad entry must not hide the rest
        if not isinstance(e, dict):
            problems, offered = ["an entry must be a mapping"], False
        else:
            problems = entry_problems(role, e)
            offered = not problems and e["harness"] in pool
            if offered:
                age = (today - datetime.date.fromisoformat(str(e["date"]))).days
                problems = binding_problems(role, binding_of({**e, "stale": age > STALE_DAYS}))
        if problems:
            print(f"  (recommendation {role} {n} left out: {'; '.join(problems)})")
        elif offered:  # an entry for an uninstalled harness is simply not offered; not an error
            out.append({**e, "stale": age > STALE_DAYS})
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
    if any(e in DOC_ERRORS for e in rec_errors):  # a malformed document has no recommendations; a bad entry is left out by usable_offers
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
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(EXAMPLE.read_text())
    try:
        os.link(tmp, target)  # no-clobber: a file that appears while the prompt is open is left untouched
    except FileExistsError:
        tmp.unlink()
        print(f"{target} exists; not overwriting it")
        return 1
    tmp.unlink()
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
