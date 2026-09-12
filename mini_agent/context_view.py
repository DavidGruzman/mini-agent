import html
import json
import webbrowser
from pathlib import Path

from mini_agent import state
from mini_agent.agent_loop import build_system_prompt
from mini_agent.tools.registry import TOOL_SCHEMAS
from mini_agent.visualize import STYLE, _render_text, _render_tool_call, build_timeline

PAGE_TEMPLATE = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>mini-agent context</title>
<style>{style}</style></head>
<body>
<h1>mini-agent context &mdash; {root}</h1>
<p>This is the exact context that would be sent to the model on the next turn: the
system prompt, the available tool schemas, and the running message history.</p>
<table class="summary">
<tr><th>Section</th><th>Chars</th><th>~Tokens</th></tr>
{summary_rows}
</table>
{sections}
</body>
</html>
"""


def _tokens(chars: int) -> int:
    return round(chars / 4)


def _summary_row(name: str, chars: int) -> str:
    return f"<tr><td>{html.escape(name)}</td><td class='num'>{chars:,}</td><td class='num'>{_tokens(chars):,}</td></tr>"


def _section(title: str, body: str, open_: bool = False) -> str:
    chars = len(body)
    return (
        f'<details class="section"{" open" if open_ else ""}>'
        f'<summary>{html.escape(title)} <span class="badge">{chars:,} chars, ~{_tokens(chars):,} tokens</span></summary>'
        f'<div class="body"><pre>{html.escape(body)}</pre></div>'
        "</details>"
    )


def render_html(root: Path, system: str, tools: list[dict], messages: list[dict]) -> str:
    tools_json = json.dumps(tools, indent=2)
    messages_json = json.dumps(messages)
    rendered = [
        _render_text(e) if e["kind"] == "text" else _render_tool_call(e) for e in build_timeline(messages)
    ]

    summary_rows = "\n".join(
        [
            _summary_row("System prompt", len(system)),
            _summary_row(f"Tool schemas ({len(tools)} tools)", len(tools_json)),
            _summary_row(f"Messages ({len(messages)} messages)", len(messages_json)),
        ]
    )
    sections = "\n".join(
        [
            "<h2>System prompt</h2>",
            _section("System prompt", system, open_=True),
            f"<h2>Tool schemas <span class='badge'>{len(tools)} tools</span></h2>",
            "\n".join(_section(t["name"], json.dumps(t, indent=2)) for t in tools),
            f"<h2>Messages <span class='badge'>{len(messages)} messages</span></h2>",
            "\n".join(rendered) or "<p><em>(no messages yet)</em></p>",
        ]
    )
    return PAGE_TEMPLATE.format(style=STYLE, root=html.escape(str(root)), summary_rows=summary_rows, sections=sections)


def generate_html(root: Path, messages: list[dict], open_browser: bool = True) -> Path:
    page = render_html(root, build_system_prompt(root), TOOL_SCHEMAS, messages)
    out = state.state_dir(root) / "context.html"
    out.write_text(page)
    if open_browser:
        webbrowser.open(out.as_uri())
    return out
