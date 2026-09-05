# Mini Coding Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimalistic CLI coding agent (Python, Anthropic API) that reads/edits code in any language, runs code for testing/debugging, and persists its own state in a project-local `.miniagent/` directory.

**Architecture:** A single ReAct-style loop (`agent_loop.py`) drives round-trips between an Anthropic API wrapper (`llm_client.py`) and a small tool registry (`tools/`), backed by a plain-file state store (`state.py`). No planner/executor split, no sub-agents, no provider abstraction.

**Tech Stack:** Python 3.10+, `anthropic` SDK, stdlib only otherwise (no test framework, no mocking libs — per explicit instruction to skip unit tests and simulations).

**Spec:** `docs/superpowers/specs/2026-09-05-mini-coding-agent-design.md`

## Global Constraints

- All path-based tools resolve paths relative to the project root and reject any path that escapes it (from spec's Tools section).
- No approval/confirmation gate on any tool call, including `run_python` (spec: "no approval/confirmation gates on tool calls" is an explicit non-goal).
- `run_python` is the agent's only execution primitive — no separate shell tool (spec's Tools section).
- Single continuous session per project directory — no session IDs/picker (spec's non-goals).
- Anthropic API only, isolated in one small module (`llm_client.py`) — no multi-provider abstraction (spec's non-goals).
- `summary.md` sync is best-effort/opportunistic only — no staleness-detection logic (spec's non-goals).
- No unit tests, no mocked/simulated integration tests — verification is via direct manual execution of small scripts or the real CLI (explicit user instruction, overrides this skill's default TDD step structure).

---

## File Structure

```
mini_agent/
  __init__.py
  __main__.py       # `python -m mini_agent` entry point
  state.py          # project root resolution, path jailing, .miniagent/ read/write
  llm_client.py      # Anthropic API wrapper with retry
  agent_loop.py      # ReAct loop, system prompt + summary bootstrap
  cli.py             # interactive stdin/stdout loop
  tools/
    __init__.py
    files.py          # read_file, write_file, edit_file
    search.py         # list_dir, grep
    exec.py            # run_python
    todo.py             # update_todo
    registry.py         # name -> callable dispatch + Anthropic tool schemas
pyproject.toml
```

Each file has one responsibility: `state.py` never talks to the LLM or subprocess; `tools/*.py` never touch `.miniagent/` directly except `todo.py` (which delegates to `state.save_todo`); `agent_loop.py` is the only place that knows how a "turn" is structured; `cli.py` is a thin I/O shell around `agent_loop`.

---

### Task 1: Project scaffolding + state store

**Files:**
- Create: `pyproject.toml`
- Create: `mini_agent/__init__.py`
- Create: `mini_agent/state.py`

**Interfaces:**
- Produces: `state.StateError(Exception)`; `state.resolve_project_root(start: str | None = None) -> Path`; `state.state_dir(root: Path) -> Path`; `state.resolve_path(root: Path, path: str) -> Path` (raises `StateError` if `path` escapes `root`); `state.load_history(root) -> list[dict]`; `state.append_history(root, message: dict) -> None`; `state.load_todo(root) -> list[dict]`; `state.save_todo(root, items: list[dict]) -> None`; `state.load_summary(root) -> str | None`.

- [ ] **Step 1: Create project scaffolding**

`pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "mini-agent"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["anthropic>=0.40.0"]

[project.scripts]
mini-agent = "mini_agent.cli:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["mini_agent*"]
```

`mini_agent/__init__.py`:
```python
```

- [ ] **Step 2: Install the package in editable mode**

Run: `pip install -e .`
Expected: installs successfully (pulls in `anthropic` if not already present).

- [ ] **Step 3: Write `mini_agent/state.py`**

```python
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


def load_history(root: Path) -> list[dict]:
    f = state_dir(root) / "history.jsonl"
    if not f.exists():
        return []
    messages = []
    try:
        with f.open() as fh:
            for line in fh:
                line = line.strip()
                if line:
                    messages.append(json.loads(line))
    except (json.JSONDecodeError, OSError):
        return []
    return messages


def append_history(root: Path, message: dict) -> None:
    f = state_dir(root) / "history.jsonl"
    with f.open("a") as fh:
        fh.write(json.dumps(message) + "\n")


def load_todo(root: Path) -> list[dict]:
    f = state_dir(root) / "todo.json"
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def save_todo(root: Path, items: list[dict]) -> None:
    f = state_dir(root) / "todo.json"
    f.write_text(json.dumps(items, indent=2))


def load_summary(root: Path) -> str | None:
    f = state_dir(root) / "summary.md"
    if not f.exists():
        return None
    try:
        return f.read_text()
    except OSError:
        return None
```

- [ ] **Step 4: Verify**

Run (from the repo root):
```bash
python3 -c "
import sys, tempfile
sys.path.insert(0, '.')
from pathlib import Path
from mini_agent import state

d = Path(tempfile.mkdtemp())
root = state.resolve_project_root(str(d))

assert state.load_history(root) == []
state.append_history(root, {'role': 'user', 'content': 'hi'})
assert state.load_history(root) == [{'role': 'user', 'content': 'hi'}]

assert state.load_todo(root) == []
state.save_todo(root, [{'id': '1', 'text': 'do x', 'status': 'open'}])
assert state.load_todo(root) == [{'id': '1', 'text': 'do x', 'status': 'open'}]

assert state.load_summary(root) is None

p = state.resolve_path(root, 'sub/file.txt')
assert str(p).startswith(str(root))
try:
    state.resolve_path(root, '../escape.txt')
    assert False, 'should have raised'
except state.StateError:
    pass

print('OK')
"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml mini_agent/__init__.py mini_agent/state.py
git commit -m "$(cat <<'EOF'
Add project scaffolding and state store

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MDqzuFqo6YbkFmWZ8Er3hp
EOF
)"
```

---

### Task 2: File tools

**Files:**
- Create: `mini_agent/tools/__init__.py`
- Create: `mini_agent/tools/files.py`

**Interfaces:**
- Consumes: `state.resolve_path(root, path) -> Path` (raises `state.StateError`) from Task 1.
- Produces: `files.read_file(root, path) -> dict` (`{"content": str}` or `{"error": str}`); `files.write_file(root, path, content) -> dict` (`{"diff": str}` or `{"error": str}`); `files.edit_file(root, path, old_string, new_string) -> dict` (`{"diff": str}` or `{"error": str}`).

- [ ] **Step 1: Write `mini_agent/tools/__init__.py`**

```python
```

- [ ] **Step 2: Write `mini_agent/tools/files.py`**

```python
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
```

- [ ] **Step 3: Verify**

```bash
python3 -c "
import sys, tempfile
sys.path.insert(0, '.')
from pathlib import Path
from mini_agent.tools import files

root = Path(tempfile.mkdtemp())

r = files.write_file(root, 'a.txt', 'hello\n')
assert 'created' in r['diff']

r = files.read_file(root, 'a.txt')
assert r['content'] == 'hello\n'

r = files.edit_file(root, 'a.txt', 'hello', 'goodbye')
assert 'goodbye' in (root / 'a.txt').read_text()

r = files.edit_file(root, 'a.txt', 'nope', 'x')
assert 'error' in r

r = files.read_file(root, 'missing.txt')
assert 'error' in r

r = files.read_file(root, '../escape.txt')
assert 'error' in r

print('OK')
"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add mini_agent/tools/__init__.py mini_agent/tools/files.py
git commit -m "$(cat <<'EOF'
Add file tools (read_file, write_file, edit_file)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MDqzuFqo6YbkFmWZ8Er3hp
EOF
)"
```

---

### Task 3: Search tools

**Files:**
- Create: `mini_agent/tools/search.py`

**Interfaces:**
- Consumes: `state.resolve_path(root, path) -> Path` from Task 1.
- Produces: `search.list_dir(root, path=".", pattern=None, recursive=False) -> dict` (`{"entries": list[str]}` or `{"error": str}`); `search.grep(root, pattern, path=".", glob=None) -> dict` (`{"matches": list[str], "truncated": bool}` or `{"error": str}`).

- [ ] **Step 1: Write `mini_agent/tools/search.py`**

```python
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
```

- [ ] **Step 2: Verify**

```bash
python3 -c "
import sys, tempfile
sys.path.insert(0, '.')
from pathlib import Path
from mini_agent.tools import search

root = Path(tempfile.mkdtemp())
(root / 'sub').mkdir()
(root / 'sub' / 'foo.py').write_text('def foo():\n    return 42\n')
(root / 'bar.py').write_text('x = 1\n')

r = search.list_dir(root)
assert 'bar.py' in r['entries'] and 'sub/' in r['entries']

r = search.list_dir(root, recursive=True)
assert 'sub/foo.py' in r['entries']

r = search.grep(root, 'return')
assert any('foo.py:2' in m for m in r['matches'])

r = search.grep(root, '[invalid(')
assert 'error' in r

print('OK')
"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add mini_agent/tools/search.py
git commit -m "$(cat <<'EOF'
Add search tools (list_dir, grep)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MDqzuFqo6YbkFmWZ8Er3hp
EOF
)"
```

---

### Task 4: Exec and todo tools

**Files:**
- Create: `mini_agent/tools/exec.py`
- Create: `mini_agent/tools/todo.py`

**Interfaces:**
- Consumes: `state.save_todo(root, items)` from Task 1.
- Produces: `exec.run_python(root, code, timeout=30) -> dict` (`{"stdout": str, "stderr": str, "exit_code": int | None, "traceback": str | None, "timed_out": bool}`); `todo.update_todo(root, items: list[dict]) -> dict` (`{"items": list[dict]}`).

- [ ] **Step 1: Write `mini_agent/tools/exec.py`**

```python
import re
import subprocess
import sys
from pathlib import Path


def run_python(root: Path, code: str, timeout: int = 30) -> dict:
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "traceback": None,
            "timed_out": True,
        }
    traceback = None
    m = re.search(r"Traceback \(most recent call last\):.*", proc.stderr, re.DOTALL)
    if m:
        traceback = m.group(0)
    return {
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "exit_code": proc.returncode,
        "traceback": traceback,
        "timed_out": False,
    }
```

- [ ] **Step 2: Write `mini_agent/tools/todo.py`**

```python
from pathlib import Path

from mini_agent.state import save_todo


def update_todo(root: Path, items: list[dict]) -> dict:
    save_todo(root, items)
    return {"items": items}
```

- [ ] **Step 3: Verify**

```bash
python3 -c "
import sys, tempfile
sys.path.insert(0, '.')
from pathlib import Path
from mini_agent.tools import exec as exec_tool, todo

root = Path(tempfile.mkdtemp())

r = exec_tool.run_python(root, 'print(1+1)')
assert r['stdout'].strip() == '2'
assert r['exit_code'] == 0

r = exec_tool.run_python(root, 'raise ValueError(\"boom\")')
assert r['exit_code'] != 0
assert 'ValueError' in r['traceback']

r = exec_tool.run_python(root, 'import time; time.sleep(5)', timeout=1)
assert r['timed_out'] is True

r = todo.update_todo(root, [{'id': '1', 'text': 'x', 'status': 'open'}])
assert r['items'][0]['id'] == '1'
assert (root / '.miniagent' / 'todo.json').exists()

print('OK')
"
```
Expected: `OK` (takes ~1s due to the timeout case)

- [ ] **Step 4: Commit**

```bash
git add mini_agent/tools/exec.py mini_agent/tools/todo.py
git commit -m "$(cat <<'EOF'
Add run_python and update_todo tools

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MDqzuFqo6YbkFmWZ8Er3hp
EOF
)"
```

---

### Task 5: Tool registry

**Files:**
- Create: `mini_agent/tools/registry.py`

**Interfaces:**
- Consumes: `files.read_file/write_file/edit_file`, `search.list_dir/grep`, `exec.run_python`, `todo.update_todo` from Tasks 2-4.
- Produces: `registry.build_registry(root: Path) -> dict[str, Callable[[dict], dict]]`; `registry.TOOL_SCHEMAS: list[dict]` (Anthropic tool-use schemas, `name` field matches every key in `build_registry`'s return).

- [ ] **Step 1: Write `mini_agent/tools/registry.py`**

```python
from pathlib import Path

from . import files, search, todo
from . import exec as exec_tool


def build_registry(root: Path) -> dict:
    return {
        "read_file": lambda i: files.read_file(root, i["path"]),
        "write_file": lambda i: files.write_file(root, i["path"], i["content"]),
        "edit_file": lambda i: files.edit_file(
            root, i["path"], i["old_string"], i["new_string"]
        ),
        "list_dir": lambda i: search.list_dir(
            root, i.get("path", "."), i.get("pattern"), i.get("recursive", False)
        ),
        "grep": lambda i: search.grep(root, i["pattern"], i.get("path", "."), i.get("glob")),
        "run_python": lambda i: exec_tool.run_python(root, i["code"], i.get("timeout", 30)),
        "update_todo": lambda i: todo.update_todo(root, i["items"]),
    }


TOOL_SCHEMAS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file relative to the project root.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Create or fully overwrite a file with the given content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace an exact, unique occurrence of old_string with new_string in a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
    {
        "name": "list_dir",
        "description": "List files/directories under a path, optionally recursive and pattern-filtered.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "pattern": {"type": "string"},
                "recursive": {"type": "boolean"},
            },
        },
    },
    {
        "name": "grep",
        "description": "Regex search across files under a path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
                "glob": {"type": "string"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "run_python",
        "description": "Run Python code as a subprocess in the project root; returns stdout, stderr, exit_code, and parsed traceback.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "timeout": {"type": "integer"},
            },
            "required": ["code"],
        },
    },
    {
        "name": "update_todo",
        "description": "Replace the current todo list wholesale with the given items.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "text": {"type": "string"},
                            "status": {"type": "string"},
                        },
                        "required": ["id", "text", "status"],
                    },
                }
            },
            "required": ["items"],
        },
    },
]
```

- [ ] **Step 2: Verify**

```bash
python3 -c "
import sys, tempfile
sys.path.insert(0, '.')
from pathlib import Path
from mini_agent.tools.registry import build_registry, TOOL_SCHEMAS

root = Path(tempfile.mkdtemp())
registry = build_registry(root)

schema_names = {s['name'] for s in TOOL_SCHEMAS}
assert schema_names == set(registry.keys())

r = registry['write_file']({'path': 'a.txt', 'content': 'hi'})
assert 'created' in r['diff']

r = registry['read_file']({'path': 'a.txt'})
assert r['content'] == 'hi'

r = registry['list_dir']({})
assert 'a.txt' in r['entries']

r = registry['run_python']({'code': 'print(42)'})
assert r['stdout'].strip() == '42'

r = registry['update_todo']({'items': []})
assert r['items'] == []

print('OK')
"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add mini_agent/tools/registry.py
git commit -m "$(cat <<'EOF'
Add tool registry with Anthropic tool schemas

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MDqzuFqo6YbkFmWZ8Er3hp
EOF
)"
```

---

### Task 6: LLM client

**Files:**
- Create: `mini_agent/llm_client.py`

**Interfaces:**
- Produces: `LLMClient(model: str = DEFAULT_MODEL)`; `LLMClient.send(system: str, messages: list[dict], tools: list[dict]) -> anthropic.types.Message`.

- [ ] **Step 1: Write `mini_agent/llm_client.py`**

```python
import os
import time

import anthropic

DEFAULT_MODEL = os.environ.get("MINI_AGENT_MODEL", "claude-sonnet-5")
MAX_RETRIES = 3


class LLMClient:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.client = anthropic.Anthropic()
        self.model = model

    def send(self, system: str, messages: list[dict], tools: list[dict]):
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system,
                    messages=messages,
                    tools=tools,
                )
            except anthropic.APIError as e:
                last_error = e
                time.sleep(2 ** attempt)
        raise last_error
```

- [ ] **Step 2: Verify**

```bash
python3 -c "
import os, sys
sys.path.insert(0, '.')
from mini_agent.llm_client import LLMClient

if not os.environ.get('ANTHROPIC_API_KEY'):
    print('SKIPPED (no ANTHROPIC_API_KEY set)')
else:
    client = LLMClient()
    resp = client.send('Reply with exactly: pong', [{'role': 'user', 'content': 'ping'}], [])
    text = ''.join(b.text for b in resp.content if b.type == 'text')
    assert 'pong' in text.lower()
    print('OK')
"
```
Expected: `OK`, or `SKIPPED (no ANTHROPIC_API_KEY set)` if no key is configured in this environment.

- [ ] **Step 3: Commit**

```bash
git add mini_agent/llm_client.py
git commit -m "$(cat <<'EOF'
Add Anthropic LLM client wrapper with retry

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MDqzuFqo6YbkFmWZ8Er3hp
EOF
)"
```

---

### Task 7: Agent loop

**Files:**
- Create: `mini_agent/agent_loop.py`

**Interfaces:**
- Consumes: `state.load_summary`, `state.append_history` from Task 1; `registry.build_registry`, `registry.TOOL_SCHEMAS` from Task 5; `LLMClient.send` from Task 6.
- Produces: `agent_loop.build_system_prompt(root: Path) -> str`; `agent_loop.run_turn(root: Path, client: LLMClient, messages: list[dict]) -> list[dict]`; `agent_loop.ensure_summary(root: Path, client: LLMClient, messages: list[dict]) -> list[dict]`.

- [ ] **Step 1: Write `mini_agent/agent_loop.py`**

```python
from pathlib import Path

from mini_agent import state
from mini_agent.llm_client import LLMClient
from mini_agent.tools.registry import TOOL_SCHEMAS, build_registry

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
    if summary:
        return BASE_SYSTEM_PROMPT + "\n\n== Project summary ==\n" + summary
    return BASE_SYSTEM_PROMPT


def run_turn(root: Path, client: LLMClient, messages: list[dict]) -> list[dict]:
    registry = build_registry(root)
    while True:
        system = build_system_prompt(root)
        response = client.send(system, messages, TOOL_SCHEMAS)
        assistant_content = [block.model_dump() for block in response.content]
        assistant_message = {"role": "assistant", "content": assistant_content}
        messages.append(assistant_message)
        state.append_history(root, assistant_message)

        tool_uses = [b for b in assistant_content if b["type"] == "tool_use"]
        if not tool_uses:
            texts = [b["text"] for b in assistant_content if b["type"] == "text"]
            print("\n".join(texts))
            return messages

        tool_results = []
        for block in tool_uses:
            fn = registry.get(block["name"])
            if fn is None:
                result = {"error": f"unknown tool: {block['name']}"}
            else:
                result = fn(block["input"])
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block["id"],
                    "content": str(result),
                }
            )
        tool_message = {"role": "user", "content": tool_results}
        messages.append(tool_message)
        state.append_history(root, tool_message)


def ensure_summary(root: Path, client: LLMClient, messages: list[dict]) -> list[dict]:
    if state.load_summary(root) is not None:
        return messages
    user_message = {"role": "user", "content": SUMMARY_BOOTSTRAP_INSTRUCTION}
    messages.append(user_message)
    state.append_history(root, user_message)
    return run_turn(root, client, messages)
```

- [ ] **Step 2: Verify**

```bash
python3 -c "
import os, sys, tempfile
sys.path.insert(0, '.')
from pathlib import Path

if not os.environ.get('ANTHROPIC_API_KEY'):
    print('SKIPPED (no ANTHROPIC_API_KEY set)')
else:
    from mini_agent import agent_loop
    from mini_agent.llm_client import LLMClient

    root = Path(tempfile.mkdtemp())
    (root / 'hello.py').write_text('print(\"hi\")\n')

    client = LLMClient()
    messages = []
    messages = agent_loop.ensure_summary(root, client, messages)
    assert (root / '.miniagent' / 'summary.md').exists()

    messages.append({
        'role': 'user',
        'content': 'What does hello.py print? Answer in one short sentence, do not modify any files.',
    })
    messages = agent_loop.run_turn(root, client, messages)
    assert messages[-1]['role'] == 'assistant'
    print('OK')
"
```
Expected: `OK` (prints the bootstrap exploration output and the final answer along the way), or `SKIPPED (no ANTHROPIC_API_KEY set)`.

- [ ] **Step 3: Commit**

```bash
git add mini_agent/agent_loop.py
git commit -m "$(cat <<'EOF'
Add ReAct agent loop with summary bootstrap

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MDqzuFqo6YbkFmWZ8Er3hp
EOF
)"
```

---

### Task 8: CLI entrypoint

**Files:**
- Create: `mini_agent/cli.py`
- Create: `mini_agent/__main__.py`

**Interfaces:**
- Consumes: `state.resolve_project_root`, `state.load_history`, `state.append_history` from Task 1; `LLMClient` from Task 6; `agent_loop.ensure_summary`, `agent_loop.run_turn` from Task 7.
- Produces: `cli.main() -> None` (also registered as the `mini-agent` console script and reachable via `python -m mini_agent`).

- [ ] **Step 1: Write `mini_agent/cli.py`**

```python
from mini_agent import agent_loop, state
from mini_agent.llm_client import LLMClient


def main():
    root = state.resolve_project_root()
    messages = state.load_history(root)
    client = LLMClient()

    messages = agent_loop.ensure_summary(root, client, messages)

    print(f"mini-agent ready in {root}. Type your instruction (Ctrl-D to exit).")
    while True:
        try:
            user_input = input("> ")
        except EOFError:
            print()
            break
        if not user_input.strip():
            continue
        user_message = {"role": "user", "content": user_input}
        messages.append(user_message)
        state.append_history(root, user_message)
        messages = agent_loop.run_turn(root, client, messages)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write `mini_agent/__main__.py`**

```python
from mini_agent.cli import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify end-to-end**

```bash
demo=$(mktemp -d)
echo 'print("hi")' > "$demo/hello.py"
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "SKIPPED (no ANTHROPIC_API_KEY set)"
else
  ( cd "$demo" && printf 'What does hello.py print? Answer in one short sentence, do not modify any files.\n' | python3 -m mini_agent )
  ls "$demo/.miniagent"
fi
```
Expected (when a key is set): the agent prints its summary-bootstrap exploration, then an answer mentioning `hi`; `$demo/.miniagent` contains `history.jsonl`, `todo.json`, and `summary.md`.

- [ ] **Step 4: Commit**

```bash
git add mini_agent/cli.py mini_agent/__main__.py
git commit -m "$(cat <<'EOF'
Add CLI entrypoint

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MDqzuFqo6YbkFmWZ8Er3hp
EOF
)"
```
