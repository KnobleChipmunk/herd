"""Send a prompt to a Herdr agent and wait until it settles, as one step.

usage: dispatch.py AGENT (TEXT | --file PATH) [--timeout MS] [--max-waits N]

`herdr agent prompt --wait` exits with "timed out waiting for agent status"
when a turn outlasts its timeout. That is not a failure: the agent is still
working. This tool then waits again with `herdr agent wait` until the agent
settles, so a dispatch is one call. Exit 0 once settled, 1 on any other error,
3 when still working after --max-waits extra waits (accepted proposal
2026-09-26-herdr-wait-not-idle).
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

TIMED_OUT = "timed out waiting for agent status"


def _run(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def dispatch(agent: str, text: str, *, timeout: int = 540000, max_waits: int = 20, runner=_run) -> int:
    r = runner(["herdr", "agent", "prompt", agent, text, "--wait", "--timeout", str(timeout)])
    waits = 0
    while r.returncode and TIMED_OUT in f"{r.stdout}{r.stderr}":
        if waits >= max_waits:
            print(f"{agent} still working after {max_waits} extra waits")
            return 3
        waits += 1
        r = runner(["herdr", "agent", "wait", agent, "--timeout", str(timeout)])
    if r.returncode:
        print((r.stderr or r.stdout).strip())
        return 1
    print(f"{agent} settled after {waits} extra wait{'s' if waits != 1 else ''}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("agent")
    ap.add_argument("text", nargs="?")
    ap.add_argument("--file")
    ap.add_argument("--timeout", type=int, default=540000)
    ap.add_argument("--max-waits", type=int, default=20)
    a = ap.parse_args(argv)
    if (a.text is None) == (a.file is None):
        ap.error("give the prompt as TEXT or --file, not both")
    text = pathlib.Path(a.file).read_text() if a.file else a.text
    return dispatch(a.agent, text, timeout=a.timeout, max_waits=a.max_waits)


if __name__ == "__main__":
    sys.exit(main())
