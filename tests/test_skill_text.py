import pathlib
import re

SKILL = pathlib.Path(__file__).resolve().parent.parent / "skill" / "SKILL.md"


def paragraph(text: str, opening: str) -> str:
    start = text.index(opening)
    end = re.search(r"\n(?:- \*\*|\*\*|## |\n)", text[start + len(opening):])
    return " ".join(text[start: start + len(opening) + (end.start() if end else len(text))].split())


def test_the_plan_reviewer_is_never_told_to_run_tests():
    """Its tier-table row says it never executes; no other rule may send it to run tests (#459)."""
    text = SKILL.read_text()
    full_suite = paragraph(text, "- **The full suite runs once per build")
    runners = next(s for s in full_suite.split(". ") if "touched test files" in s)
    assert "plan reviewer" not in runners.lower()
    assert "The plan reviewer runs nothing" in full_suite


def test_the_plan_reviewer_brief_draws_the_read_only_line():
    brief = paragraph(SKILL.read_text(), "**Plan-reviewer brief")
    assert "never applies the plan" in brief
    assert "runs its tests or mutations" in brief
    assert "git blobs" in brief
