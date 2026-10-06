import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = sorted(p for p in ROOT.rglob("SKILL.md") if ".git" not in p.parts)


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: str(p.relative_to(ROOT)))
def test_skill_frontmatter_is_strict_yaml(skill):
    """pi (and other Agent Skills hosts) parse frontmatter as strict YAML; Claude Code is lenient."""
    _, frontmatter, _ = skill.read_text().split("---\n", 2)
    meta = yaml.safe_load(frontmatter)
    assert isinstance(meta, dict) and meta.get("name") and meta.get("description")
