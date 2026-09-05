from pathlib import Path

from mini_agent.state import save_todo


def update_todo(root: Path, items: list[dict]) -> dict:
    try:
        save_todo(root, items)
    except TypeError as e:
        return {"error": f"items not serializable: {e}"}
    return {"items": items}
