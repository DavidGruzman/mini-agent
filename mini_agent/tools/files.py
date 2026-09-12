import difflib
from pathlib import Path

from mini_agent.state import resolve_path

MAX_READ_CHARS = 20000


def read_file(root: Path, path: str) -> dict:
    text = resolve_path(root, path).read_text(encoding="utf-8")
    if len(text) > MAX_READ_CHARS:
        text = text[:MAX_READ_CHARS] + f"\n... [truncated, {len(text)} chars total]"
    return {"content": text}


def write_file(root: Path, path: str, content: str) -> dict:
    p = resolve_path(root, path)
    before = p.read_text() if p.exists() else None
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    if before is None:
        return {"diff": f"created {path}"}
    diff = "\n".join(difflib.unified_diff(before.splitlines(), content.splitlines(), lineterm=""))
    return {"diff": diff or "(no changes)"}


def edit_file(root: Path, path: str, old_string: str, new_string: str) -> dict:
    p = resolve_path(root, path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old_string)
    if count != 1:
        return {"error": f"old_string matched {count} times, expected exactly 1"}
    new_text = text.replace(old_string, new_string, 1)
    p.write_text(new_text, encoding="utf-8")
    diff = "\n".join(difflib.unified_diff(text.splitlines(), new_text.splitlines(), lineterm=""))
    return {"diff": diff}
