"""
Configuration for the custom MCP server

This module loads environment variables and defines shared path settings used by
the MCP server. It is kept independent from Django settings so the MCP server can
run as a separate process or service.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# Project root:
# mcp_server/config.py -> mcp_server/ -> project root
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from the project .env file
load_dotenv(BASE_DIR / ".env")


def resolve_project_path(value: str) -> Path:
    """
    Convert a relative project path into an absolute path.

    Example:
    "media" -> "/path/to/project/media"
    """
    path = Path(value)

    if not path.is_absolute():
        path = BASE_DIR / path

    return path.resolve()


# Filesystem root used by the MCP server
# This can be passed from Django through the MCP_FILESYSTEM_ROOT environment variable
MCP_ROOT = resolve_project_path(os.getenv("MCP_FILESYSTEM_ROOT", "media"))