import json
import os
from pathlib import Path


class StateError(Exception):
    pass


def resolve_project_root(start: str | None = None) -> Path:
    return Path(start or os.getcwd()).resolve()


def state_dir(root: Path) -> Path:
    d = root / ".miniagent"
    d.mkdir(exist_ok=True)
    return d


def resolve_path(root: Path, path: str) -> Path:
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise StateError(f"path '{path}' escapes project root")
    return candidate


def _sanitize_history(messages: list[dict]) -> list[dict]:
    while messages and messages[0].get("role") != "user":
        messages.pop(0)
    if messages and messages[-1].get("role") == "assistant":
        content = messages[-1]["content"]
        if isinstance(content, list) and any(b.get("type") == "tool_use" for b in content):
            messages.pop()
    return messages


def load_history_raw(root: Path) -> list[dict]:
    f = state_dir(root) / "history.jsonl"
    if not f.exists():
        return []
    return [json.loads(line) for line in f.read_text().splitlines() if line.strip()]


def load_history(root: Path) -> list[dict]:
    return _sanitize_history(load_history_raw(root))


def append_history(root: Path, message: dict) -> None:
    f = state_dir(root) / "history.jsonl"
    with f.open("a") as fh:
        fh.write(json.dumps(message) + "\n")


def load_todo(root: Path) -> list[dict]:
    f = state_dir(root) / "todo.json"
    return json.loads(f.read_text()) if f.exists() else []


def save_todo(root: Path, items: list[dict]) -> None:
    (state_dir(root) / "todo.json").write_text(json.dumps(items, indent=2))


def load_summary(root: Path) -> str | None:
    f = state_dir(root) / "summary.md"
    return f.read_text() if f.exists() else None
