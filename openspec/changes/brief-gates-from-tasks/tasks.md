# Tasks: briefing gates from tasks.md

DEPENDS ON PR #66, pinned base d6b0ed7.

## 0. Gates

Baseline d6b0ed7 measured in /tmp/herd-proposal-gates-reference: `510 passed in 10.22s`, Ruff `All checks passed!`. Build adds seven test cases: expect 517 passed. Observed reference full suite: `517 passed in 10.42s`.
Touched suite `python3 -m pytest tests/test_mkbrief.py -q --no-header`: baseline 26, build 33 passed (observed 33 passed in 0.80s).
Touched RED after section 1, before section 2: run `PYTHONPATH=src python3 -m pytest tests/test_mkbrief.py -q --no-header` in this build worktree; expect 30 failed, 3 passed (observed 30 failed, 3 passed in 0.61s during literal replay). Preserve the tail.
After implementation run `python3 /home/tusk/projects/herd/tools/gates.py suite-ok --issue proposal-gates` then `python3 -m pytest -q` once; expected baseline +7 = 517 passed. Reference duration 10.42 seconds. Run `ruff check tools tests`: All checks passed! (identical to baseline).
Type checking NOT CHECKED: no configured project command, mypy absent. pytest-xdist absent; run serially.
Literal gate: `python3 tools/gates.py count 'task_gates(worktree, change)' tools/mkbrief.py`: baseline 0, build 1.
Fence gate: `python3 /home/tusk/projects/herd/tools/fencecheck.py openspec/changes/brief-gates-from-tasks/tasks.md .`: FENCES OK (12 steps).
Mutation names: M1, M2, M3, M4, M5. Run all five with `python3 /home/tusk/projects/herd/tools/mutate.py openspec/changes/brief-gates-from-tasks/tasks.md .`; all must be KILLED. Pre-execution observed M1 KILLED by the CLI-regeneration test, M2 KILLED by the invalid-gate test, and M3/M4 KILLED by the fenced-heading test. Record the full FAILED lines from your drives.


Fold regression before implementation: 1 failed, 32 passed in 0.91s; indentation and trailing spaces must survive. M5 restores whole-string stripping and must be KILLED by the section-boundary test.


## 1. Tests first

- [ ] **T1** `tests/test_mkbrief.py` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
import pytest

import mkbrief


def brief(repo_with_worktree, **overrides):
    main, wt = repo_with_worktree
    args = dict(id="42", worktree=wt, branch="fix/42-x", base="main", change="fix-x",
                gates="GATES\n", allowed="  - src/x.py", python="/py/bin/python",
                lead_pane="w9:p9Z", reviewer="codex_review", has_xdist=False)
    args.update(overrides)
    return main, wt, mkbrief.build_briefing(**args), mkbrief.build_reviewer_prompt(**args)
```

Replace it with exactly:

```python
import pytest

import mkbrief


def write_tasks(worktree, body="# Plan\n\n## 0. Gates\n\n510 passed\nM1–M5\nFENCES OK (11 steps)\n\n## 1. Tests first\n"):
    path = worktree / "openspec/changes/fix-x/tasks.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return path


def brief(repo_with_worktree, **overrides):
    main, wt = repo_with_worktree
    if not (wt / "openspec/changes/fix-x/tasks.md").exists():
        write_tasks(wt)
    args = dict(id="42", worktree=wt, branch="fix/42-x", base="main", change="fix-x",
                allowed="  - src/x.py", python="/py/bin/python",
                lead_pane="w9:p9Z", reviewer="codex_review", has_xdist=False)
    args.update(overrides)
    return main, wt, mkbrief.build_briefing(**args), mkbrief.build_reviewer_prompt(**args)
```

- [ ] **T2** `tests/test_mkbrief.py` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
    _, wt = repo_with_worktree
    monkeypatch.setenv("HERDR_PANE_ID", "w5:p5A")
    monkeypatch.setenv("HERD_PYTHON", sys.executable)
    gates = tmp_path / "gates.txt"
    gates.write_text("G\n")
    allowed = tmp_path / "allowed.txt"
    allowed.write_text("  - src/x.py\n")
    mkbrief.main(["42", str(wt), "fix/42-x", "main", "fix-x", str(gates), str(allowed)])
    assert "w5:p5A" in (wt / "BUILD-BRIEFING-42.md").read_text()
    assert "codex_review" in (wt / "BUILD-BRIEFING-42.md").read_text()
    assert (wt / "CODEX-PROMPT-42.md").exists()
```

Replace it with exactly:

```python
    _, wt = repo_with_worktree
    monkeypatch.setenv("HERDR_PANE_ID", "w5:p5A")
    monkeypatch.setenv("HERD_PYTHON", sys.executable)
    write_tasks(wt)
    allowed = tmp_path / "allowed.txt"
    allowed.write_text("  - src/x.py\n")
    mkbrief.main(["42", str(wt), "fix/42-x", "main", "fix-x", str(allowed)])
    assert "w5:p5A" in (wt / "BUILD-BRIEFING-42.md").read_text()
    assert "codex_review" in (wt / "BUILD-BRIEFING-42.md").read_text()
    assert (wt / "CODEX-PROMPT-42.md").exists()
```

- [ ] **T3** `tests/test_mkbrief.py` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
    _, wt = repo_with_worktree
    monkeypatch.setenv("HERDR_PANE_ID", "w5:p5A")
    monkeypatch.setenv("HERD_PYTHON", sys.executable)
    gates_file = tmp_path / "gates.txt"
    gates_file.write_text("G\n")
    allowed = tmp_path / "allowed.txt"
    allowed.write_text("  - `src/x.py`\n")
    mkbrief.main(["42", str(wt), "fix/42-x", "main", "fix-x", str(gates_file), str(allowed)])
    assert (wt / "ALLOWED-42.txt").read_text() == "  - `src/x.py`\n  - `openspec/changes/fix-x/`\n"


```

Replace it with exactly:

```python
    _, wt = repo_with_worktree
    monkeypatch.setenv("HERDR_PANE_ID", "w5:p5A")
    monkeypatch.setenv("HERD_PYTHON", sys.executable)
    write_tasks(wt)
    allowed = tmp_path / "allowed.txt"
    allowed.write_text("  - `src/x.py`\n")
    mkbrief.main(["42", str(wt), "fix/42-x", "main", "fix-x", str(allowed)])
    assert (wt / "ALLOWED-42.txt").read_text() == "  - `src/x.py`\n  - `openspec/changes/fix-x/`\n"


```

- [ ] **T4** `tests/test_mkbrief.py` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
    assert "without waiting for a fold" in recovery
    assert "the lead installs any regenerated test fences" in recovery
    assert "re-apply the affected implementation files" in recovery
```

Replace it with exactly:

````python
    assert "without waiting for a fold" in recovery
    assert "the lead installs any regenerated test fences" in recovery
    assert "re-apply the affected implementation files" in recovery


def test_main_regenerates_suite_mutation_and_fence_literals_from_tasks(repo_with_worktree, tmp_path, monkeypatch):
    _, wt = repo_with_worktree
    monkeypatch.setenv("HERD_PYTHON", sys.executable)
    tasks = write_tasks(wt)
    allowed = tmp_path / "allowed.txt"
    allowed.write_text("tools/x.py\n")
    args = ["42", str(wt), "fix/42-x", "main", "fix-x", str(allowed), "--lead-pane", "w5:p5A"]
    mkbrief.main(args)
    first = (wt / "BUILD-BRIEFING-42.md").read_text()
    for literal in ("510 passed", "M1–M5", "FENCES OK (11 steps)"):
        assert literal in first
    tasks.write_text(tasks.read_text().replace("510 passed", "512 passed").replace("M1–M5", "M1–M7")
                     .replace("11 steps", "13 steps"))
    mkbrief.main(args)
    second = (wt / "BUILD-BRIEFING-42.md").read_text()
    for old, new in (("510 passed", "512 passed"), ("M1–M5", "M1–M7"), ("11 steps", "13 steps")):
        assert old not in second and new in second
    before = {p: p.read_bytes() for p in wt.glob("*-42.*")}
    tasks.write_text("# No gates\n")
    with pytest.raises(SystemExit, match="exactly one nonempty.*Gates"):
        mkbrief.main(args)
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("body", ["# no section\n", "## 0. Gates\n\n## 1. Tests\n",
                                   "## 0. Gates\nA\n## 0. Gates\nB\n", "    ## 0. Gates\nbody\n"])
def test_invalid_task_gates_fail_clearly(repo_with_worktree, body):
    _, wt = repo_with_worktree
    write_tasks(wt, body)
    with pytest.raises(SystemExit, match="exactly one nonempty.*Gates"):
        mkbrief.task_gates(wt, "fix-x")


def test_missing_tasks_names_the_unreadable_file(repo_with_worktree):
    _, wt = repo_with_worktree
    with pytest.raises(SystemExit, match="cannot read.*tasks.md"):
        mkbrief.task_gates(wt, "fix-x")


def test_gate_section_respects_fenced_headings_and_stops_at_next_section(repo_with_worktree):
    _, wt = repo_with_worktree
    body = ("# Plan\n````python\n## 0. Gates\nfalse\n````\n## 0. Gates\n"
            "510 passed\n```text\n## example output\n```\n## 1. Tests\nnot a gate\n"
            "~~~text\n## 0. Gates\nfalse again\n~~~\n")
    write_tasks(wt, body)
    assert mkbrief.task_gates(wt, "fix-x") == "510 passed\n```text\n## example output\n```\n"
    write_tasks(wt, "## 0. Gates\n \n    python3 -m pytest  \n\t\n## 1. Tests\n")
    assert mkbrief.task_gates(wt, "fix-x") == "    python3 -m pytest  \n"
````

## 2. Implementation

- [ ] **I1** `tools/mkbrief.py` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
"""Write BUILD-BRIEFING-<id>.md and CODEX-PROMPT-<id>.md into a build worktree.

usage: mkbrief.py <id> <worktree> <branch> <base-desc> <change-name> <gates-file> <allowed-files-file>
                  [--lead-pane <pane>] [--reviewer <agent name>]

The lead pane defaults to $HERDR_PANE_ID (run this from the lead's pane); the
```

Replace it with exactly:

```python
"""Write BUILD-BRIEFING-<id>.md and CODEX-PROMPT-<id>.md into a build worktree.

usage: mkbrief.py <id> <worktree> <branch> <base-desc> <change-name> <allowed-files-file>
                  [--lead-pane <pane>] [--reviewer <agent name>]

The lead pane defaults to $HERDR_PANE_ID (run this from the lead's pane); the
```

- [ ] **I2** `tools/mkbrief.py` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
import argparse
import os
import pathlib
import subprocess

import fencecheck
```

Replace it with exactly:

```python
import argparse
import os
import pathlib
import re
import subprocess

import fencecheck
```

- [ ] **I3** `tools/mkbrief.py` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
    return subprocess.run([python, "-c", "import xdist"], capture_output=True).returncode == 0


def build_briefing(*, id: str, worktree: pathlib.Path, branch: str, base: str, change: str, gates: str,
                   allowed: str, python: str, lead_pane: str, reviewer: str, has_xdist: bool) -> str:
    main = main_checkout(worktree)
    sha = base_sha(worktree, base)
    xdist = ("`pytest-xdist` is installed; the gates in tasks.md say whether to use it."
```

Replace it with exactly:

```python
    return subprocess.run([python, "-c", "import xdist"], capture_output=True).returncode == 0


def task_gates(worktree: pathlib.Path, change: str) -> str:
    path = worktree / "openspec" / "changes" / change / "tasks.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"cannot read {path}: {exc}") from exc
    blocks: list[list[str]] = []
    current: list[str] | None = None
    fence = ""
    for line in text.splitlines(keepends=True):
        if fence:
            if current is not None:
                current.append(line)
            if re.fullmatch(r" {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t]*\n?", line):
                fence = ""
            continue
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            fence = marker.group(1)
            if current is not None:
                current.append(line)
        elif re.fullmatch(r" {0,3}## 0\. Gates[ \t]*\n?", line):
            current = []
            blocks.append(current)
        elif re.match(r"^ {0,3}##(?:\s|$)", line):
            current = None
        elif current is not None:
            current.append(line)
    if len(blocks) != 1 or not "".join(blocks[0]).strip():
        raise SystemExit(f"{path} must contain exactly one nonempty '## 0. Gates' section")
    lines = blocks[0]
    while not lines[0].strip():
        lines.pop(0)
    while not lines[-1].strip():
        lines.pop()
    return "".join(lines).rstrip("\n") + "\n"


def build_briefing(*, id: str, worktree: pathlib.Path, branch: str, base: str, change: str,
                   allowed: str, python: str, lead_pane: str, reviewer: str, has_xdist: bool) -> str:
    gate_text = task_gates(worktree, change)
    main = main_checkout(worktree)
    sha = base_sha(worktree, base)
    xdist = ("`pytest-xdist` is installed; the gates in tasks.md say whether to use it."
```

- [ ] **I4** `tools/mkbrief.py` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
Check each with `python3 {GATES} match "<expected line>" <output file>`: it prints
MATCH, or the counts that differ. pytest's warnings and wall time do not count.

{gates}
## The spec — read in this order

1. `openspec/changes/{change}/proposal.md`
```

Replace it with exactly:

```python
Check each with `python3 {GATES} match "<expected line>" <output file>`: it prints
MATCH, or the counts that differ. pytest's warnings and wall time do not count.

{gate_text}
## The spec — read in this order

1. `openspec/changes/{change}/proposal.md`
```

- [ ] **I5** `tools/mkbrief.py` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python

def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("id", "worktree", "branch", "base", "change", "gates_file", "allowed_file"):
        ap.add_argument(name)
    ap.add_argument("--lead-pane")
    ap.add_argument("--reviewer", default="codex_review")
```

Replace it with exactly:

```python

def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("id", "worktree", "branch", "base", "change", "allowed_file"):
        ap.add_argument(name)
    ap.add_argument("--lead-pane")
    ap.add_argument("--reviewer", default="codex_review")
```

- [ ] **I6** `tools/mkbrief.py` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
    w = pathlib.Path(a.worktree)
    python = find_python(w)
    args = dict(id=a.id, worktree=w, branch=a.branch, base=a.base, change=a.change,
                gates=pathlib.Path(a.gates_file).read_text(),
                allowed=pathlib.Path(a.allowed_file).read_text().rstrip(),
                python=python, lead_pane=resolve_lead_pane(a.lead_pane), reviewer=a.reviewer,
                has_xdist=has_xdist(python))
    (w / f"ALLOWED-{a.id}.txt").write_text(args["allowed"] + f"\n  - `openspec/changes/{a.change}/`\n")
    (w / f"BUILD-BRIEFING-{a.id}.md").write_text(build_briefing(**args))
    (w / f"CODEX-PROMPT-{a.id}.md").write_text(build_reviewer_prompt(**args))
    print("wrote briefing + codex prompt in", w)


```

Replace it with exactly:

```python
    w = pathlib.Path(a.worktree)
    python = find_python(w)
    args = dict(id=a.id, worktree=w, branch=a.branch, base=a.base, change=a.change,
                allowed=pathlib.Path(a.allowed_file).read_text().rstrip(),
                python=python, lead_pane=resolve_lead_pane(a.lead_pane), reviewer=a.reviewer,
                has_xdist=has_xdist(python))
    briefing = build_briefing(**args)
    reviewer_prompt = build_reviewer_prompt(**args)
    (w / f"ALLOWED-{a.id}.txt").write_text(args["allowed"] + f"\n  - `openspec/changes/{a.change}/`\n")
    (w / f"BUILD-BRIEFING-{a.id}.md").write_text(briefing)
    (w / f"CODEX-PROMPT-{a.id}.md").write_text(reviewer_prompt)
    print("wrote briefing + codex prompt in", w)


```

- [ ] **I7** `skill/SKILL.md` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
  make (a product call, a behaviour the guild would notice), and anything
  in the operator gates below. With the user present, say which one and
  wait. Unattended, park that issue and carry on (see the sweep).
- Creates the build worktree, writes the briefing, prompts `pi_build`.
- Rules on escalations (BLOCKED from the builder). A ruling is one message
  to the builder, and a sentence the builder must relay to the reviewer.
- When the builder reports the reviewer green: runs the `reviewer` skill,
```

Replace it with exactly:

```python
  make (a product call, a behaviour the guild would notice), and anything
  in the operator gates below. With the user present, say which one and
  wait. Unattended, park that issue and carry on (see the sweep).
- Creates the build worktree and generates the briefing after APPROVE with
  `python3 <herd>/tools/mkbrief.py <id> <worktree> <branch> <pinned-base-sha>
  <change-name> <allowed-files-file> --lead-pane <live-pane-id>`, then prompts
  `pi_build`. Put every measured gate, including the full-suite count,
  mutation names and fence step count, in tasks.md's single `## 0. Gates`
  section. The generator copies that section; it takes no separate gate file.
  After any spec amendment, regenerate the briefing from tasks.md before
  dispatching the next round. Keep the original base SHA pinned.
- Rules on escalations (BLOCKED from the builder). A ruling is one message
  to the builder, and a sentence the builder must relay to the reviewer.
- When the builder reports the reviewer green: runs the `reviewer` skill,
```

- [ ] **I8** `skill/SKILL.md` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
folds the accepted fix into the reference,
re-runs the affected tests and mutations, regenerates the fences, verifies
byte parity, installs any regenerated test fences in the build worktree,
then marks `gates.py fold done --issue <id>`. The builder
re-applies the affected implementation files, re-runs all gates (including the full suite once
for the new build-state after `gates.py suite-ok --issue <id>`), updates the
handoff and resumes review within the cap authorized by the lead ruling. A pending reference fold prevents REVIEW CLEAN and DONE.
```

Replace it with exactly:

```python
folds the accepted fix into the reference,
re-runs the affected tests and mutations, regenerates the fences, verifies
byte parity, installs any regenerated test fences in the build worktree,
regenerates the briefing from the amended tasks.md (`mkbrief.py`, same pinned
base SHA), then marks `gates.py fold done --issue <id>`. The builder
re-applies the affected implementation files, re-runs all gates (including the full suite once
for the new build-state after `gates.py suite-ok --issue <id>`), updates the
handoff and resumes review within the cap authorized by the lead ruling. A pending reference fold prevents REVIEW CLEAN and DONE.
```

## 3. Mutation drives

- [ ] **M1** in `tools/mkbrief.py`: replace

```python
return "".join(lines).rstrip("\n") + "\n"
```

with

```python
return "STALE\n"
```

Killer: `tests/test_mkbrief.py::test_main_regenerates_suite_mutation_and_fence_literals_from_tasks`

- [ ] **M2** in `tools/mkbrief.py`: replace

```python
if len(blocks) != 1 or not "".join(blocks[0]).strip():
```

with

```python
if False:
```

Killer: `tests/test_mkbrief.py::test_invalid_task_gates_fail_clearly`

- [ ] **M3** in `tools/mkbrief.py`: replace

```python
            current = None
```

with

```python
            current = current
```

Killer: `tests/test_mkbrief.py::test_gate_section_respects_fenced_headings_and_stops_at_next_section`

- [ ] **M4** in `tools/mkbrief.py`: replace

```python
        if fence:
```

with

```python
        if False:
```

Killer: `tests/test_mkbrief.py::test_gate_section_respects_fenced_headings_and_stops_at_next_section`

- [ ] **M5** in `tools/mkbrief.py`: replace

```python
return "".join(lines).rstrip("\n") + "\n"
```

with

```python
return "".join(lines).strip() + "\n"
```

Killer: `tests/test_mkbrief.py::test_gate_section_respects_fenced_headings_and_stops_at_next_section`
