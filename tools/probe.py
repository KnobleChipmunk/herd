"""Probe each role's models before a run and pick the first that answers.

usage: probe.py [--skill SKILL.md] [--role ROLE ...] [--log --repo PATH]

Reads the Roster table in the herd skill (the one place models are named),
sends every candidate in a role's fallback chain a one-line request through
its own harness, and prints the model each role will use. A model that a
harness lists is not necessarily one the login can use, so nothing is
assumed. With --log, every role that fell back gets a `fallback` event in
the run log. Exits 1 when a role has no model that answers.
"""
from __future__ import annotations

import argparse
import itertools
import pathlib
import re
import subprocess
import sys

import runlog

PROMPT = "Reply with exactly: OK"
TIMEOUT = 180
SKILL = pathlib.Path(__file__).resolve().parent.parent / "skill" / "SKILL.md"
DEFAULT_ROLES = ("Builder", "Plan reviewer", "Build reviewer")


def parse_roster(skill_text: str) -> dict[str, dict]:
    """The first table after the `## Roster` heading, keyed by role."""
    lines = skill_text[skill_text.index("## Roster"):].splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("|"))
    table = list(itertools.takewhile(lambda ln: ln.startswith("|"), lines[start:]))
    roster = {}
    for line in table[2:]:
        role, harness, model, pane, falls_back = [c.strip() for c in line.strip().strip("|").split("|")]
        roster[role] = {
            "harness": harness,
            "models": [m.removeprefix("--model ") for m in re.findall(r"`([^`]+)`", model)],
            "panes": re.findall(r"`([^`]+)`", pane),
            "fallback": [r.strip() for r in falls_back.split(",") if r.strip() not in ("", "—")],
        }
    return roster


def chain(roster: dict[str, dict], role: str) -> list[tuple[str, str]]:
    out = [(roster[role]["harness"], m) for m in roster[role]["models"]]
    for next_role in roster[role]["fallback"]:
        out += [(roster[next_role]["harness"], m) for m in roster[next_role]["models"]]
    return out


def probe_command(harness: str, model: str) -> list[str]:
    if harness == "Codex":
        return ["codex", "exec", "-m", model, PROMPT]
    if harness == "Claude Code":
        return ["claude", "-p", "--model", model, PROMPT]
    if harness == "pi":
        return ["pi", "--model", model, "-p", PROMPT]
    raise SystemExit(f"no probe for harness {harness!r}")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, stdin=subprocess.DEVNULL)


def choose(candidates: list[tuple[str, str]], runner=None) -> tuple[tuple[str, str] | None, list[str]]:
    runner = runner or run
    tried = []
    for harness, model in candidates:
        try:
            r = runner(probe_command(harness, model))
        except subprocess.TimeoutExpired:
            tried.append(f"{model}: no answer in {TIMEOUT}s")
            continue
        if r.returncode == 0 and "OK" in r.stdout:
            return (harness, model), tried
        err = (r.stderr or r.stdout).strip().splitlines()
        tried.append(f"{model}: {err[-1][:160] if err and r.returncode else 'no OK in the reply'}")
    return None, tried


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skill", default=str(SKILL))
    ap.add_argument("--role", action="append")
    ap.add_argument("--log", action="store_true")
    ap.add_argument("--repo", default=".")
    a = ap.parse_args(argv)
    roster = parse_roster(pathlib.Path(a.skill).read_text())
    missing = 0
    for role in a.role or DEFAULT_ROLES:
        candidates = chain(roster, role)
        chosen, tried = choose(candidates, run)
        if chosen is None:
            print(f"{role}: NONE — " + "; ".join(tried))
            missing += 1
            continue
        line = f"{role}: {chosen[1]} ({chosen[0]})"
        if chosen != candidates[0]:
            line += " — FALLBACK; " + "; ".join(tried)
            if a.log:
                runlog.append(pathlib.Path(a.repo), "fallback", {
                    "agent": roster[role]["panes"][0], "model": chosen[1], "text": "; ".join(tried)})
        print(line)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
