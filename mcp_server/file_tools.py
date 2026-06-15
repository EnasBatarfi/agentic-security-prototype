"""
File operation helpers for the custom MCP server

This module contains reusable filesystem logic used by MCP tools. The functions
are kept separate from the MCP server entrypoint so the tool behavior can be
updated independently.
"""

from pathlib import Path

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