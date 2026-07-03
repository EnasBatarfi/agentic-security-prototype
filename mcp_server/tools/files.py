"""
File operation helpers for the custom MCP server

This module contains reusable filesystem logic used by MCP tools. The functions
are kept separate from the MCP server entrypoint so the tool behavior can be
updated independently.
"""

import shutil
from pathlib import Path
from uuid import uuid4

from ..config import MCP_ROOT, MCP_DELETED_ROOT


def build_mcp_path(path: str = "") -> Path:
    """
    Build a filesystem path using the configured MCP root.

    Example:
    When MCP_ROOT is /project/media/users/10
    a.txt -> /project/media/users/10/a.txt
    """
    root = MCP_ROOT
    target = (root / (path or ".")).resolve()

    # If the path is inside the MCP root return it
    try:
        target.relative_to(root)
    # Otherwise if the path is outside the MCP root raise an error
    except ValueError:
        raise ValueError("Path is outside MCP root.")

    return target

def to_mcp_relative(path: Path) -> str:
    """
    Return a filesystem path relative to MCP_ROOT.

    Example:
    When MCP_ROOT is /project/media/users/10
    /project/media/users/10/a.txt -> a.txt
    """
    # 
    return path.resolve().relative_to(MCP_ROOT).as_posix()


def list_files_impl(path: str) -> str:
    """
    List files and folders for a path.

    args:
        path: The path to list

    returns:
        A list of files and folders
    """
    target_path = build_mcp_path(path)

    if target_path.is_file():
        # If the target is a file return its relative path
        return to_mcp_relative(target_path)

    entries = sorted(target_path.rglob("*"), key=lambda item: item.as_posix().lower())

    # Return relative path for each entry in the directory
    return "\n".join(to_mcp_relative(entry) for entry in entries)

def search_files_impl(path: str, query: str) -> str:
    """
    Search files and folders by name.

    args:
        path: The starting path to search
        query: The search query

    returns:
        A list of matching files
    """
    words = query.lower().strip().split()
    target_path = build_mcp_path(path)

    if target_path.is_file():
        # If the target is a file return its relative path
        return to_mcp_relative(target_path)

    matches = sorted(
        (
            path
            for path in target_path.rglob("*")
            if all(word in path.name.lower() for word in words)
        ),
        key=lambda item: item.as_posix(),
    )

    # Return relative path for each match in the directory
    return "\n".join(to_mcp_relative(match) for match in matches)


def read_file_impl(path: str) -> str:
    """
    Read a text file.

    args:
        path: The path to the file to read

    returns:
        The contents of the file
    """
    target_path = build_mcp_path(path)

    return target_path.read_text(encoding="utf-8")


def delete_file_impl(path: str) -> str:
    """
    Delete a file.

    args:
        path: The path to the file to delete
    returns:
        A message indicating the file was deleted
    """
    source = build_mcp_path(path)

    # Ensure we don't delete the MCP root like the user directory
    if source == MCP_ROOT.resolve():
        raise ValueError("Cannot delete MCP root.")

    deleted_root = MCP_DELETED_ROOT
    deleted_root.mkdir(exist_ok=True)

    destination = deleted_root / f"{uuid4().hex}_{source.name}"

    # Move the file to the "_deleted" folder
    shutil.move(str(source), str(destination))

    return f"Deleted {path}"
