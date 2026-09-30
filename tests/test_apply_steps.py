import json
import subprocess
import sys

import apply_steps

TOOL = apply_steps.__file__

STEPS = [
    {"name": "T1", "kind": "new_file", "path": "tests/test_calc.py", "old": None,
     "new": "def test_add():\n    assert 1\n"},
    {"name": "I1", "kind": "replace", "path": "src/calc.py", "old": "return a - b\n",
     "new": "return a + b\n"},
    {"name": "I2", "kind": "append", "path": "src/calc.py", "old": None,
     "new": "\n\nZERO = 0\n"},
]


def tree(tmp_path, steps=STEPS):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/calc.py").write_text("def add(a, b):\n    return a - b\n")
    path = tmp_path / "STEPS-9.json"
    path.write_text(json.dumps(steps))
    return path


def run(*args):
    return subprocess.run([sys.executable, TOOL, *map(str, args)], capture_output=True, text=True)


def test_applies_every_step_in_order_by_default(tmp_path):
    steps = tree(tmp_path)
    result = run(steps, tmp_path)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "src/calc.py").read_text() == "def add(a, b):\n    return a + b\n\n\nZERO = 0\n"
    assert (tmp_path / "tests/test_calc.py").exists()
    assert result.stdout.splitlines() == [
        "applied T1 new_file tests/test_calc.py",
        "applied I1 replace src/calc.py",
        "applied I2 append src/calc.py",
        "applied 3 steps",
    ]


def test_a_section_letter_selects_that_section_only(tmp_path):
    steps = tree(tmp_path)
    assert run(steps, tmp_path, "T").returncode == 0
    assert (tmp_path / "tests/test_calc.py").exists()
    assert "return a - b" in (tmp_path / "src/calc.py").read_text()


def test_named_steps_apply_alone(tmp_path):
    steps = tree(tmp_path)
    result = run(steps, tmp_path, "I1")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "src/calc.py").read_text() == "def add(a, b):\n    return a + b\n"
    assert not (tmp_path / "tests/test_calc.py").exists()


def test_path_filter_reapplies_one_file_after_a_fold(tmp_path):
    steps = tree(tmp_path)
    result = run(steps, tmp_path, "--path", "src/calc.py")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[-1] == "applied 2 steps"
    assert not (tmp_path / "tests/test_calc.py").exists()


def test_an_anchor_that_does_not_occur_once_stops_before_writing_and_names_the_step(tmp_path):
    steps = tree(tmp_path)
    (tmp_path / "src/calc.py").write_text("return a - b\nreturn a - b\n")
    result = run(steps, tmp_path, "I1")
    assert result.returncode == 1
    assert "I1 replace src/calc.py: anchor occurs 2 times, expected 1" in result.stderr
    assert (tmp_path / "src/calc.py").read_text() == "return a - b\nreturn a - b\n"


def test_a_failed_step_stops_the_run_and_reports_what_was_applied(tmp_path):
    steps = tree(tmp_path)
    (tmp_path / "src/calc.py").write_text("no anchor here\n")
    result = run(steps, tmp_path)
    assert result.returncode == 1
    assert result.stdout.splitlines() == ["applied T1 new_file tests/test_calc.py"]
    assert "I1 replace src/calc.py: anchor occurs 0 times, expected 1" in result.stderr
    assert "stopped after 1 of 3 steps" in result.stderr


def test_an_unknown_step_name_is_an_error_before_anything_is_applied(tmp_path):
    steps = tree(tmp_path)
    result = run(steps, tmp_path, "I9")
    assert result.returncode == 2
    assert "unknown step I9" in result.stderr
    assert not (tmp_path / "tests/test_calc.py").exists()


def test_new_file_refuses_to_overwrite(tmp_path):
    steps = tree(tmp_path)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_calc.py").write_text("kept\n")
    result = run(steps, tmp_path, "T1")
    assert result.returncode == 1
    assert "T1 new_file tests/test_calc.py: file already exists" in result.stderr
    assert (tmp_path / "tests/test_calc.py").read_text() == "kept\n"
