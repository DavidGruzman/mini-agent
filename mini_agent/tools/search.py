import fnmatch
import re
from pathlib import Path

from mini_agent.state import StateError, resolve_path

MAX_GREP_RESULTS = 100


def list_dir(root: Path, path: str = ".", pattern: str | None = None, recursive: bool = False) -> dict:
    try:
        p = resolve_path(root, path)
    except StateError as e:
        return {"error": str(e)}
    if not p.exists():
        return {"error": f"path not found: {path}"}
    entries = p.rglob("*") if recursive else p.iterdir()
    names = []
    for entry in entries:
        if pattern and not fnmatch.fnmatch(entry.name, pattern):
            continue
        rel = str(entry.relative_to(root))
        names.append(rel + ("/" if entry.is_dir() else ""))
    return {"entries": sorted(names)}


def grep(root: Path, pattern: str, path: str = ".", glob: str | None = None) -> dict:
    try:
        p = resolve_path(root, path)
    except StateError as e:
        return {"error": str(e)}
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return {"error": f"invalid regex: {e}"}
    matches = []
    files = p.rglob(glob) if glob else p.rglob("*")
    for f in files:
        if not f.is_file():
            continue
        try:
            text = f.read_text(errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                matches.append(f"{f.relative_to(root)}:{i}:{line.strip()}")
                if len(matches) >= MAX_GREP_RESULTS:
                    return {"matches": matches, "truncated": True}
    return {"matches": matches, "truncated": False}
