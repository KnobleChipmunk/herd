"""Herd plan tool: one plan module drives apply / mutate / render / parity.

A plan module defines:
  TESTS  = [Step]   test-side steps (applied first, RED observed after)
  IMPL   = [Step]   implementation steps
  MUTATIONS = [(name, relpath, old, new, killer_test_nodeid)]
Step = dict(kind="replace"|"append"|"insert_before"|"new_file", path=..., old=..., new=..., why=...)
  replace:        old text (must occur exactly once) -> new text
  insert_before:  new text inserted immediately before old (unique anchor)
  append:         new text appended at end of file (file must end with exactly one newline)
  new_file:       new is the whole file body

usage: herdtool.py <plan.py> apply-tests|apply-impl|mutate|render|check-applied <worktree>
"""
from __future__ import annotations

import importlib.util
import pathlib
import shutil
import subprocess
import sys

PY = "/home/tusk/projects/project-mera/.venv/bin/python"


def base_text(ref: str, base: str, rel: str) -> str:
    return subprocess.run(["git", "-C", ref, "show", f"{base}:{rel}"], capture_output=True, text=True, check=True).stdout


def between(text: str, start: str, end: str) -> str:
    """The unique span from `start` through the first `end` after it, inclusive."""
    assert text.count(start) == 1, ("start not unique", start[:50])
    i = text.index(start); j = text.index(end, i) + len(end)
    return text[i:j]


def load(plan_path: str):
    spec = importlib.util.spec_from_file_location("plan", plan_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def apply_step(w: pathlib.Path, step: dict) -> None:
    path = w / step["path"]
    kind = step["kind"]
    if kind == "new_file":
        assert not path.exists(), (step["path"], "already exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(step["new"], encoding="utf-8")
        return
    if kind == "whole_file":
        assert path.exists(), (step["path"], "does not exist")
        path.write_text(step["new"], encoding="utf-8")
        return
    text = path.read_text(encoding="utf-8")
    if kind == "append":
        assert text.endswith("\n") and not text.endswith("\n\n"), (step["path"], "file end not a single newline")
        path.write_text(text + step["new"], encoding="utf-8")
        return
    old = step["old"]
    assert text.count(old) == 1, (step["path"], "anchor count", text.count(old), old[:60])
    if kind == "replace":
        path.write_text(text.replace(old, step["new"], 1), encoding="utf-8")
    elif kind == "insert_before":
        path.write_text(text.replace(old, step["new"] + old, 1), encoding="utf-8")
    else:
        raise ValueError(kind)


def is_applied(w: pathlib.Path, step: dict) -> bool:
    path = w / step["path"]
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if step["kind"] in ("new_file", "whole_file"):
        return text == step["new"]
    if step["kind"] == "append":
        return text.endswith(step["new"])
    if step["kind"] == "insert_before":
        return text.count(step["new"] + step["old"]) == 1
    return text.count(step["new"]) >= 1 and (step["old"] not in text or step["old"] in step["new"])


def mutate(w: pathlib.Path, muts: list) -> int:
    survived = 0
    for name, rel, old, new, test in muts:
        path = w / rel
        orig = path.read_text(encoding="utf-8")
        assert orig.count(old) == 1, (name, "anchor not unique", orig.count(old))
        path.write_text(orig.replace(old, new, 1), encoding="utf-8")
        try:
            for pc in (w / "src").rglob("__pycache__"):
                shutil.rmtree(pc, ignore_errors=True)
            r = subprocess.run(
                [PY, "-m", "pytest", *test.split(), "-q", "--no-header", "-p", "no:cacheprovider", "-x"],
                cwd=w, capture_output=True, text=True,
                env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
                     "HOME": "/home/tusk"},
            )
        finally:
            path.write_text(orig, encoding="utf-8")
        verdict = "KILLED" if r.returncode else "SURVIVED"
        survived += r.returncode == 0
        fail = next((ln for ln in r.stdout.splitlines() if ln.startswith(("FAILED", "ERROR"))), "")
        print(f"{name} {verdict} {fail[:150]}")
    return survived


def lang_of(path: str) -> str:
    return "html" if path.endswith(".html") else "python"


def fence(text: str, lang: str = "python") -> str:
    ticks = "````" if "```" in text else "```"
    return f"{ticks}{lang}\n{text}{'' if text.endswith(chr(10)) else chr(10)}{ticks}\n"


def render_steps(steps: list, start: int, prefix: str) -> str:
    out = []
    for i, s in enumerate(steps, start):
        head = f"- [ ] **{prefix}{i}** `{s['path']}` — {s['why']}\n\n"
        k = s["kind"]
        if k == "new_file":
            body = "Create this file with exactly this body (byte-exact, ends with one newline):\n\n" + fence(s["new"], lang_of(s["path"]))
        elif k == "whole_file":
            body = ("REPLACE THE WHOLE FILE. Delete everything in it and write exactly this body "
                    "(byte-exact, ends with one newline):\n\n" + fence(s["new"], lang_of(s["path"])))
        elif k == "append":
            body = ("Append exactly this text at the END of the file. The fence below BEGINS with the blank "
                    "lines that separate it from the existing last line — keep them. The file must end with one newline:\n\n"
                    + fence(s["new"], lang_of(s["path"])))
        elif k == "insert_before":
            body = ("Find this exact text (it occurs exactly once):\n\n" + fence(s["old"], lang_of(s["path"])) +
                    "\nInsert exactly this text IMMEDIATELY BEFORE it (the fence carries its own trailing blank lines):\n\n"
                    + fence(s["new"], lang_of(s["path"])))
        elif s.get("old_desc"):
            body = s["old_desc"] + "\n\nReplace it with exactly:\n\n" + fence(s["new"], lang_of(s["path"]))
        else:
            body = ("Find this exact text (it occurs exactly once):\n\n" + fence(s["old"], lang_of(s["path"])) +
                    "\nReplace it with exactly:\n\n" + fence(s["new"], lang_of(s["path"])))
        out.append(head + body)
    return "\n".join(out)


def main() -> None:
    plan = load(sys.argv[1])
    cmd = sys.argv[2]
    w = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else None
    if cmd == "apply-tests":
        for s in plan.TESTS:
            apply_step(w, s)
        print("applied", len(plan.TESTS), "test steps")
    elif cmd == "apply-impl":
        for s in plan.IMPL:
            apply_step(w, s)
        print("applied", len(plan.IMPL), "impl steps")
    elif cmd == "mutate":
        sys.exit(1 if mutate(w, plan.MUTATIONS) else 0)
    elif cmd == "check-applied":
        bad = [s["path"] + ":" + s["why"][:40] for s in plan.TESTS + plan.IMPL if not is_applied(w, s)]
        print("PARITY OK" if not bad else "PARITY FAIL: " + "; ".join(bad))
        sys.exit(1 if bad else 0)
    elif cmd == "render":
        print("## 1. Tests first (expect RED)\n")
        print(render_steps(plan.TESTS, 1, "T"))
        print("\n## 2. Implementation (expect GREEN)\n")
        print(render_steps(plan.IMPL, 1, "I"))
        print("\n## 3. Mutation drives (each must be KILLED; restore the file after each)\n")
        for name, rel, old, new, test in plan.MUTATIONS:
            print(f"- [ ] **{name}** in `{rel}`: replace\n\n{fence(old, lang_of(rel))}\nwith\n\n{fence(new, lang_of(rel))}\nKiller: `{test}`\n")
    else:
        raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    main()
