"""Run an explicit command, saving combined output and its real exit status."""

import datetime as dt
from pathlib import Path
import shlex
import subprocess
import sys
from zoneinfo import ZoneInfo


def main():
    output_path = Path(sys.argv[1])
    command = sys.argv[2:]
    if not command:
        raise SystemExit("Usage: run_and_record.py OUTPUT COMMAND [ARG ...]")
    started = dt.datetime.now(ZoneInfo("America/Los_Angeles")).isoformat()
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    transcript = (
        f"Started (America/Los_Angeles): {started}\n"
        f"Working directory: {Path.cwd()}\n"
        f"Command: {shlex.join(command)}\n\n"
        f"{result.stdout}\nExit status: {result.returncode}\n"
    )
    output_path.write_text(transcript, encoding="utf-8")
    print(transcript, end="")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
