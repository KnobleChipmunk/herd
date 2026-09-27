"""The team: the portable role catalog, the current-step packet, and the loop's gate checks (#40).

usage: team.py check                                   validate skill/herd.yaml and its cards
       team.py assign ROLE --issue N --session S [--candidate C] [--scope TEXT] [--checks A,B]
                      [--bindings PATH] [--repo PATH]     record the resolved assignment at dispatch
       team.py packet ROLE --issue N [--candidate C] [--bindings PATH] [--repo PATH]
                                                       what a session needs at dispatch or after compaction
       team.py gate dispatch --issue N [--repo PATH]   the spec is approved and the last plan review approves
       team.py gate review   --issue N [--repo PATH]   the review-round cap (2, +1 per ruling) is not exceeded
       team.py gate review-file PATH                   a review file names the candidate it reviewed

Roles are not seats (docs/team-design.md): `skill/herd.yaml` names each role's
purpose, where it runs, its card, what it evaluates and what it may not do; the
machine-local bindings (#38) say which harness and model play it. The gates
check structure only; reviewers and the operator judge outcomes.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

import bindings
import runlog

SKILL = pathlib.Path(__file__).resolve().parent.parent / "skill"
CATALOG = SKILL / "herd.yaml"
CARD_ROOTS = (SKILL / "cards", SKILL.parent / "hermes")
KEYS = ("runs_in", "binding", "card", "activation", "purpose", "outputs", "may_not", "capabilities", "skip_when",
        "allowed_operations", "time_limit_minutes", "cost_limit", "exclusions", "advisory")
LEAD_HELD = ("orchestrator", "architect", "planner", "product_intake", "release_prep")
OWN_SESSION = ("builder", "plan_reviewer", "build_reviewer", "qa", "dogfood", "designer", "librarian")
REVIEW_CAP = 2


def load(path: pathlib.Path = CATALOG) -> dict:
    import yaml
    return yaml.safe_load(path.read_text())


def validate(doc: dict) -> list[str]:
    errors = [] if doc.get("version") == 1 else ["unsupported or missing version"]
    roles = doc.get("roles") or {}
    errors += [f"missing role {name}" for name in LEAD_HELD + OWN_SESSION if name not in roles]
    for name, r in roles.items():
        errors += [f"{name}: missing {k}" for k in KEYS if r.get(k) is None]
        if r.get("runs_in") not in ("own-session", "lead-held"):
            errors.append(f"{name}: runs_in must be own-session or lead-held")
        if name in LEAD_HELD and r.get("runs_in") != "lead-held":
            errors.append(f"{name}: a lead-held role (docs/team-design.md §2)")
        if name in OWN_SESSION and r.get("runs_in") != "own-session":
            errors.append(f"{name}: an own-session role (docs/team-design.md §2)")
        if r.get("binding") and r["binding"] not in bindings.ROLES:
            errors.append(f"{name}: unknown binding '{r['binding']}'")
        if r.get("card"):
            card = (SKILL / r["card"]).resolve()
            if card.suffix != ".md" or not any(card.is_relative_to(root.resolve()) for root in CARD_ROOTS):
                errors.append(f"{name}: card {r['card']} is not a role card (a .md under skill/cards/ or hermes/)")
            elif not card.exists():
                errors.append(f"{name}: card {r['card']} not found")
        for e in r.get("evaluates") or []:
            if e == name:
                errors.append(f"{name}: a role cannot evaluate itself")
            elif e not in roles:
                errors.append(f"{name}: evaluates unknown role '{e}'")
    return errors


def issue_events(repo: pathlib.Path, issue: str) -> list[dict]:
    return [e for e in runlog.read(repo) if e.get("issue") == issue]


def gate_dispatch(events: list[dict], issue: str) -> str | None:
    if not any(e["kind"] == "spec-approved" for e in events):
        return f"no spec-approved for #{issue}"
    reviews = [e for e in events if e["kind"] == "plan-review"]
    if not reviews:
        return f"no plan review for #{issue}"
    if reviews[-1].get("verdict") != "APPROVE":
        return f"the last plan review of #{issue} is {reviews[-1].get('verdict')}, not APPROVE"
    return None


def gate_review(events: list[dict], issue: str) -> str | None:
    rounds = sum(e["kind"] == "review-round" for e in events)
    rulings = sum(e["kind"] == "ruling" for e in events)
    if rounds >= REVIEW_CAP + rulings:
        return f"BLOCKED: #{issue} reached the review cap ({REVIEW_CAP} rounds{f' + {rulings} by ruling' if rulings else ''})"
    return None


def gate_review_file(path: pathlib.Path) -> str | None:
    if not re.search(r"(?im)^[ \t]*candidate[ \t]*:[ \t]*\S[^\r\n]*$", path.read_text()):
        return f"{path.name} names no candidate (add a 'Candidate: <commit or tree>' line)"
    return None


def resolved_binding(role_binding: str, bindings_file: pathlib.Path):
    if not bindings_file.exists():
        return "unknown (no bindings file)"
    return bindings.resolve(role_binding, user=bindings.load(bindings_file).get("roles")) or "unknown (unbound)"


def assign(role: str, *, issue: str, repo: pathlib.Path, session: str, candidate: str | None, scope: str | None,
           checks: list[str], bindings_file: pathlib.Path) -> str | None:
    """Record the resolved assignment in the run log (team design §2: role + binding + session + candidate
    + scope + selected checks); return why it was refused, or None."""
    roles = load()["roles"]
    if role not in roles:
        return f"unknown role {role!r}"
    b = resolved_binding(roles[role]["binding"], bindings_file)
    record = {"role": role, "binding": b, "session": session,
              "candidate": candidate, "scope": scope, "checks": checks}
    return runlog.append(repo, "note", {"issue": issue, "text": "assignment " + json.dumps(record, sort_keys=True)})


def latest_assignment(events: list[dict], role: str) -> dict | None:
    for e in reversed(events):
        if e["kind"] == "note" and e.get("text", "").startswith("assignment "):
            record = json.loads(e["text"][len("assignment "):])
            if record.get("role") == role:
                return record
    return None


def packet(role: str, *, issue: str, repo: pathlib.Path, candidate: str | None, bindings_file: pathlib.Path) -> dict:
    """When an assignment was recorded at dispatch, the binding and candidate come from it and the bindings
    file is not read; an explicit candidate names a newer one (a fix changed it)."""
    r = load()["roles"][role]
    events = issue_events(repo, issue)
    progress = [e for e in events if e["kind"] in runlog.PROGRESS]
    assignment = latest_assignment(events, role)
    if assignment:
        binding = assignment.get("binding") or "unknown (none recorded at dispatch)"
        candidate = candidate or assignment.get("candidate")
    else:
        binding = resolved_binding(r["binding"], bindings_file)
    authored = r.get("evaluates") or []
    return {"role": role, "card": str(SKILL / r["card"]), "issue": issue,
            "step": progress[-1]["kind"] if progress else "unknown", "candidate": candidate or "unknown",
            "returns_to": r.get("returns_to", "the lead"),
            "independence": f"fresh context whatever pane or model; must not have authored: {', '.join(authored)}"
            if authored
            else "none required",
            "binding": binding, "may_not": r["may_not"],
            "assignment": assignment or "unknown (no assignment recorded)"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    asg = sub.add_parser("assign")
    asg.add_argument("role")
    asg.add_argument("--issue", required=True)
    asg.add_argument("--session", required=True)
    asg.add_argument("--candidate")
    asg.add_argument("--scope")
    asg.add_argument("--checks", default="")
    asg.add_argument("--bindings")
    asg.add_argument("--repo", default=".")
    pk = sub.add_parser("packet")
    pk.add_argument("role")
    pk.add_argument("--issue", required=True)
    pk.add_argument("--candidate")
    pk.add_argument("--bindings")
    pk.add_argument("--repo", default=".")
    g = sub.add_parser("gate")
    g.add_argument("which", choices=("dispatch", "review", "review-file"))
    g.add_argument("path", nargs="?")
    g.add_argument("--issue")
    g.add_argument("--repo", default=".")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        errors = validate(load())
        print("\n".join(errors) or "valid: skill/herd.yaml")
        return 2 if errors else 0
    if a.cmd == "assign":
        why = assign(a.role, issue=a.issue, repo=pathlib.Path(a.repo), session=a.session, candidate=a.candidate,
                     scope=a.scope, checks=[c for c in a.checks.split(",") if c],
                     bindings_file=pathlib.Path(a.bindings) if a.bindings else bindings.user_path())
        print(why or "recorded")
        return 2 if why else 0
    if a.cmd == "packet":
        p = packet(a.role, issue=a.issue, repo=pathlib.Path(a.repo), candidate=a.candidate,
                   bindings_file=pathlib.Path(a.bindings) if a.bindings else bindings.user_path())
        for k, v in p.items():
            print(f"{k}: {v}")
        return 0
    if a.which == "review-file":
        why = gate_review_file(pathlib.Path(a.path))
    else:
        events = issue_events(pathlib.Path(a.repo), a.issue)
        why = gate_dispatch(events, a.issue) if a.which == "dispatch" else gate_review(events, a.issue)
    print(why or "ok")
    return 2 if why else 0


if __name__ == "__main__":
    sys.exit(main())
