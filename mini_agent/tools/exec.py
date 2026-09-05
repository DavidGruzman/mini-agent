import re
import subprocess
import sys
from pathlib import Path


def run_python(root: Path, code: str, timeout: int = 30) -> dict:
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "traceback": None,
            "timed_out": True,
        }
    traceback = None
    m = re.search(r"Traceback \(most recent call last\):.*", proc.stderr, re.DOTALL)
    if m:
        traceback = m.group(0)
    return {
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "exit_code": proc.returncode,
        "traceback": traceback,
        "timed_out": False,
    }
