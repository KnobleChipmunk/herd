"""The lifecycle of a librarian proposal: list what is pending, record a decision, notice a merge.

usage: proposals.py list [--all] [--status STATUS] [--ledger PATH]
       proposals.py set <stem> <status> [--pr URL]
       proposals.py sync

A proposal's decision is one `Status:` line under its title: `open` (the
default for a file without one), `accepted`, `in-pr <url>`, `applied <url>
<merge date>`, or `rejected`. `list` ranks pending proposals by their class's
event count in the friction ledger. `sync` asks gh about every `in-pr`
proposal and marks the merged ones applied, so the librarian grades only a
change that actually landed.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import re
import sys

from librarian import FRICTION_LEDGER, class_counts
from merge_stack import gh_runner

FOLDER = pathlib.Path(__file__).resolve().parent.parent / "proposals"
STATUSES = ("open", "accepted", "in-pr", "applied", "rejected")
PENDING = ("open", "accepted", "in-pr")
COMMANDS = ("list", "set", "sync")
_STATUS = re.compile(r"^Status: (\S+)(?: (.*))?$", re.M)


@dataclasses.dataclass
class Proposal:
    path: pathlib.Path
    stem: str
    slug: str
    title: str
    status: str
    note: str
    events: int | None


def parse(path: pathlib.Path, counts: dict[str, int]) -> Proposal:
    text = path.read_text()
    title = text.splitlines()[0].removeprefix("# Proposal:").strip() if text else path.stem
    m = _STATUS.search(text)
    klass = re.search(r"^## Class\s*\n+(\S+)", text, re.M)
    slug = klass.group(1) if klass else path.stem.split("-", 3)[-1]
    return Proposal(path, path.stem, slug, title, m.group(1) if m else "open", (m.group(2) or "") if m else "",
                    counts.get(slug))


def load(folder: pathlib.Path, ledger: pathlib.Path) -> list[Proposal]:
    counts = class_counts(ledger)
    return [parse(p, counts) for p in sorted(folder.glob("*.md"))]


def render(props: list[Proposal], statuses: tuple[str, ...] = STATUSES) -> list[str]:
    shown = [p for p in props if p.status in statuses]
    shown.sort(key=lambda p: (-(p.events or 0), p.stem))
    return [f"{p.stem}  {p.status}{(' ' + p.note) if p.note else ''}  "
            f"{'?' if p.events is None else p.events} events  {p.title}" for p in shown]


def set_status(path: pathlib.Path, status: str, pr: str = "") -> None:
    if status not in STATUSES:
        raise SystemExit(f"unknown status {status}; one of {', '.join(STATUSES)}")
    if status in ("in-pr", "applied") and not pr:
        raise SystemExit(f"{status} needs --pr")
    line = f"Status: {status}{(' ' + pr) if pr else ''}"
    text = path.read_text()
    if _STATUS.search(text):
        text = _STATUS.sub(line, text, count=1)
    else:
        title, _, rest = text.partition("\n")
        text = f"{title}\n\n{line}\n{rest}" if rest.startswith("\n") else f"{title}\n\n{line}\n\n{rest}"
    path.write_text(text)


def sync(props: list[Proposal], gh) -> list[str]:
    changed = []
    for p in props:
        if p.status != "in-pr" or not p.note:
            continue
        url = p.note.split()[0]
        r = gh(["pr", "view", url, "--json", "state,mergedAt"])
        if r.returncode != 0:
            print(f"{p.stem}: gh could not read {url}: {(r.stderr or r.stdout).strip()}", file=sys.stderr)
            continue
        info = json.loads(r.stdout)
        if info.get("state") == "MERGED":
            set_status(p.path, "applied", f"{url} {(info.get('mergedAt') or '')[:10]}".strip())
            changed.append(p.stem)
    return changed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list")
    ls.add_argument("--all", action="store_true")
    ls.add_argument("--status", choices=STATUSES)
    ls.add_argument("--ledger")
    st = sub.add_parser("set")
    st.add_argument("stem")
    st.add_argument("status")
    st.add_argument("--pr", default="")
    sub.add_parser("sync")
    a = ap.parse_args(argv)
    if a.cmd == "set":
        path = FOLDER / f"{a.stem.removesuffix('.md')}.md"
        if not path.exists():
            raise SystemExit(f"no proposal {path}")
        set_status(path, a.status, a.pr)
        print(f"{path.stem}: {a.status}{(' ' + a.pr) if a.pr else ''}")
        return 0
    props = load(FOLDER, pathlib.Path(getattr(a, "ledger", None) or FRICTION_LEDGER))
    if a.cmd == "sync":
        changed = sync(props, gh_runner(FOLDER.parent))
        print(f"applied: {', '.join(changed)}" if changed else "no in-pr proposal has merged")
        return 0
    statuses = (a.status,) if a.status else (STATUSES if a.all else PENDING)
    lines = render(props, statuses)
    print("\n".join(lines) if lines else "no proposals in " + "/".join(statuses))
    return 0


if __name__ == "__main__":
    sys.exit(main())
