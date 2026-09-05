import re
import subprocess
import sys
from pathlib import Path

MAX_OUTPUT_CHARS = 20000


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_CHARS:
        return text[:MAX_OUTPUT_CHARS] + f"\n... [truncated, {len(text)} chars total]"
    return text


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
    except (OSError, MemoryError) as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exit_code": None,
            "traceback": None,
            "timed_out": False,
        }
    traceback = None
    m = re.search(r"Traceback \(most recent call last\):.*", proc.stderr, re.DOTALL)
    if m:
        traceback = _truncate(m.group(0))
    return {
        "stdout": _truncate(proc.stdout),
        "stderr": _truncate(proc.stderr),
        "exit_code": proc.returncode,
        "traceback": traceback,
        "timed_out": False,
    }
