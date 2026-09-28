# Tasks: read-only fence projection

Pinned prerequisite ace145d (PR #69).

## Requirement table

| Source section | Implementing step | Acceptance evidence / linked deferral |
|---|---|---|
| Accepted proposal: read-only projection and documented forms | I3 | T1 read-only snapshot, base mapping preservation, all existing step kinds and inline forms |
| Accepted proposal: anchor counts and final parity | I1-I3 | T1 nonunique/missing anchors, sequential replacements, final drift and pinned git blob CLI |
| Accepted proposal: exact invocation and boundary in review brief | I4-I5 | T1 card command/boundary assertion; caller is plan-reviewer Evidence |
| Design: preserve old final-build CLI | I3 | Existing23 test cases remain green; empty plans/invalid refs verified |

## 0. Gates

Baseline ace145d in reference: `23 passed in 0.05s` touched; `519 passed in 9.62s` full; Ruff `All checks passed!`; literal PROJECTION OK in tools/fencecheck.py is0.
Run `PYTHONPATH=src python3 -m pytest tests/test_fencecheck.py -q --no-header` after section1: expect12 failed,23 passed (observed12 failed,23 passed in0.11s). After implementation: expect35 passed (observed35 passed in0.08s).
Run `python3 /home/tusk/projects/herd/tools/gates.py suite-ok --issue proposal-audit` then `PYTHONPATH=src python3 -m pytest -q` once: expect531 passed (baseline519+12). Pre-execution observed531 passed in9.75s.
Run `ruff check tools tests`: All checks passed! Type checking NOT CHECKED: no configured command, mypy absent. pytest-xdist absent; run serially.
Literal gate: `python3 tools/gates.py count 'PROJECTION OK' tools/fencecheck.py`: baseline0, build1.
Fence gate: `python3 tools/fencecheck.py openspec/changes/read-only-fence-projection/tasks.md .`: FENCES OK (6 steps).
Projection gate: `python3 -B tools/fencecheck.py openspec/changes/read-only-fence-projection/tasks.md . --base ace145d`: PROJECTION OK (6 steps), every quoted anchor1 and all four touched files PARITY OK.
Run `openspec validate read-only-fence-projection`: Change 'read-only-fence-projection' is valid.
Run `python3 tools/mutate.py openspec/changes/read-only-fence-projection/tasks.md .`: M1-M6 all KILLED. M1 enforces unique anchors; M2 detects final drift; M3 covers sequential inline forms; M4 preserves the base mapping; M5 rejects empty base refs; M6 checks file-operation output. Record observed FAILED lines.

Fold regression: before the output fix the three file-operation precondition cases fail (`3 failed, 32 passed in 0.13s`); after the fix all35 pass. Emit n/a even on a failed file precondition.


## 1. Tests first

- [ ] **T1** `tests/test_fencecheck.py` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
])
def test_forms_lists_only_the_sources_fence_could_have_rendered(rendered, sources):
    assert fencecheck.forms(rendered) == sources
```

Replace it with exactly:

```python
])
def test_forms_lists_only_the_sources_fence_could_have_rendered(rendered, sources):
    assert fencecheck.forms(rendered) == sources


def test_projection_reports_each_anchor_and_final_parity_without_writing(built, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("projection must not apply steps or load plan code")

    monkeypatch.setattr(herdtool, "apply_step", forbidden)
    monkeypatch.setattr(herdtool, "load", forbidden)
    impl = [s for s in IMPL if not s.get("old_desc")]
    text = render(impl=impl)
    before = {str(p.relative_to(built)): p.read_bytes() for p in built.rglob("*") if p.is_file()}
    lines, failed = fencecheck.project(text, BASE, built)
    assert not failed
    assert "T1 `tests/test_new.py`: anchors=n/a (new_file)" in lines
    assert "I2 `src/append.py`: anchors=n/a (append)" in lines
    assert "I3 `src/whole.py`: anchors=n/a (whole_file)" in lines
    assert "T2 `src/replace.py`: anchors=1" in lines
    assert "I4 `src/inline.py`: anchors=1" in lines
    assert "I5 `src/anchor.py`: anchors=1" in lines
    assert "PARITY `src/inline.py`: OK" in lines
    assert len([line for line in lines if line.startswith("PARITY")]) == 7
    assert before == {str(p.relative_to(built)): p.read_bytes() for p in built.rglob("*") if p.is_file()}
    assert BASE["src/replace.py"] == "a = 1\nb = 2\nc = 3\n"


def test_projection_handles_sequential_inline_replacements(tmp_path):
    steps = [dict(kind="replace", path="x.py", old="one", new="two", why="first"),
             dict(kind="replace", path="x.py", old="two", new="three", why="second")]
    (tmp_path / "x.py").write_text("value = three + 1\n")
    lines, failed = fencecheck.project(render(tests=[], impl=steps), {"x.py": "value = one + 1\n"}, tmp_path)
    assert not failed
    assert "I1 `x.py`: anchors=1" in lines and "I2 `x.py`: anchors=1" in lines
    assert "PARITY `x.py`: OK" in lines


@pytest.mark.parametrize("base,reason", [("wrong\n", "anchors=0"), ("old\nold\n", "anchors=2")])
def test_projection_refuses_nonunique_anchors(tmp_path, base, reason):
    step = dict(kind="replace", path="x.py", old="old\n", new="new\n", why="replace")
    (tmp_path / "x.py").write_text(base.replace("old\n", "new\n", 1))
    lines, failed = fencecheck.project(render(tests=[], impl=[step]), {"x.py": base}, tmp_path)
    assert failed and any(reason in line for line in lines)


@pytest.mark.parametrize("kind,base,reason", [
    ("new_file", {"x.py": "old\n"}, "file already exists in base"),
    ("whole_file", {}, "file missing from base"),
    ("append", {"x.py": "old\n\n"}, "file end not a single newline"),
])
def test_projection_checks_file_preconditions(tmp_path, kind, base, reason):
    step = dict(kind=kind, path="x.py", new="new\n", why="change")
    (tmp_path / "x.py").write_text("new\n")
    lines, failed = fencecheck.project(render(tests=[], impl=[step]), base, tmp_path)
    assert failed and any(reason in line for line in lines)
    assert f"I1 `x.py`: anchors=n/a ({kind})" in lines


def test_projection_rejects_prose_only_replace(built):
    lines, failed = fencecheck.project(render(), BASE, built)
    assert failed and any("I4 `src/desc.py`: quoted old text required" == line for line in lines)


def test_projection_detects_final_drift_and_missing_reference(tmp_path):
    steps = [dict(kind="replace", path="x.py", old="old\n", new="new\n", why="replace"),
             dict(kind="new_file", path="missing.py", new="body\n", why="create")]
    (tmp_path / "x.py").write_text("new\nextra\n")
    lines, failed = fencecheck.project(render(tests=[], impl=steps), {"x.py": "old\n"}, tmp_path)
    assert failed
    assert "PARITY `x.py`: DIFFERS" in lines
    assert "PARITY `missing.py`: reference missing" in lines


def test_projection_preserves_required_blank_line_forms(tmp_path):
    step = dict(kind="insert_before", path="x.py", old="def f():\n", new="import os\n\n\n", why="insert")
    (tmp_path / "x.py").write_text("import os\n\ndef f():\n    pass\n")
    lines, failed = fencecheck.project(render(tests=[], impl=[step]), {"x.py": "def f():\n    pass\n"}, tmp_path)
    assert failed and "PARITY `x.py`: DIFFERS" in lines


def test_projection_cli_uses_pinned_git_blobs_without_writing(repo_with_worktree, capsys):
    import subprocess

    _, wt = repo_with_worktree
    (wt / "x.py").write_text("old\n")
    subprocess.run(["git", "add", "x.py"], cwd=wt, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"], cwd=wt, check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=wt, text=True).strip()
    (wt / "x.py").write_text("new\n")
    tasks = wt / "tasks.md"
    tasks.write_text(render(tests=[], impl=[dict(kind="replace", path="x.py", old="old\n", new="new\n", why="replace")]))
    before = {p: p.read_bytes() for p in (wt / "x.py", tasks)}
    assert fencecheck.main([str(tasks), str(wt), "--base", base]) == 0
    output = capsys.readouterr().out
    assert "I1 `x.py`: anchors=1" in output and "PARITY `x.py`: OK" in output
    assert output.rstrip().endswith("PROJECTION OK (1 steps)")
    assert before == {p: p.read_bytes() for p in before}
    for invalid in ("missing-ref", ""):
        assert fencecheck.main([str(tasks), str(wt), "--base", invalid]) == 2
        assert "invalid base" in capsys.readouterr().out
    tasks.write_text("# no steps\n")
    assert fencecheck.main([str(tasks), str(wt), "--base", base]) == 2
    assert "no T/I steps" in capsys.readouterr().out


def test_plan_review_names_the_read_only_projection_command():
    root = pathlib.Path(fencecheck.__file__).resolve().parent.parent
    card = (root / "skill/cards/plan-reviewer.md").read_text()
    assert "--base <pinned-base-sha>" in card
    assert "in memory" in card and "never writes files" in card
    assert "never imports or executes plan code" in card
    assert "projection command in `skill/cards/plan-reviewer.md`" in (root / "skill/SKILL.md").read_text()
```

## 2. Implementation

- [ ] **I1** `tools/fencecheck.py` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
"""Check a build worktree against the byte-exact fences of its tasks.md.

usage: fencecheck.py <tasks.md> <worktree>

Prints one line per step that deviates (step, file, why) and exits 1, or
prints `FENCES OK (<n> steps)` and exits 0. Exits 2 when tasks.md has no steps.
```

Replace it with exactly:

```python
"""Check a build worktree against the byte-exact fences of its tasks.md.

usage: python3 -B fencecheck.py <tasks.md> <worktree> [--base <pinned-base-sha>]

With --base, read git blobs and project fences in memory without writing or
executing plan code. Report anchor counts and final reference parity. Prose-only
replacement instructions need quoted old text for projection.

Prints one line per step that deviates (step, file, why) and exits 1, or
prints `FENCES OK (<n> steps)` and exits 0. Exits 2 when tasks.md has no steps.
```

- [ ] **I2** `tools/fencecheck.py` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
"""
from __future__ import annotations

import pathlib
import sys

from herdtool import forms, parse_tasks, step_problem
```

Replace it with exactly:

```python
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

from herdtool import forms, parse_tasks, step_problem
```

- [ ] **I3** `tools/fencecheck.py` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
    return problems


def main(argv: list[str] | None = None) -> int:
    tasks_path, worktree = argv if argv is not None else sys.argv[1:3]
    text = pathlib.Path(tasks_path).read_text(encoding="utf-8")
    steps = parse_tasks(text)
    if not steps:
        print(f"no T/I steps found in {tasks_path}")
        return 2
    problems = check(text, pathlib.Path(worktree))
    for p in problems:
        print(p)
```

Replace it with exactly:

```python
    return problems


def project(tasks_text: str, base_files: dict[str, str], w: pathlib.Path) -> tuple[list[str], bool]:
    """Project parsed fences onto base text in memory and compare the reference.

    The reference selects rendered forms as in check(); if a later step has
    replaced an inline result, the unique base anchor selects its paired form.
    Whole-file and append bodies retain their exact rendered bytes.
    """
    files = dict(base_files)
    lines, failed = [], False
    steps = parse_tasks(tasks_text)
    for original in steps:
        path, kind = original["path"], original["kind"]
        label = f"{original['name']} `{path}`"
        current = files.get(path)
        step = resolve(w, original)
        reason = None
        if kind == "new_file":
            if current is not None:
                reason = "file already exists in base"
            else:
                files[path] = step["new"]
        elif current is None:
            reason = "file missing from base"
        elif kind == "whole_file":
            files[path] = step["new"]
        elif kind == "append":
            if not current.endswith("\n") or current.endswith("\n\n"):
                reason = "file end not a single newline"
            else:
                files[path] = current + step["new"]
        elif step["old"] is None:
            reason = "quoted old text required"
        else:
            old, new = step["old"], step["new"]
            count = current.count(old)
            if count == 0:
                # A later step may remove the reference occurrence used by resolve.
                for index, form in enumerate(forms(original["old"])):
                    if current.count(form):
                        old = form
                        if kind == "replace":
                            new_forms = forms(original["new"])
                            new = new_forms[min(index, len(new_forms) - 1)]
                        count = current.count(old)
                        break
            lines.append(f"{label}: anchors={count}")
            if count != 1:
                reason = "anchor must occur exactly once"
            else:
                files[path] = current.replace(old, new + old if kind == "insert_before" else new, 1)
        if kind in ("new_file", "whole_file", "append"):
            lines.append(f"{label}: anchors=n/a ({kind})")
        if reason:
            lines.append(f"{label}: {reason}")
            failed = True
    for path in sorted({step["path"] for step in steps}):
        reference = w / path
        if not reference.is_file():
            status = "reference missing"
        else:
            status = "OK" if files.get(path) == reference.read_text(encoding="utf-8") else "DIFFERS"
        lines.append(f"PARITY `{path}`: {status}")
        failed |= status != "OK"
    return lines, failed


def project_base(tasks_text: str, w: pathlib.Path, base: str) -> int:
    ref = subprocess.run(["git", "-C", str(w), "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"],
                         capture_output=True, text=True)
    if ref.returncode:
        print(f"invalid base: {base}")
        return 2
    files = {}
    for path in {step["path"] for step in parse_tasks(tasks_text)}:
        blob = subprocess.run(["git", "-C", str(w), "show", f"{ref.stdout.strip()}:{path}"],
                              capture_output=True, text=True, encoding="utf-8")
        if blob.returncode == 0:
            files[path] = blob.stdout
    lines, failed = project(tasks_text, files, w)
    for line in lines:
        print(line)
    if not failed:
        print(f"PROJECTION OK ({len(parse_tasks(tasks_text))} steps)")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tasks_path")
    parser.add_argument("worktree")
    parser.add_argument("--base")
    args = parser.parse_args(argv)
    tasks_path, worktree = args.tasks_path, args.worktree
    text = pathlib.Path(tasks_path).read_text(encoding="utf-8")
    steps = parse_tasks(text)
    if not steps:
        print(f"no T/I steps found in {tasks_path}")
        return 2
    if args.base is not None:
        return project_base(text, pathlib.Path(worktree), args.base)
    problems = check(text, pathlib.Path(worktree))
    for p in problems:
        print(p)
```

- [ ] **I4** `skill/cards/plan-reviewer.md` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python

## Evidence

Reads files and git blobs, does its own arithmetic, projects fences onto the base in memory.

## Authority

```

Replace it with exactly:

```python

## Evidence

Reads files and git blobs and does its own arithmetic. For fence projection run `python3 -B <herd>/tools/fencecheck.py <tasks.md> <reference-worktree> --base <pinned-base-sha>`. It applies documented fence forms in memory, reports each anchor count and final reference parity, never writes files, and never imports or executes plan code. Require `PROJECTION OK (<n> steps)`; investigate every reported mismatch. A prose-only replacement needs quoted old text before it can be audited. Use this command instead of rebuilding the projection with a reviewer-written parser.

## Authority

```

- [ ] **I5** `skill/SKILL.md` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
Apply the authority-rule check in `skill/cards/plan-reviewer.md` whenever
a rule is extracted, reformatted, or rewritten.
Tell it where its line is: it may read files and git blobs, do its own
arithmetic, inspect code, and project the fences onto the base in memory;
it never applies the plan, imports the plan's code, or runs its tests or
mutations. The lead's pre-execution is the execution evidence.
Have it write findings to `PLAN-REVIEW-<id>-round-N.md` in the repo root
```

Replace it with exactly:

```python
Apply the authority-rule check in `skill/cards/plan-reviewer.md` whenever
a rule is extracted, reformatted, or rewritten.
Tell it where its line is: it may read files and git blobs, do its own
arithmetic, inspect code, and run the read-only fence
projection command in `skill/cards/plan-reviewer.md` against the pinned base;
it never applies the plan, imports the plan's code, or runs its tests or
mutations. The lead's pre-execution is the execution evidence.
Have it write findings to `PLAN-REVIEW-<id>-round-N.md` in the repo root
```

## 3. Mutation drives

- [ ] **M1** in `tools/fencecheck.py`: replace

```python
if count != 1:
```

with

```python
if False:
```

Killer: `tests/test_fencecheck.py::test_projection_refuses_nonunique_anchors`

- [ ] **M2** in `tools/fencecheck.py`: replace

```python
status = "OK" if files.get(path) == reference.read_text(encoding="utf-8") else "DIFFERS"
```

with

```python
status = "OK"
```

Killer: `tests/test_fencecheck.py::test_projection_detects_final_drift_and_missing_reference`

- [ ] **M3** in `tools/fencecheck.py`: replace

```python
if count == 0:
```

with

```python
if False:
```

Killer: `tests/test_fencecheck.py::test_projection_handles_sequential_inline_replacements`

- [ ] **M4** in `tools/fencecheck.py`: replace

```python
files = dict(base_files)
```

with

```python
files = base_files
```

Killer: `tests/test_fencecheck.py::test_projection_reports_each_anchor_and_final_parity_without_writing`

- [ ] **M5** in `tools/fencecheck.py`: replace

```python
if args.base is not None:
```

with

```python
if args.base:
```

Killer: `tests/test_fencecheck.py::test_projection_cli_uses_pinned_git_blobs_without_writing`

- [ ] **M6** in `tools/fencecheck.py`: replace

```python
lines.append(f"{label}: anchors=n/a ({kind})")
```

with

```python
pass
```

Killer: `tests/test_fencecheck.py::test_projection_reports_each_anchor_and_final_parity_without_writing`
