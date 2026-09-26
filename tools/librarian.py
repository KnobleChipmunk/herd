"""The post-run librarian's deterministic half: ledger rows, friction filing, and the facts to report.

usage: librarian.py report         [--repo PATH]
       librarian.py ledger-rows    [--repo PATH]
       librarian.py append-ledger  [--repo PATH] [--ledger PATH]
       librarian.py friction       [--repo PATH]
       librarian.py friction-append --class SLUG [--title TITLE] --issue N --text TEXT [--date D] [--ledger PATH]

Every number in a ledger row is counted from the run log and live gh, never
estimated: the model (Hermes) decides which friction class a line belongs to
and what a proposal says, and this tool does the counting and the file edits.
The ledgers live in the vault ($HERD_VAULT, default ~/Documents/Obsidian/Exocortex).
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import platform
import re
import sys

import runlog
from herdtool import main_checkout
from merge_stack import gh_runner

COLUMNS = ("date", "repo", "ticket", "pr", "variant", "tier", "plan rounds", "rounds", "findings", "rulings",
           "blocked", "gate miss", "lead", "outcome")
CAPS = {"small": 2, "full": 3}
VAULT = pathlib.Path(os.environ.get("HERD_VAULT", pathlib.Path.home() / "Documents/Obsidian/Exocortex"))
HERD_LEDGER = VAULT / "knowledge" / "herd-ledger.md"
FRICTION_LEDGER = VAULT / "knowledge" / "friction-ledger.md"


def findings_of(verdict: str) -> str:
    m = re.search(r"FINDINGS:\s*(\d+)", verdict)
    return m.group(1) if m else "0"


def rows(events: list[dict], repo: str, gh) -> list[dict]:
    """One ledger row per issue the run touched, in the order the run first touched it."""
    issues: dict[str, list[dict]] = {}
    for e in events:
        if e.get("issue"):
            issues.setdefault(e["issue"], []).append(e)
    out = []
    for issue, evs in issues.items():
        def of(kind: str) -> list[dict]:
            return [e for e in evs if e["kind"] == kind]
        tier = next((e["tier"] for e in of("spec-approved")), "?")
        rulings, reviews = len(of("ruling")), of("review-round")
        cap = CAPS[tier] + rulings if tier in CAPS else "?"
        prs = list(dict.fromkeys(e["pr"] for e in of("pr-opened")))
        if prs:
            outcome = json.loads(gh(["pr", "view", prs[-1], "--json", "state"]).stdout)["state"].lower()
        elif of("decision-needed") and not of("decision-made"):
            outcome = "parked"
        elif of("blocked"):
            outcome = "blocked"
        elif cap != "?" and len(reviews) > cap:
            outcome = "capped"
        else:
            outcome = "abandoned"
        out.append({
            "date": (evs[0].get("ts") or evs[0]["run"])[:10], "repo": repo, "ticket": f"#{issue}", "pr": ", ".join(prs) or "—",
            "variant": "fallback" if of("fallback") else "codex", "tier": tier,
            "plan rounds": str(len(of("plan-review"))), "rounds": f"{len(reviews)}/{cap}",
            "findings": ",".join(findings_of(e["verdict"]) for e in reviews) or "—",
            "rulings": str(rulings), "blocked": str(len(of("blocked"))), "gate miss": str(len(of("gate-miss"))),
            "lead": str(len(of("lead-finding"))), "outcome": outcome,
        })
    return out


def render_row(row: dict) -> str:
    return "| " + " | ".join(row[c] for c in COLUMNS) + " |"


def countable(row: dict) -> bool:
    """A row the ledger can hold: its build recorded a spec-approved tier, so its counts are real."""
    return row["tier"] != "?"


def append_rows(ledger: pathlib.Path, new_rows: list[dict]) -> int:
    """Insert countable rows after the table's last row, skipping any whose date, repo and ticket are there."""
    lines = ledger.read_text().splitlines()
    last = max(i for i, ln in enumerate(lines) if ln.startswith("|"))
    present = {tuple(c.strip() for c in ln.strip("|").split("|")[:3]) for ln in lines if ln.startswith("|")}
    fresh = [render_row(r) for r in new_rows
             if countable(r) and (r["date"], r["repo"], r["ticket"]) not in present]
    if not fresh:
        return 0
    ledger.write_text("\n".join(lines[:last + 1] + fresh + lines[last + 1:]) + "\n")
    return len(fresh)


def machine() -> str:
    if sys.platform == "darwin":
        return "mac"
    return "windows" if "microsoft" in platform.release().lower() else "linux"


def friction_line(date: str, repo: str, issue: str, text: str) -> str:
    return f"- {date} {repo} #{issue} ({machine()}): {text}"


def friction_append(ledger: pathlib.Path, slug: str, title: str, line: str) -> int:
    """File `line` under class `slug` (a new class needs `title`); return the class's event count."""
    lines = ledger.read_text().splitlines()
    head = next((i for i, ln in enumerate(lines) if re.match(rf"## {re.escape(slug)}( \(|$)", ln)), None)
    if head is None:
        if not title:
            raise SystemExit(f"new class {slug} needs --title")
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", f"## {slug} ({title})", line]
        ledger.write_text("\n".join(lines) + "\n")
        return 1
    end = next((i for i in range(head + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    last_bullet = max((i for i in range(head + 1, end) if lines[i].startswith("- ") or lines[i].startswith("  ")),
                      default=head)
    lines.insert(last_bullet + 1, line)
    ledger.write_text("\n".join(lines) + "\n")
    return class_counts(ledger)[slug]


def class_counts(ledger: pathlib.Path) -> dict[str, int]:
    """Each friction class's event count: its dated bullets, not its outcome lines."""
    counts: dict[str, int] = {}
    slug = None
    for ln in ledger.read_text().splitlines() if ledger.exists() else []:
        if ln.startswith("## "):
            slug = ln[3:].split(" (", 1)[0].strip()
            counts[slug] = 0
        elif slug and re.match(r"- \d{4}-\d{2}-\d{2} ", ln) and "**outcome" not in ln:
            counts[slug] += 1
    return counts


def retros(main: pathlib.Path, events: list[dict]) -> list[pathlib.Path]:
    issues = {e["issue"] for e in events if e.get("issue")}
    return sorted(p for p in main.glob("RETRO-*-*.md") if p.name.split("-")[1] in issues)


def run_level_retros(main: pathlib.Path) -> list[pathlib.Path]:
    """Retro files not tied to an issue (the lead's own, a second day's): the librarian decides whether
    each belongs to this run from its date and content."""
    return sorted(p for p in main.glob("RETRO-*-*.md") if not p.name.split("-")[1][:1].isdigit())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("report", "ledger-rows", "append-ledger", "friction"):
        sub.add_parser(name)
    fa = sub.add_parser("friction-append")
    fa.add_argument("--class", dest="slug", required=True)
    fa.add_argument("--title", default="")
    fa.add_argument("--issue", required=True)
    fa.add_argument("--text", required=True)
    fa.add_argument("--date", default=datetime.date.today().isoformat())
    for p in sub.choices.values():
        p.add_argument("--repo", default=".")
        p.add_argument("--ledger")
    a = ap.parse_args(argv)
    repo = pathlib.Path(a.repo)
    main_dir = main_checkout(repo)
    events = runlog.latest_run(repo)
    if a.cmd == "friction-append":
        line = friction_line(a.date, main_dir.name, a.issue, a.text)
        n = friction_append(pathlib.Path(a.ledger) if a.ledger else FRICTION_LEDGER, a.slug, a.title, line)
        print(f"{a.slug}: {n} event{'s' if n != 1 else ''}" + (" — GRADUATES (propose a rule)" if n == 2 else ""))
        return 0
    if a.cmd == "friction":
        for e in events:
            if e["kind"] == "friction":
                print(f"#{e.get('issue', '?')} {e['agent']}: {e['text']}")
        for p in retros(main_dir, events):
            print(f"retro {p}")
        for p in run_level_retros(main_dir):
            modified = datetime.date.fromtimestamp(p.stat().st_mtime).isoformat()
            print(f"retro? {p} (not tied to an issue; modified {modified})")
        return 0
    table = rows(events, main_dir.name, gh_runner(main_dir))
    if a.cmd == "ledger-rows":
        for r in table:
            print(render_row(r))
    elif a.cmd == "append-ledger":
        added = append_rows(pathlib.Path(a.ledger) if a.ledger else HERD_LEDGER, table)
        skipped = sum(not countable(r) for r in table)
        print(f"appended {added} rows" + (f"; skipped {skipped} with no review counts (no spec-approved)"
                                          if skipped else ""))
    else:
        if events:
            print(f"run {events[0]['run']}: {events[0].get('text', '(no description)')}")
        for ln in runlog.status(events):
            print(ln)
        for r in table:
            print(f"#{r['ticket'][1:]} outcome={r['outcome']} rounds={r['rounds']} findings={r['findings']}")
        print(f"friction lines: {sum(e['kind'] == 'friction' for e in events)}; retro files: "
              f"{len(retros(main_dir, events))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
