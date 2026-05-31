from pathlib import Path
from uuid import uuid4

from django.conf import settings
from langchain_core.tools import tool

from apps.files.models import UploadedFile

from .client import call_mcp_tool, mcp_path


DELETED_FOLDER_NAME = "_deleted"


def list_files(path: str = "") -> str:
    """List files through the MCP filesystem server."""
    
    # List all files and folders in the given path
    return call_mcp_tool("list_directory",{"path": mcp_path(path)},)


def search_files(query: str) -> str:
    """Search files through the external MCP filesystem server."""

    # Search for files matching the query pattern in the entire MCP filesystem
    return call_mcp_tool("search_files",{"path": mcp_path(""),"pattern": query,},)


def read_file(path: str) -> str:
    """Read a file through the external MCP filesystem server."""

    # Read the contents of the specified file
    return call_mcp_tool("read_text_file",{"path": mcp_path(path)},)


def delete_file(path: str) -> str:
    """Delete a file through the external MCP filesystem server."""

    # Instead of permanently deleting the file, we move it to a "_deleted" folder in the MCP filesystem
    deleted_root = Path(settings.MCP_FILESYSTEM_ROOT).resolve() / DELETED_FOLDER_NAME

    # Ensure the "_deleted" folder exists
    call_mcp_tool("create_directory",{"path": str(deleted_root)},)

    destination = deleted_root / f"{uuid4().hex}_{Path(path).name}"
    # Move the file to the "_deleted" folder in the MCP filesystem
    call_mcp_tool("move_file",{"source": mcp_path(path),"destination": str(destination),},)

    # Also delete the corresponding UploadedFile record in the Django database
    UploadedFile.objects.filter(file=path).delete()

    return f"Deleted {path}"


# These just to expose the above functions as tools to be used by the agent
@tool("list_files")
def list_files_tool(path: str = "") -> str:
    """List uploaded files and folders by path."""

    return list_files(path)


@tool("search_files")
def search_files_tool(query: str) -> str:
    """Search uploaded files by filename pattern."""

    return search_files(query)


@tool("read_file")
def read_file_tool(path: str) -> str:
    """Read an uploaded file by path."""

    return read_file(path)


@tool("delete_file")
def delete_file_tool(path: str) -> str:
    """Delete an uploaded file by path."""

    return delete_file(path)


def get_tools():
    """Return the tools used by the agent."""

    return [
        list_files_tool,
        search_files_tool,
        read_file_tool,
        delete_file_tool,
    ]