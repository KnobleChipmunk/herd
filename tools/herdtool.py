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

The interpreter is $HERD_PYTHON, else the main checkout's .venv, else this one.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys


def git_common_dir(w: pathlib.Path) -> pathlib.Path:
    """The .git directory shared by the primary checkout and all its linked worktrees."""
    common = subprocess.run(["git", "-C", str(w), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                            capture_output=True, text=True, check=True).stdout.strip()
    return pathlib.Path(common).resolve()


def main_checkout(w: pathlib.Path) -> pathlib.Path:
    """The primary checkout that `w` (a linked worktree or the checkout itself) belongs to."""
    return git_common_dir(w).parent


def find_python(w: pathlib.Path) -> str:
    if os.environ.get("HERD_PYTHON"):
        return os.environ["HERD_PYTHON"]
    venv_py = main_checkout(w) / ".venv" / "bin" / "python"
    return str(venv_py) if venv_py.exists() else sys.executable


def mutate_env() -> dict[str, str]:
    """A pinned environment for the drives, plus node's directory: page tests
    run under node and skip without it, and a skipped killer proves nothing."""
    path = ["/usr/bin", "/bin"]
    node = shutil.which("node")
    if node and str(pathlib.Path(node).parent) not in path:
        path.append(str(pathlib.Path(node).parent))
    return {"PYTHONPATH": "src", "PATH": ":".join(path), "PYTHONDONTWRITEBYTECODE": "1",
            "HOME": str(pathlib.Path.home())}


def base_text(ref: str, base: str, rel: str) -> str:
    return subprocess.run(["git", "-C", ref, "show", f"{base}:{rel}"], capture_output=True, text=True, check=True).stdout


def between(text: str, start: str, end: str) -> str:
    """The unique span from `start` through the first `end` after it, inclusive."""
    assert text.count(start) == 1, ("start not unique", start[:50])
    i = text.index(start)
    j = text.index(end, i) + len(end)
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


def first_diff_line(a: str, b: str) -> int:
    la, lb = a.splitlines(keepends=True), b.splitlines(keepends=True)
    return next((i for i, (x, y) in enumerate(zip(la, lb), 1) if x != y), min(len(la), len(lb)) + 1)


def step_problem(w: pathlib.Path, step: dict) -> str | None:
    """Why `step` is not applied in worktree `w`, or None when it is."""
    path = w / step["path"]
    if not path.exists():
        return "file missing"
    text = path.read_text(encoding="utf-8")
    if step["kind"] in ("new_file", "whole_file"):
        return None if text == step["new"] else f"file differs from the fence at line {first_diff_line(text, step['new'])}"
    if step["kind"] == "append":
        return None if text.endswith(step["new"]) else "file does not end with the appended text"
    if step["kind"] == "insert_before":
        ok = text.count(step["new"] + step["old"]) == 1
        return None if ok else "inserted text not found exactly once before its anchor"
    if step["new"] not in text:
        return "replacement text not found"
    old = step.get("old")
    if old is not None and old in text and old not in step["new"]:
        return "replaced text still present"
    return None


def is_applied(w: pathlib.Path, step: dict) -> bool:
    return step_problem(w, step) is None


def porcelain(w: pathlib.Path) -> str | None:
    r = subprocess.run(["git", "-C", str(w), "status", "--porcelain"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def content_hashes(w: pathlib.Path) -> dict[str, str]:
    """A hash of every modified or untracked file. The status letter of a file
    that was already changed does not move when a test rewrites it again."""
    r = subprocess.run(["git", "-C", str(w), "status", "--porcelain", "-z", "-uall"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return {}
    paths = [e[3:] for e in r.stdout.split("\0") if len(e) > 3 and e[3:] and (w / e[3:]).is_file()]
    if not paths:
        return {}
    h = subprocess.run(["git", "-C", str(w), "hash-object", "--stdin-paths"],
                       input="\n".join(paths) + "\n", capture_output=True, text=True)
    return dict(zip(paths, h.stdout.split(), strict=True)) if h.returncode == 0 else {}


# A drive killed mid-mutation never reaches its `finally`, so the file stays
# mutated and the next run sees a VOID anchor or, worse, builds on it. The
# drive records what it is about to change, and every run restores first.
INFLIGHT = ".herd-mutate-inflight.json"


def inflight_path(w: pathlib.Path) -> pathlib.Path:
    return w / INFLIGHT


def write_inflight(w: pathlib.Path, path: pathlib.Path, original: str) -> None:
    inflight_path(w).write_text(json.dumps({"path": str(path.relative_to(w)), "original": original}),
                                encoding="utf-8")


def restore_inflight(w: pathlib.Path) -> str | None:
    """Put back a file an interrupted drive left mutated; the line to report, or None."""
    journal = inflight_path(w)
    if not journal.exists():
        return None
    record = json.loads(journal.read_text(encoding="utf-8"))
    journal.unlink()
    target = (w / record["path"]).resolve()
    # The journal is data on disk: never let it name a file outside the tree.
    if not target.is_relative_to(w.resolve()):
        return f"REFUSED an interrupted-drive journal naming {record['path']}, outside the tree"
    target.write_text(record["original"], encoding="utf-8")
    return f"RESTORED {record['path']}, left mutated by an interrupted drive"


def verdict(returncode: int, stdout: str) -> tuple[str, str]:
    """KILLED, SURVIVED, or NOT RUN, and the line that shows it.

    Only a failing or erroring test is a kill, and only a passing one a
    survival. A skip, a deselection, or a killer id pytest cannot resolve ran
    nothing, and says nothing about the mutation."""
    fail = next((ln for ln in stdout.splitlines() if ln.startswith(("FAILED", "ERROR"))), "")
    if returncode != 0 and fail:
        return "KILLED", fail
    summary = next((ln for ln in reversed(stdout.splitlines()) if ln.strip()), "")
    if returncode == 0 and re.search(r"\b\d+ passed", summary):
        return "SURVIVED", ""
    return "NOT RUN", summary or f"pytest exited {returncode} with no output"


def run_mutations(w: pathlib.Path, muts: list, py: str) -> tuple[list[str], int]:
    """Drive each (name, relpath, old, new, killer) once; return report lines and the failure count.

    A failure is a survivor, a void drive (anchor not exactly once), or a tree
    left changed after the drives (a test with side effects, a failed restore).
    """
    lines, failures = [], 0
    restored = restore_inflight(w)
    if restored:
        lines.append(restored)
        failures += restored.startswith("REFUSED")
    before = porcelain(w)
    before_content = content_hashes(w)
    for name, rel, old, new, test in muts:
        path = w / rel
        orig = path.read_text(encoding="utf-8")
        if orig.count(old) != 1:
            lines.append(f"{name} VOID anchor occurs {orig.count(old)} times in {rel}")
            failures += 1
            continue
        write_inflight(w, path, orig)
        path.write_text(orig.replace(old, new, 1), encoding="utf-8")
        try:
            for pc in w.rglob("__pycache__"):
                shutil.rmtree(pc, ignore_errors=True)
            r = subprocess.run(
                [py, "-B", "-m", "pytest", *test.split(), "-q", "--no-header", "-p", "no:cacheprovider", "-x"],
                cwd=w, capture_output=True, text=True, env=mutate_env(),
            )
        finally:
            path.write_text(orig, encoding="utf-8")
            inflight_path(w).unlink(missing_ok=True)
        result, shown = verdict(r.returncode, r.stdout)
        failures += result != "KILLED"
        lines.append(f"{name} {result} {shown[:150]}".rstrip())
    after = porcelain(w)
    after_content = content_hashes(w)
    changed = []
    if before is not None and after is not None and after != before:
        changed += sorted(set(after.splitlines()) - set(before.splitlines()))
    changed += [f"content of {p}" for p in sorted(before_content)
                if p in after_content and after_content[p] != before_content[p]]
    if changed:
        lines.append("TREE CHANGED after the drives: " + "; ".join(changed))
        failures += 1
    return lines, failures


def mutate(w: pathlib.Path, muts: list) -> int:
    lines, failures = run_mutations(w, muts, find_python(w))
    for ln in lines:
        print(ln)
    return failures


def forms(rendered: str) -> list[str]:
    """The texts a rendered fence body can have come from, exact first.

    fence() adds a newline only to text that lacks one, so the body without its
    last newline is a possible source only if it does not itself end in one.
    """
    stripped = rendered[:-1]
    return [rendered] if stripped.endswith("\n") else [rendered, stripped]


def lang_of(path: str) -> str:
    return "html" if path.endswith(".html") else "python"


def fence(text: str, lang: str = "python") -> str:
    ticks = "````" if "```" in text else "```"
    return f"{ticks}{lang}\n{text}{'' if text.endswith(chr(10)) else chr(10)}{ticks}\n"


CREATE = "Create this file with exactly this body (byte-exact, ends with one newline):"
WHOLE = ("REPLACE THE WHOLE FILE. Delete everything in it and write exactly this body "
         "(byte-exact, ends with one newline):")
APPEND = ("Append exactly this text at the END of the file. The fence below BEGINS with the blank "
          "lines that separate it from the existing last line — keep them. The file must end with one newline:")
FIND = "Find this exact text (it occurs exactly once):"
INSERT = "Insert exactly this text IMMEDIATELY BEFORE it (the fence carries its own trailing blank lines):"
REPLACE_WITH = "Replace it with exactly:"


def render_steps(steps: list, start: int, prefix: str) -> str:
    out = []
    for i, s in enumerate(steps, start):
        head = f"- [ ] **{prefix}{i}** `{s['path']}` — {s['why']}\n\n"
        k = s["kind"]
        lang = lang_of(s["path"])
        if k == "new_file":
            body = f"{CREATE}\n\n" + fence(s["new"], lang)
        elif k == "whole_file":
            body = f"{WHOLE}\n\n" + fence(s["new"], lang)
        elif k == "append":
            body = f"{APPEND}\n\n" + fence(s["new"], lang)
        elif k == "insert_before":
            body = f"{FIND}\n\n" + fence(s["old"], lang) + f"\n{INSERT}\n\n" + fence(s["new"], lang)
        elif s.get("old_desc"):
            body = s["old_desc"] + f"\n\n{REPLACE_WITH}\n\n" + fence(s["new"], lang)
        else:
            body = f"{FIND}\n\n" + fence(s["old"], lang) + f"\n{REPLACE_WITH}\n\n" + fence(s["new"], lang)
        out.append(head + body)
    return "\n".join(out)


def render_mutations(muts: list) -> str:
    out = []
    for name, rel, old, new, test in muts:
        lang = lang_of(rel)
        out.append(f"- [ ] **{name}** in `{rel}`: replace\n\n{fence(old, lang)}\nwith\n\n{fence(new, lang)}\n"
                   f"Killer: `{test}`\n\n")
    return "".join(out)


MUT_HEAD = re.compile(r"^- \[ \] \*\*(M[^*]*)\*\* in `([^`]+)`: replace\n", re.M)
KILLER = re.compile(r"^Killer: `([^`]+)`", re.M)


def parse_mutations(text: str) -> list[dict]:
    """The mutations of a tasks.md written by render_mutations, bodies as rendered."""
    heads = list(MUT_HEAD.finditer(text))
    muts = []
    for n, h in enumerate(heads):
        seg = text[h.end():heads[n + 1].start() if n + 1 < len(heads) else len(text)]
        bodies = [m.group(2) for m in FENCE_BODY.finditer(seg)]
        muts.append({"name": h.group(1), "path": h.group(2), "old": bodies[0], "new": bodies[1],
                     "test": KILLER.search(seg).group(1)})
    return muts


STEP_HEAD = re.compile(r"^- \[ \] \*\*([TI]\d+)\*\* `([^`]+)` — ", re.M)
FENCE_BODY = re.compile(r"^(`{3,4})[\w-]*\n(.*?)^\1\n", re.M | re.S)


def parse_tasks(text: str) -> list[dict]:
    """The T/I steps of a tasks.md written by render_steps, bodies as rendered (always newline-terminated)."""
    heads = list(STEP_HEAD.finditer(text))
    steps = []
    for n, h in enumerate(heads):
        seg = text[h.end():heads[n + 1].start() if n + 1 < len(heads) else len(text)]
        fences = list(FENCE_BODY.finditer(seg))
        # The step ends at the first `## ` heading outside a fence; one inside a fence is file content.
        pos = seg.find("\n## ")
        while pos != -1 and any(f.start() <= pos < f.end() for f in fences):
            pos = seg.find("\n## ", pos + 1)
        if pos != -1:
            seg = seg[:pos]
        bodies = [m.group(2) for m in fences if m.end() <= len(seg)]
        step = {"name": h.group(1), "path": h.group(2), "old": None}
        if WHOLE in seg:
            step.update(kind="whole_file", new=bodies[0])
        elif CREATE in seg:
            step.update(kind="new_file", new=bodies[0])
        elif APPEND in seg:
            step.update(kind="append", new=bodies[0])
        elif INSERT in seg:
            step.update(kind="insert_before", old=bodies[0], new=bodies[1])
        elif FIND in seg:
            step.update(kind="replace", old=bodies[0], new=bodies[1])
        else:
            step.update(kind="replace", new=bodies[0])
        steps.append(step)
    return steps


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
        print(render_mutations(plan.MUTATIONS), end="")
    else:
        raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    main()
