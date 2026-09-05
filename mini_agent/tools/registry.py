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
