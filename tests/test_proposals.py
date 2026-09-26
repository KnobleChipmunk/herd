import json
import pathlib
import subprocess

import librarian
import proposals

LEDGER = """# Friction ledger

## sandboxed-testclient-hang (Starlette TestClient hangs under the sandbox)
- 2026-09-25 project-mera #459 (wsl): hung.
- 2026-09-25 project-mera #459 (wsl): hung again.
- 2026-09-26 project-mera #459 (wsl): hung a third time.

## mutate-py-argv-match (mutate.py's guard matches any argv mentioning pytest)
- 2026-09-26 project-mera #459 (wsl): refused.
- 2026-09-26 project-mera #459 (wsl): refused again.
"""


def proposal(slug: str, status: str | None = None) -> str:
    head = f"# Proposal: {slug} title\n\n"
    if status:
        head += f"Status: {status}\n\n"
    return head + f"## Class\n\n{slug} — one line\n\n## Proposed change\n\nDo it.\n"


def setup(tmp_path: pathlib.Path, files: dict[str, str | None]) -> tuple[pathlib.Path, pathlib.Path]:
    folder = tmp_path / "proposals"
    folder.mkdir()
    for stem, status in files.items():
        slug = stem.split("-", 3)[3]
        (folder / f"{stem}.md").write_text(proposal(slug, status))
    ledger = tmp_path / "friction-ledger.md"
    ledger.write_text(LEDGER)
    return folder, ledger


def gh_states(states: dict[str, str]):
    def gh(args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(args, 0, json.dumps({"state": states[args[2]], "mergedAt": "2026-09-27T10:00:00Z"}), "")
    return gh


def test_class_counts_are_the_ones_friction_append_reports(tmp_path):
    ledger = tmp_path / "friction-ledger.md"
    ledger.write_text(LEDGER)
    assert librarian.class_counts(ledger) == {"sandboxed-testclient-hang": 3, "mutate-py-argv-match": 2}
    n = librarian.friction_append(ledger, "mutate-py-argv-match", "", "- 2026-09-27 project-mera #480 (wsl): again.")
    assert n == librarian.class_counts(ledger)["mutate-py-argv-match"] == 3


def test_a_proposal_with_no_status_line_is_open(tmp_path):
    folder, ledger = setup(tmp_path, {"2026-09-25-sandboxed-testclient-hang": None})
    (p,) = proposals.load(folder, ledger)
    assert (p.status, p.slug, p.events) == ("open", "sandboxed-testclient-hang", 3)


def test_list_ranks_open_proposals_by_their_class_events_and_hides_closed_ones(tmp_path):
    folder, ledger = setup(tmp_path, {
        "2026-09-26-mutate-py-argv-match": "open",
        "2026-09-25-sandboxed-testclient-hang": None,
        "2026-09-25-something-rejected": "rejected",
    })
    lines = proposals.render(proposals.load(folder, ledger), statuses=proposals.PENDING)
    assert [ln.split()[0] for ln in lines] == ["2026-09-25-sandboxed-testclient-hang", "2026-09-26-mutate-py-argv-match"]
    assert "3 events" in lines[0] and "open" in lines[0]


def test_a_class_missing_from_the_ledger_shows_unknown_events(tmp_path):
    folder, ledger = setup(tmp_path, {"2026-09-26-no-such-class": None})
    (line,) = proposals.render(proposals.load(folder, ledger), statuses=proposals.PENDING)
    assert "? events" in line


def test_set_writes_one_status_line_and_replaces_the_old_one(tmp_path):
    folder, ledger = setup(tmp_path, {"2026-09-26-mutate-py-argv-match": None})
    path = folder / "2026-09-26-mutate-py-argv-match.md"
    proposals.set_status(path, "accepted")
    proposals.set_status(path, "in-pr", "https://github.com/KnobleChipmunk/herd/pull/22")
    text = path.read_text()
    assert text.count("Status:") == 1
    assert "Status: in-pr https://github.com/KnobleChipmunk/herd/pull/22\n" in text
    assert text.startswith("# Proposal: mutate-py-argv-match title\n\nStatus: in-pr")
    assert "## Proposed change\n\nDo it.\n" in text


def test_set_refuses_an_unknown_status_and_a_pr_status_without_its_pr(tmp_path):
    folder, _ = setup(tmp_path, {"2026-09-26-mutate-py-argv-match": None})
    path = folder / "2026-09-26-mutate-py-argv-match.md"
    for status, pr, why in (("done", "", "unknown status done"), ("in-pr", "", "in-pr needs --pr"),
                            ("applied", "", "applied needs --pr")):
        try:
            proposals.set_status(path, status, pr)
        except SystemExit as exc:
            assert why in str(exc)
        else:
            raise AssertionError(f"{status} was accepted")


def test_sync_marks_a_proposal_applied_once_its_pr_merges(tmp_path):
    folder, ledger = setup(tmp_path, {
        "2026-09-26-mutate-py-argv-match": "in-pr https://github.com/o/herd/pull/22",
        "2026-09-25-sandboxed-testclient-hang": "in-pr https://github.com/o/herd/pull/30",
    })
    changed = proposals.sync(proposals.load(folder, ledger),
                             gh_states({"https://github.com/o/herd/pull/22": "MERGED",
                                        "https://github.com/o/herd/pull/30": "OPEN"}))
    assert changed == ["2026-09-26-mutate-py-argv-match"]
    by = {p.stem: p for p in proposals.load(folder, ledger)}
    assert by["2026-09-26-mutate-py-argv-match"].status == "applied"
    assert by["2026-09-26-mutate-py-argv-match"].note == "https://github.com/o/herd/pull/22 2026-09-27"
    assert by["2026-09-25-sandboxed-testclient-hang"].status == "in-pr"


def test_the_repos_own_proposals_all_parse(tmp_path):
    folder = pathlib.Path(proposals.__file__).resolve().parent.parent / "proposals"
    for p in proposals.load(folder, tmp_path / "no-ledger.md"):
        assert p.status in proposals.STATUSES and p.slug, p.stem
