"""Small coding tools for the learning agent."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from pyhelixent.foundation import Tool, define_tool


class WorkspacePathError(ValueError):
    """Raised when a path escapes the configured workspace."""


def read_file_tool(workspace_root: str | Path) -> Tool:
    root = Path(workspace_root).resolve()

    def invoke(input: dict[str, Any]) -> Any:
        path = _resolve_workspace_path(root, input.get("path", "."))
        if not path.exists():
            return _error("FILE_NOT_FOUND", f"File {path} does not exist", path=str(path))
        if not path.is_file():
            return _error("NOT_A_FILE", f"Path {path} is not a file", path=str(path))

        start_line = input.get("start_line")
        end_line = input.get("end_line")
        max_chars = int(input.get("max_chars", 12000))

        text = path.read_text(encoding="utf-8")
        if start_line is None and end_line is None:
            return _truncate(text, max_chars)

        lines = text.splitlines()
        start = int(start_line or 1)
        end = int(end_line or len(lines))
        if start < 1 or start > len(lines):
            return _error("START_LINE_OUT_OF_RANGE", "start_line is outside the file", start_line=start)
        if end < start:
            return _error("INVALID_RANGE", "end_line must be greater than or equal to start_line")

        selected = lines[start - 1 : min(end, len(lines))]
        numbered = "\n".join(f"{line_no}: {line}" for line_no, line in enumerate(selected, start=start))
        return _truncate(numbered, max_chars)

    return define_tool(
        name="read_file",
        description="Read a file from the configured workspace.",
        parameters={
            "path": "Path relative to the workspace root, or an absolute path inside it.",
            "start_line": "Optional 1-based start line.",
            "end_line": "Optional 1-based end line.",
            "max_chars": "Optional maximum returned characters.",
        },
        invoke=_guard_path_errors(invoke),
    )


def write_file_tool(workspace_root: str | Path) -> Tool:
    root = Path(workspace_root).resolve()

    def invoke(input: dict[str, Any]) -> Any:
        path = _resolve_workspace_path(root, input["path"])
        content = str(input.get("content", ""))
        create_parents = bool(input.get("create_parents", True))
        if create_parents:
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {
            "ok": True,
            "path": str(path),
            "chars": len(content),
        }

    return define_tool(
        name="write_file",
        description="Write a text file inside the configured workspace.",
        parameters={
            "path": "Path relative to the workspace root, or an absolute path inside it.",
            "content": "Text content to write.",
            "create_parents": "Whether missing parent directories should be created.",
        },
        invoke=_guard_path_errors(invoke),
    )


def list_files_tool(workspace_root: str | Path) -> Tool:
    root = Path(workspace_root).resolve()

    def invoke(input: dict[str, Any]) -> Any:
        path = _resolve_workspace_path(root, input.get("path", "."))
        recursive = bool(input.get("recursive", False))
        max_entries = int(input.get("max_entries", 200))
        if not path.exists():
            return _error("PATH_NOT_FOUND", f"Path {path} does not exist", path=str(path))
        if path.is_file():
            return {"ok": True, "root": str(root), "files": [_display_path(root, path)]}

        iterator = path.rglob("*") if recursive else path.iterdir()
        files: list[str] = []
        for entry in sorted(iterator, key=lambda item: str(item)):
            if entry.name.startswith("."):
                continue
            files.append(_display_path(root, entry))
            if len(files) >= max_entries:
                break
        return {"ok": True, "root": str(root), "files": files, "truncated": len(files) >= max_entries}

    return define_tool(
        name="list_files",
        description="List files and directories inside the configured workspace.",
        parameters={
            "path": "Path relative to the workspace root.",
            "recursive": "Whether to list recursively.",
            "max_entries": "Maximum number of entries.",
        },
        invoke=_guard_path_errors(invoke),
    )


def grep_search_tool(workspace_root: str | Path) -> Tool:
    root = Path(workspace_root).resolve()

    def invoke(input: dict[str, Any]) -> Any:
        path = _resolve_workspace_path(root, input.get("path", "."))
        if not path.exists():
            return _error("PATH_NOT_FOUND", f"Path {path} does not exist", path=str(path))
        pattern = str(input.get("pattern", ""))
        case_sensitive = bool(input.get("case_sensitive", True))
        max_matches = int(input.get("max_matches", 50))
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            regex = re.compile(pattern, flags)
        except re.error as exc:
            return _error("INVALID_PATTERN", str(exc), pattern=pattern)

        files = [path] if path.is_file() else [item for item in path.rglob("*") if item.is_file()]
        matches: list[dict[str, Any]] = []
        for file_path in sorted(files, key=lambda item: str(item)):
            if any(part.startswith(".") for part in file_path.relative_to(root).parts):
                continue
            try:
                lines = file_path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for line_no, line in enumerate(lines, start=1):
                if regex.search(line):
                    matches.append(
                        {
                            "path": _display_path(root, file_path),
                            "line": line_no,
                            "text": line,
                        }
                    )
                    if len(matches) >= max_matches:
                        return {"ok": True, "matches": matches, "truncated": True}
        return {"ok": True, "matches": matches, "truncated": False}

    return define_tool(
        name="grep_search",
        description="Search text files inside the configured workspace using a regular expression.",
        parameters={
            "path": "Path relative to the workspace root.",
            "pattern": "Regular expression to search for.",
            "case_sensitive": "Whether matching is case-sensitive.",
            "max_matches": "Maximum number of matches.",
        },
        invoke=_guard_path_errors(invoke),
    )


def bash_tool(
    workspace_root: str | Path,
    *,
    timeout_seconds: float = 10,
    allow_dangerous: bool = False,
) -> Tool:
    root = Path(workspace_root).resolve()

    def invoke(input: dict[str, Any]) -> Any:
        command = str(input.get("command", ""))
        if not allow_dangerous and _looks_dangerous(command):
            return _error("COMMAND_BLOCKED", "Command was blocked by the learning shell policy", command=command)

        try:
            completed = subprocess.run(
                command,
                cwd=root,
                shell=True,
                executable="/bin/zsh",
                text=True,
                capture_output=True,
                timeout=float(input.get("timeout_seconds", timeout_seconds)),
                check=False,
            )
        except subprocess.TimeoutExpired:
            return _error("COMMAND_TIMEOUT", "Command timed out", command=command)

        return {
            "ok": completed.returncode == 0,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    return define_tool(
        name="bash",
        description="Run a shell command in the configured workspace with a timeout.",
        parameters={
            "command": "Shell command to run.",
            "timeout_seconds": "Optional timeout override.",
        },
        invoke=invoke,
    )


def default_coding_tools(workspace_root: str | Path) -> list[Tool]:
    """Return the default toolset for the learning coding agent."""

    return [
        read_file_tool(workspace_root),
        write_file_tool(workspace_root),
        list_files_tool(workspace_root),
        grep_search_tool(workspace_root),
        bash_tool(workspace_root),
    ]


def _resolve_workspace_path(root: Path, raw_path: Any) -> Path:
    candidate = Path(str(raw_path)).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=False)
    if resolved != root and root not in resolved.parents:
        raise WorkspacePathError(f"Path {resolved} is outside workspace {root}")
    return resolved


def _display_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated]"


def _error(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"ok": False, "code": code, "message": message, "details": details}


def _guard_path_errors(invoke):
    def wrapped(input: dict[str, Any]) -> Any:
        try:
            return invoke(input)
        except WorkspacePathError as exc:
            return _error("INVALID_PATH", str(exc))

    return wrapped


def _looks_dangerous(command: str) -> bool:
    patterns = [
        r"(^|[;&|]\s*)rm\s+(-[^\s]*r|-[^\s]*f|--recursive|--force)",
        r"(^|[;&|]\s*)git\s+reset\b",
        r"(^|[;&|]\s*)git\s+clean\b",
        r"(^|[;&|]\s*)shutdown\b",
        r"(^|[;&|]\s*)reboot\b",
        r"(^|[;&|]\s*)mkfs\b",
        r"(^|[;&|]\s*)dd\s+",
    ]
    return any(re.search(pattern, command) for pattern in patterns)
