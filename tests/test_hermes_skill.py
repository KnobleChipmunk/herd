import pathlib
import re

import librarian
import runlog

SKILL = pathlib.Path(librarian.__file__).resolve().parent.parent / "hermes" / "herd-librarian" / "SKILL.md"


def test_the_skill_has_hermes_frontmatter_with_a_short_description():
    text = SKILL.read_text()
    assert text.startswith("---\nname: herd-librarian\n")
    description = re.search(r"^description: (.+)$", text, re.M).group(1).strip('"')
    assert len(description) <= 60 and description.endswith(".")


def test_every_librarian_subcommand_the_skill_names_exists():
    named = set(re.findall(r"librarian\.py ([a-z-]+)", SKILL.read_text()))
    assert named >= {"report", "append-ledger", "friction", "friction-append"}
    parser_cmds = {"report", "ledger-rows", "append-ledger", "friction", "friction-append"}
    assert named <= parser_cmds, named - parser_cmds


def test_every_run_log_kind_the_skill_names_exists():
    named = set(re.findall(r"runlog\.py add ([a-z-]+)", SKILL.read_text()))
    assert named and named <= set(runlog.KINDS), named - set(runlog.KINDS)


def test_the_skill_forbids_the_actions_the_librarian_must_never_take():
    text = SKILL.read_text()
    for forbidden in ("git commit", "git push", "merge_stack.py --apply", "SKILL.md", "memory"):
        assert forbidden in text.split("## Never")[1], forbidden


def test_every_proposals_subcommand_the_skills_name_exists():
    import proposals
    herd_skill = SKILL.parent.parent.parent / "skill" / "SKILL.md"
    named = set(re.findall(r"proposals\.py ([a-z-]+)", SKILL.read_text() + herd_skill.read_text()))
    assert {"list", "set", "sync"} <= named
    assert named <= set(proposals.COMMANDS), named - set(proposals.COMMANDS)


def test_the_skill_names_no_personal_path():
    """The herd checkout comes from the launch prompt, the vault from $HERD_VAULT."""
    text = SKILL.read_text()
    for personal in ("~/projects", "/home/", "Exocortex", "project-mera"):
        assert personal not in text, personal
    assert "<herd>" in text and "$HERD_VAULT" in text
