# Tasks: preserve authority conditions

Pinned prerequisite 4dfa966 (proposal-gates).

## 0. Gates

Baseline 4dfa966: touched tests/test_team.py 33 passed in 0.45s; baseline full suite 517 passed (proposal-gates verified build). Run `PYTHONPATH=src python3 -m pytest tests/test_team.py -q --no-header` after tests first: 1 failed, 33 passed in 0.45s. After implementation: 34 passed in 0.43s.
Run `python3 /home/tusk/projects/herd/tools/gates.py suite-ok --issue proposal-authority`, then `PYTHONPATH=src python3 -m pytest -q` once: expect 518 passed (baseline +1). Predecessor duration about 10 seconds.
Run `ruff check tools tests`: All checks passed! (same baseline).
Type checking NOT CHECKED: mypy absent, no project command configured. pytest-xdist absent; run serially.
Literal gate `python3 tools/gates.py count 'surviving authorization condition' skill/cards/plan-reviewer.md`: baseline 0, build 1.
Fence gate `python3 tools/fencecheck.py openspec/changes/preserve-authority-conditions/tasks.md .`: FENCES OK (3 steps).
Mutations M1, M2 and M3: run `python3 tools/mutate.py openspec/changes/preserve-authority-conditions/tasks.md .`; all must be KILLED by test_plan_review_preserves_authorization_conditions. Pre-execution observed all three killed.


## 1. Tests first

- [ ] **T1** `tests/test_team.py` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
        text = (SKILL_DIR / "cards" / c).read_text()
        assert "must not be an author of what it judges" in text and "fresh context" in text

```

Replace it with exactly:

```python
        text = (SKILL_DIR / "cards" / c).read_text()
        assert "must not be an author of what it judges" in text and "fresh context" in text


def test_plan_review_preserves_authorization_conditions():
    card = (SKILL_DIR / "cards" / "plan-reviewer.md").read_text()
    assert "compare its actor, action, scope, and authorization condition against the source skill" in card
    assert "tightened prohibitions" in card and "relaxed permissions" in card
    assert "focused assertion" in card and "surviving authorization condition" in card
    assert "cite an existing assertion" in card
    skill = (SKILL_DIR / "SKILL.md").read_text()
    assert "authority-rule check in `skill/cards/plan-reviewer.md`" in skill
```

## 2. Implementation

- [ ] **I1** `skill/cards/plan-reviewer.md` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python

Spends effort on what execution cannot catch: re-derive fixture arithmetic, challenge design conventions and boundary cases, check that every text anchor resolves once, and that every gate is a measured literal with its baseline.

## Evidence

Reads files and git blobs, does its own arithmetic, projects fences onto the base in memory.
```

Replace it with exactly:

```python

Spends effort on what execution cannot catch: re-derive fixture arithmetic, challenge design conventions and boundary cases, check that every text anchor resolves once, and that every gate is a measured literal with its baseline.

When a rule is extracted, reformatted, or rewritten, compare its actor, action, scope, and authorization condition against the source skill. Check tightened prohibitions as well as relaxed permissions. Require a focused assertion of the surviving authorization condition before approving the plan; cite an existing assertion when it already covers the rewritten rule.

## Evidence

Reads files and git blobs, does its own arithmetic, projects fences onto the base in memory.
```

- [ ] **I2** `skill/SKILL.md` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
membership / design conventions / boundary cases, check every text anchor
resolves uniquely at HEAD, every gate is a measured literal with its
baseline named, and blank-line separation is stated for every insert.
Tell it where its line is: it may read files and git blobs, do its own
arithmetic, inspect code, and project the fences onto the base in memory;
it never applies the plan, imports the plan's code, or runs its tests or
```

Replace it with exactly:

```python
membership / design conventions / boundary cases, check every text anchor
resolves uniquely at HEAD, every gate is a measured literal with its
baseline named, and blank-line separation is stated for every insert.
Apply the authority-rule check in `skill/cards/plan-reviewer.md` whenever
a rule is extracted, reformatted, or rewritten.
Tell it where its line is: it may read files and git blobs, do its own
arithmetic, inspect code, and project the fences onto the base in memory;
it never applies the plan, imports the plan's code, or runs its tests or
```

## 3. Mutation drives

- [ ] **M1** in `skill/cards/plan-reviewer.md`: replace

```python
authorization condition against the source skill
```

with

```python
permission against the source skill
```

Killer: `tests/test_team.py::test_plan_review_preserves_authorization_conditions`

- [ ] **M2** in `skill/cards/plan-reviewer.md`: replace

```python
tightened prohibitions as well as relaxed permissions
```

with

```python
relaxed permissions
```

Killer: `tests/test_team.py::test_plan_review_preserves_authorization_conditions`

- [ ] **M3** in `skill/cards/plan-reviewer.md`: replace

```python
; cite an existing assertion when it already covers the rewritten rule.
```

with

```python
.
```

Killer: `tests/test_team.py::test_plan_review_preserves_authorization_conditions`
