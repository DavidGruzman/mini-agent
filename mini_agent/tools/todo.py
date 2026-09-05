from pathlib import Path

from mini_agent.state import save_todo


def update_todo(root: Path, items: list[dict]) -> dict:
    save_todo(root, items)
    return {"items": items}
