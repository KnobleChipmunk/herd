# Tasks: scratch mutation runs from the current directory (#55)

## 1. Tests first

- [ ] **T1** `tests/test_mutate.py` — Insert the parameterized CLI regression. Preserve two blank lines between top-level functions; the fence ends with those two blank lines.

Find this exact text (it occurs exactly once):

```python
def test_refuses_while_pytest_runs_in_the_worktree(build):
```

Insert exactly this text IMMEDIATELY BEFORE it (the fence carries its own trailing blank lines):

```python
@pytest.mark.parametrize("worktree", [".", "./", "absolute"])
def test_main_scratch_accepts_current_directory_and_preserves_source(build, monkeypatch, capsys, worktree):
    tasks = build / "SCRATCH-tasks.md"
    tasks.write_text(render_tasks())
    calc = build / "src" / "calc.py"
    before = calc.read_bytes()
    stamp = calc.stat().st_mtime_ns
    status = git("status", "--porcelain", cwd=build)
    monkeypatch.chdir(build)
    tree = str(build) if worktree == "absolute" else worktree

    assert mutate.main([str(tasks), tree, "--only", "M1", "--scratch"]) == 0

    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1 and lines[0].startswith("M1 KILLED")
    assert calc.read_bytes() == before
    assert calc.stat().st_mtime_ns == stamp
    assert git("status", "--porcelain", cwd=build) == status


```

Run `python3 -m pytest -q tests/test_mutate.py -k main_scratch` before implementation: expect the two current-directory cases to fail with FileExistsError; the absolute case passes.

## 2. Implementation

- [ ] **I1** `tools/mutate.py` — Resolve the scratch source before taking its name. No blank lines are inserted within this block.

Find this exact text (it occurs exactly once):

```python
    with tempfile.TemporaryDirectory(prefix="herd-mutate-") as tmp:
```

Replace it with exactly:

```python
    w = w.resolve()
    with tempfile.TemporaryDirectory(prefix="herd-mutate-") as tmp:
```

## 3. Mutation drives

- [ ] **M1** in `tools/mutate.py`: replace

```python
    w = w.resolve()
    with tempfile.TemporaryDirectory(prefix="herd-mutate-") as tmp:
```

with

```python
    with tempfile.TemporaryDirectory(prefix="herd-mutate-") as tmp:
```

Killer: `tests/test_mutate.py::test_main_scratch_accepts_current_directory_and_preserves_source`

- [ ] **M2** in `tools/mutate.py`: replace

```python
    if not scratch:
```

with

```python
    if True:
```

Killer: `tests/test_mutate.py::test_main_scratch_accepts_current_directory_and_preserves_source`


## 4. Gates and pre-execution evidence

Baseline: main/origin/main at `1dce87003ca91cd703d6ee0f84cdc9413e724dc8`, measured in `/home/tusk/projects/herd__worktrees/55-reference` before edits.

- Baseline full suite: `python3 -m pytest -q` -> `504 passed in 9.61s`. Build expectation: baseline + three parameter cases, 507 passed. Run once after all edits, after `python3 /home/tusk/projects/herd/tools/gates.py suite-ok --issue 55 --repo /home/tusk/projects/herd` permits it.
- Touched suite: `python3 -m pytest -q tests/test_mutate.py` -> `27 passed in 4.65s` after pre-execution (baseline 24 + 3).
- Ruff: `ruff check tools tests` -> `All checks passed!` before and after.
- Literal gate: `python3 tools/gates.py count 'w = w.resolve()' tools/mutate.py` -> baseline `1`, build `2`.
- Type checking: no configured type-check command in pyproject.toml or CI; `python3 -m mypy --version` reports `No module named mypy`. Record as not checked, never PASS. pytest-xdist is not installed; run serially.

Pre-execution RED: `2 failed, 1 passed, 24 deselected in 0.38s`; both failures are the issue's FileExistsError at shutil.copytree. GREEN and Ruff above were executed in the reference tree. Drive both mutations after tests finish using `python3 /home/tusk/projects/herd/tools/mutate.py <tasks.md> <worktree>`. Both must be KILLED with this regression as the failing test. Reviewers use the same command with `--scratch` and an absolute worktree path.

Check fence parity with `python3 /home/tusk/projects/herd/tools/fencecheck.py <tasks.md> <worktree>`; expected `FENCES OK (2 steps)`. Do not alter tests after the tests-first step.

Observed pre-execution mutation results: M1 KILLED and M2 KILLED; each reports FAILED tests/test_mutate.py::test_main_scratch_accepts_current_directory_and_preserves_source[.]. Fencecheck reported FENCES OK (2 steps); openspec validation passed. Plan review and builder dispatch have not started: the operator chose to restart from a live Herdr pane after the inherited pane w1:p2Z was missing.
