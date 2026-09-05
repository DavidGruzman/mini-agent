import html
import json
import webbrowser
from pathlib import Path

from mini_agent import state

PAGE_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>mini-agent trajectory</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif;
         max-width: 900px; margin: 2rem auto; padding: 0 1rem; background: #f7f7f8; color: #1b1b1f; }}
  .msg {{ padding: 0.6rem 1rem; margin: 0.6rem 0; border-radius: 8px; white-space: pre-wrap; word-wrap: break-word; }}
  .msg.user {{ background: #e3ecff; }}
  .msg.assistant {{ background: #ffffff; border: 1px solid #ddd; }}
  .msg .role {{ font-weight: 600; font-size: 0.8rem; text-transform: uppercase;
                color: #666; display: block; margin-bottom: 0.25rem; }}
  details.tool {{ margin: 0.6rem 0; border: 1px solid #ddd; border-radius: 8px;
                  background: #fbf8f0; overflow: hidden; }}
  details.tool summary {{ padding: 0.5rem 1rem; cursor: pointer; font-family: monospace; }}
  details.tool .tool-body {{ padding: 0.75rem 1rem; border-top: 1px solid #ddd; }}
  details.tool h4 {{ margin: 0.5rem 0 0.25rem; font-size: 0.8rem; text-transform: uppercase; color: #666; }}
  details.tool pre {{ white-space: pre-wrap; word-wrap: break-word; background: #f0f0f0;
                      padding: 0.5rem; border-radius: 4px; margin: 0; }}
  h1 {{ font-size: 1.2rem; }}
</style>
</head>
<body>
<h1>mini-agent trajectory &mdash; {root}</h1>
{entries}
</body>
</html>
"""


def _short_repr(value, limit=80) -> str:
    text = json.dumps(value) if not isinstance(value, str) else value
    text = text.replace("\n", " ")
    if len(text) > limit:
        text = text[:limit] + "..."
    return text


def build_timeline(messages: list[dict]) -> list[dict]:
    timeline = []
    pending = {}
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if role == "user":
            if isinstance(content, str):
                timeline.append({"kind": "text", "role": "user", "text": content})
            elif isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_result":
                        continue
                    entry = pending.pop(block.get("tool_use_id"), None)
                    output = block.get("content")
                    if entry is not None:
                        entry["output"] = output
                    else:
                        timeline.append(
                            {"kind": "tool_call", "name": "(unmatched tool_result)", "input": None, "output": output}
                        )
        elif role == "assistant":
            if isinstance(content, str):
                timeline.append({"kind": "text", "role": "assistant", "text": content})
            elif isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")
                    if btype == "text":
                        timeline.append({"kind": "text", "role": "assistant", "text": block.get("text", "")})
                    elif btype == "tool_use":
                        entry = {"kind": "tool_call", "name": block.get("name", "?"), "input": block.get("input"), "output": None}
                        timeline.append(entry)
                        tool_use_id = block.get("id")
                        if tool_use_id is not None:
                            pending[tool_use_id] = entry
                    else:
                        timeline.append({"kind": "text", "role": "assistant", "text": f"[{btype}] {json.dumps(block)}"})
    return timeline


def _render_text(entry: dict) -> str:
    return (
        f'<div class="msg {entry["role"]}">'
        f'<span class="role">{html.escape(entry["role"])}</span>'
        f'{html.escape(entry["text"])}'
        f"</div>"
    )


def _render_tool_call(entry: dict) -> str:
    input_preview = _short_repr(entry["input"]) if entry["input"] is not None else ""
    if entry["output"] is None:
        status = "(no result recorded)"
    else:
        status = f"{len(entry['output'])} chars"
    summary = html.escape(f"\U0001f527 {entry['name']}({input_preview}) → {status}")
    input_json = html.escape(json.dumps(entry["input"], indent=2)) if entry["input"] is not None else "(none)"
    output_text = html.escape(entry["output"]) if entry["output"] is not None else "(none)"
    return (
        '<details class="tool">'
        f"<summary>{summary}</summary>"
        '<div class="tool-body">'
        f"<h4>Input</h4><pre>{input_json}</pre>"
        f"<h4>Output</h4><pre>{output_text}</pre>"
        "</div>"
        "</details>"
    )


def render_html(root: Path, timeline: list[dict]) -> str:
    parts = []
    for entry in timeline:
        if entry["kind"] == "text":
            parts.append(_render_text(entry))
        else:
            parts.append(_render_tool_call(entry))
    return PAGE_TEMPLATE.format(root=html.escape(str(root)), entries="\n".join(parts))


def generate_html(root: Path, open_browser: bool = True) -> Path:
    messages = state.load_history_raw(root)
    timeline = build_timeline(messages)
    page = render_html(root, timeline)
    out = state.state_dir(root) / "trajectory.html"
    out.write_text(page)
    if open_browser:
        webbrowser.open(out.as_uri())
    return out
