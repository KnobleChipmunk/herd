# Tasks: requirement coverage

Pinned prerequisite 8c97de1 (proposal-authority).

## Requirement table

| Source section | Implementing step | Acceptance evidence / linked deferral |
|---|---|---|
| Accepted proposal: one row per governing requirement | I1, I3 | T1 checks columns and exhaustive requirement instruction |
| Accepted proposal: new commands have callers | I1, I2 | T1 checks caller instruction; this plan introduces no commands |
| Accepted proposal: compare issue and design | I1, I2 | T1 checks source comparison; no design decision required |

## 0. Gates

Baseline 8c97de1: tests/test_team.py 34 passed in 0.44s; predecessor full suite 518 passed in 10.36s. Run `PYTHONPATH=src python3 -m pytest tests/test_team.py -q --no-header` after tests first: 1 failed, 34 passed in 0.44s; after implementation: 35 passed in 0.49s.
Run `python3 /home/tusk/projects/herd/tools/gates.py suite-ok --issue proposal-requirements` then `PYTHONPATH=src python3 -m pytest -q` once: expect 519 passed (baseline +1).
Run `ruff check tools tests`: All checks passed! (same baseline). Type checking NOT CHECKED: mypy absent, no project command configured. pytest-xdist absent; run serially.
Literal gate `python3 tools/gates.py count 'requirement table' openspec/config.yaml`: baseline 0, build 1.
Fence gate `python3 tools/fencecheck.py openspec/changes/plan-requirement-coverage/tasks.md .`: FENCES OK (4 steps).
Run `python3 tools/mutate.py openspec/changes/plan-requirement-coverage/tasks.md .`: M1, M2, M3 must all be KILLED by test_plan_template_accounts_for_requirements_and_command_callers (observed in pre-execution).


OpenSpec gate: `openspec validate plan-requirement-coverage` → `Change 'plan-requirement-coverage' is valid` (observed).

## 1. Tests first

- [ ] **T1** `tests/test_team.py` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
    assert "cite an existing assertion" in card
    skill = (SKILL_DIR / "SKILL.md").read_text()
    assert "authority-rule check in `skill/cards/plan-reviewer.md`" in skill
```

Replace it with exactly:

```python
    assert "cite an existing assertion" in card
    skill = (SKILL_DIR / "SKILL.md").read_text()
    assert "authority-rule check in `skill/cards/plan-reviewer.md`" in skill


def test_plan_template_accounts_for_requirements_and_command_callers():
    import yaml

    config = yaml.safe_load((SKILL_DIR.parent / "openspec/config.yaml").read_text())
    rules = " ".join(config["rules"]["tasks"])
    for field in ("source section", "implementing step", "acceptance evidence", "linked deferral"):
        assert field in rules
    assert "every governing requirement" in rules
    assert "every new command" in rules and "caller in the skill or a card" in rules
    assert "against the issue and design" in rules and "Before fences are generated" in rules
    card = (SKILL_DIR / "cards/plan-reviewer.md").read_text()
    assert "requirement table" in card and "against the issue and design" in card
    assert "every new command" in card and "caller in the skill or a card" in card
    assert "requirement table from `openspec/config.yaml`" in (SKILL_DIR / "SKILL.md").read_text()
```

## 2. Implementation

- [ ] **I1** `openspec/config.yaml` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
#     archive:
#       guidance:
#         - Summarize the archive outcome before finishing
```

Replace it with exactly:

```python
#     archive:
#       guidance:
#         - Summarize the archive outcome before finishing

rules:
  tasks:
    - Before fences are generated, add a requirement table with one row for every governing requirement, naming its source section, implementing step and acceptance evidence, or a linked deferral.
    - Check the table against the issue and design before pre-execution and the first independent review; tests alone do not establish coverage.
    - For every new command, name its caller in the skill or a card in the table's acceptance evidence.
```

- [ ] **I2** `skill/cards/plan-reviewer.md` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python

When a rule is extracted, reformatted, or rewritten, compare its actor, action, scope, and authorization condition against the source skill. Check tightened prohibitions as well as relaxed permissions. Require a focused assertion of the surviving authorization condition before approving the plan; cite an existing assertion when it already covers the rewritten rule.

## Evidence

Reads files and git blobs, does its own arithmetic, projects fences onto the base in memory.
```

Replace it with exactly:

```python

When a rule is extracted, reformatted, or rewritten, compare its actor, action, scope, and authorization condition against the source skill. Check tightened prohibitions as well as relaxed permissions. Require a focused assertion of the surviving authorization condition before approving the plan; cite an existing assertion when it already covers the rewritten rule.

Check the requirement table against the issue and design: every governing requirement needs an implementing step and acceptance evidence, or a linked deferral. Verify every new command has a caller in the skill or a card. Use the source sections to find omissions even when the pre-execution tests pass.

## Evidence

Reads files and git blobs, does its own arithmetic, projects fences onto the base in memory.
```

- [ ] **I3** `skill/SKILL.md` — Replace this unique quoted block; preserve exactly the blank lines shown.

Find this exact text (it occurs exactly once):

```python
  passes — and note validate is WEAKER than archive: a delta for a spec
  name with no file under `openspec/specs/` must be headed `## ADDED
  Requirements`, or the archive aborts later (#321).
- **Pre-executes the spec before plan review (#321).** In a scratch
  worktree cut from HEAD: apply every tasks.md instruction literally (a
  script extracting the fences, then the anchored edits), observe RED,
```

Replace it with exactly:

```python
  passes — and note validate is WEAKER than archive: a delta for a spec
  name with no file under `openspec/specs/` must be headed `## ADDED
  Requirements`, or the archive aborts later (#321).
- Before generating fences, complete the requirement table from `openspec/config.yaml`
  against the issue and design, including a skill/card caller for each new command.
- **Pre-executes the spec before plan review (#321).** In a scratch
  worktree cut from HEAD: apply every tasks.md instruction literally (a
  script extracting the fences, then the anchored edits), observe RED,
```

## 3. Mutation drives

- [ ] **M1** in `openspec/config.yaml`: replace

```python
acceptance evidence, or a linked deferral
```

with

```python
acceptance evidence
```

Killer: `tests/test_team.py::test_plan_template_accounts_for_requirements_and_command_callers`

- [ ] **M2** in `openspec/config.yaml`: replace

```python
caller in the skill or a card
```

with

```python
implementation file
```

Killer: `tests/test_team.py::test_plan_template_accounts_for_requirements_and_command_callers`

- [ ] **M3** in `skill/cards/plan-reviewer.md`: replace

```python
requirement table against the issue and design
```

with

```python
requirement table against the tests
```

Killer: `tests/test_team.py::test_plan_template_accounts_for_requirements_and_command_callers`
