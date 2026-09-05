import difflib
from pathlib import Path

from mini_agent.state import StateError, resolve_path

MAX_READ_CHARS = 20000


def read_file(root: Path, path: str) -> dict:
    try:
        p = resolve_path(root, path)
    except StateError as e:
        return {"error": str(e)}
    if not p.exists():
        return {"error": f"file not found: {path}"}
    text = p.read_text(errors="replace")
    if len(text) > MAX_READ_CHARS:
        text = text[:MAX_READ_CHARS] + f"\n... [truncated, {len(text)} chars total]"
    return {"content": text}


def write_file(root: Path, path: str, content: str) -> dict:
    try:
        p = resolve_path(root, path)
    except StateError as e:
        return {"error": str(e)}
    before = p.read_text(errors="replace") if p.exists() else None
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    if before is None:
        return {"diff": f"created {path}"}
    diff = "\n".join(
        difflib.unified_diff(before.splitlines(), content.splitlines(), lineterm="")
    )
    return {"diff": diff or "(no changes)"}


def edit_file(root: Path, path: str, old_string: str, new_string: str) -> dict:
    try:
        p = resolve_path(root, path)
    except StateError as e:
        return {"error": str(e)}
    if not p.exists():
        return {"error": f"file not found: {path}"}
    text = p.read_text(errors="replace")
    count = text.count(old_string)
    if count == 0:
        return {"error": "old_string not found"}
    if count > 1:
        return {"error": f"old_string is not unique ({count} matches)"}
    new_text = text.replace(old_string, new_string, 1)
    p.write_text(new_text)
    diff = "\n".join(
        difflib.unified_diff(text.splitlines(), new_text.splitlines(), lineterm="")
    )
    return {"diff": diff}
