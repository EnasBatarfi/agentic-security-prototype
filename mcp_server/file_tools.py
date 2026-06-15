"""
File operation helpers for the custom MCP server

This module contains reusable filesystem logic used by MCP tools. The functions
are kept separate from the MCP server entrypoint so the tool behavior can be
updated independently.
"""

import shutil
from pathlib import Path
from uuid import uuid4

from .config import MCP_ROOT


def build_mcp_path(path: str = "") -> Path:
    """
    Build a filesystem path using the configured MCP root.

    This follows the same style as the existing Django MCP client:
    combine the MCP root with the requested path, then resolve it.
    """
    return (MCP_ROOT / (path or "")).resolve()


def list_files_impl(path: str = "") -> str:
    """
    List files and folders for a path.
    """
    target_path = build_mcp_path(path)

    entries = sorted(
        target_path.iterdir(),
        key=lambda item: item.name.lower(),
    )

    return "\n".join(str(entry) for entry in entries)

def search_files_impl(query: str) -> str:
    """
    Search files and folders by name.
    """
    pattern = "*".join(query.strip().split())

    matches = sorted(
        MCP_ROOT.rglob(f"*{pattern}*"),
        key=lambda item: item.as_posix(),
    )

    return "\n".join(str(match) for match in matches)


def read_file_impl(path: str) -> str:
    """
    Read a text file.
    """
    target_path = build_mcp_path(path)

    return target_path.read_text(encoding="utf-8")


def delete_file_impl(path: str) -> str:
    """
    Delete a file.
    """
    source = build_mcp_path(path)

    deleted_root = MCP_ROOT / "_deleted"
    deleted_root.mkdir(exist_ok=True)

    destination = deleted_root / f"{uuid4().hex}_{source.name}"

    # Move the file to the "_deleted" folder
    shutil.move(str(source), str(destination))

    return f"Deleted {path}"