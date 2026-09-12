import re
import subprocess
import sys
from pathlib import Path

MAX_OUTPUT_CHARS = 20000


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + f"... [truncated, {len(text)} chars total]"


def run_python(root: Path, code: str, timeout: int = 30) -> dict:
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code], cwd=root, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "", "exit_code": None, "traceback": None, "timed_out": True}
    m = re.search(r"Traceback \(most recent call last\):.*", proc.stderr, re.DOTALL)
    return {
        "stdout": _truncate(proc.stdout),
        "stderr": _truncate(proc.stderr),
        "exit_code": proc.returncode,
        "traceback": _truncate(m.group(0)) if m else None,
        "timed_out": False,
    }
