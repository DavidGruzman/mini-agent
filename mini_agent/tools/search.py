import fnmatch
import re
from pathlib import Path

from mini_agent.state import resolve_path

MAX_GREP_RESULTS = 100
IGNORE_DIRS = {".git", ".miniagent", "node_modules", "__pycache__", ".venv"}


def _ignored(entry: Path, root: Path) -> bool:
    return any(part in IGNORE_DIRS for part in entry.relative_to(root).parts)


def list_dir(root: Path, path: str = ".", pattern: str | None = None, recursive: bool = False) -> dict:
    p = resolve_path(root, path)
    entries = p.rglob("*") if recursive else p.iterdir()
    names = [
        str(e.relative_to(root)) + ("/" if e.is_dir() else "")
        for e in entries
        if not _ignored(e, root) and (not pattern or fnmatch.fnmatch(e.name, pattern))
    ]
    return {"entries": sorted(names)}


def grep(root: Path, pattern: str, path: str = ".", glob: str | None = None) -> dict:
    p = resolve_path(root, path)
    regex = re.compile(pattern)
    files = [p] if p.is_file() else (p.rglob(glob) if glob else p.rglob("*"))
    matches = []
    for f in files:
        if not f.is_file() or (p.is_dir() and _ignored(f, root)):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), start=1):
            if regex.search(line):
                matches.append(f"{f.relative_to(root)}:{i}:{line.strip()}")
                if len(matches) >= MAX_GREP_RESULTS:
                    return {"matches": matches, "truncated": True}
    return {"matches": matches, "truncated": False}
