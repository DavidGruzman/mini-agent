from pathlib import Path

from mini_agent import state
from mini_agent.llm_client import LLMClient
from mini_agent.tools.registry import TOOL_SCHEMAS, build_registry

MAX_ITERATIONS = 50
MAX_RESULT_CHARS = 50000

BASE_SYSTEM_PROMPT = """You are a minimalistic coding agent. You can read, search, \
edit, and run code in the project rooted at the current directory using the \
provided tools. Keep .miniagent/summary.md up to date: if a change you make \
would make it stale (new module, changed architecture), patch the relevant \
section using write_file/edit_file. Use update_todo to track multi-step work \
when a task has more than a couple of steps."""

SUMMARY_BOOTSTRAP_INSTRUCTION = """No project summary exists yet. Explore this \
codebase using list_dir, grep, and read_file, then call write_file to create \
.miniagent/summary.md summarizing the architecture, key modules/files, and \
conventions. Keep it concise. Do not ask the user anything - just do this now."""


def build_system_prompt(root: Path) -> str:
    summary = state.load_summary(root)
    if summary is None:
        return BASE_SYSTEM_PROMPT
    return BASE_SYSTEM_PROMPT + "\n\n== Project summary ==\n" + summary


def run_turn(root: Path, client: LLMClient, messages: list[dict]) -> list[dict]:
    registry = build_registry(root)
    for _ in range(MAX_ITERATIONS):
        response = client.send(build_system_prompt(root), messages, TOOL_SCHEMAS)
        assistant_content = [block.model_dump() for block in response.content]
        assistant_message = {"role": "assistant", "content": assistant_content}
        messages.append(assistant_message)
        state.append_history(root, assistant_message)

        tool_uses = [b for b in assistant_content if b["type"] == "tool_use"]
        if not tool_uses:
            print("\n".join(b["text"] for b in assistant_content if b["type"] == "text"))
            return messages

        tool_results = []
        for block in tool_uses:
            fn = registry.get(block["name"])
            try:
                result = fn(block["input"]) if fn else {"error": f"unknown tool: {block['name']}"}
            except Exception as e:
                result = {"error": str(e)}
            content = str(result)
            if len(content) > MAX_RESULT_CHARS:
                content = content[:MAX_RESULT_CHARS] + f"... [truncated, {len(content)} chars total]"
            tool_results.append({"type": "tool_result", "tool_use_id": block["id"], "content": content})

        tool_message = {"role": "user", "content": tool_results}
        messages.append(tool_message)
        state.append_history(root, tool_message)
    print(f"(warning: stopped after {MAX_ITERATIONS} tool round-trips without finishing)")
    return messages


def ensure_summary(root: Path, client: LLMClient, messages: list[dict]) -> list[dict]:
    if state.load_summary(root) is not None:
        return messages
    user_message = {"role": "user", "content": SUMMARY_BOOTSTRAP_INSTRUCTION}
    messages.append(user_message)
    state.append_history(root, user_message)
    return run_turn(root, client, messages)
