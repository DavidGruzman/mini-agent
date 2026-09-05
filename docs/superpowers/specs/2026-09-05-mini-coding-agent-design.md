# Mini Coding Agent — Design Spec

## Overview

A minimalistic CLI coding agent, backed by Anthropic models, that reads and
edits code in any language within a project directory, runs code for
testing/debugging, and persists its own state in a project-local directory.

## Architecture

Single ReAct-style loop, no planner/executor split, no sub-agents.

```
CLI (interactive loop)
  -> Agent Loop (holds session messages, drives tool round-trips)
       -> LLM Client (thin Anthropic API wrapper)
       -> Tool Registry (read_file, write_file, edit_file, list_dir, grep,
                          run_python, update_todo)
            -> State Store (.miniagent/ in project root)
```

One turn = user input -> LLM call -> (tool_use blocks -> execute -> LLM call)*
-> plain text reply -> printed, loop waits for next input.

On startup, prior session state in `.miniagent/` (if present) is loaded so
the session continues where it left off. Sessions are single and continuous
per project directory — no session IDs/picker.

## LLM Client

Built directly against the Anthropic API (messages + tool use). Isolated in
one small module so a future provider swap is a contained change; no
provider abstraction layer is built now.

## Tools

All path-based tools resolve paths relative to the project root and reject
any path that escapes it.

- `read_file(path)` — file contents (large files truncated, with a note
  reporting the total size; no partial re-read of a specific range — out
  of scope for v1).
- `write_file(path, content)` — create or fully overwrite a file; returns a
  diff (or "created").
- `edit_file(path, old_string, new_string)` — exact find/replace,
  `old_string` must match exactly once; returns a diff.
- `list_dir(path=".", pattern=None, recursive=False)` — list matching
  files/dirs.
- `grep(pattern, path=".", glob=None)` — regex search across files, capped
  result count.
- `run_python(code, timeout=30)` — runs `code` as a subprocess, cwd =
  project root; returns `{stdout, stderr, exit_code, traceback}` (traceback
  parsed from stderr when present). This is the agent's only execution
  primitive — it also covers non-Python toolchains, since the Python code
  can shell out via `subprocess`.
- `update_todo(items)` — replaces the current todo list wholesale with
  `items` (`{id, text, status}`); returns the new list.

No approval/confirmation gate on any tool call (including `run_python`) —
the agent runs autonomously within the project-root sandbox.

## Project Summary (context-saving)

Not a new tool — just a convention on top of `write_file`/`edit_file`:

- On startup, if `.miniagent/summary.md` doesn't exist, the agent runs an
  initial exploration pass and writes one (architecture, key
  modules/files, conventions).
- On every startup, if it exists, its content is injected into the system
  prompt automatically (no tool call needed) — this is what saves tokens,
  by avoiding repeated re-discovery via read/grep cycles.
- The agent is instructed (system prompt) to opportunistically patch
  `summary.md` when it makes a structurally significant change. No
  staleness-detection logic — best-effort only.

## State Store

`.miniagent/` in the project root:

- `history.jsonl` — append-only conversation transcript (session resume).
- `todo.json` — current todo list.
- `summary.md` — project context summary (see above).

On a corrupt/unreadable state file, the agent logs a warning and starts
fresh rather than crashing.

## Error Handling

- Tool errors (not found, edit target not unique/missing, path outside
  root, non-zero exit, timeout) are returned as tool results with an error
  flag — visible to the model, never raised as crashes.
- API errors (rate limit, transient network) retried with backoff a small
  fixed number of times; if still failing, surfaced to the user and the
  loop pauses for the next input.

## Explicit Non-Goals (v1)

- Multi-provider LLM abstraction.
- Approval/confirmation gates on tool calls.
- Automatic staleness detection/sync for the summary file.
- Session picker / multiple named sessions per project.
- Sandbox/jail beyond project-root path restriction (no container, no
  resource limits beyond `run_python`'s timeout).
