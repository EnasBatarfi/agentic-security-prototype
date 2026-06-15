"""
Custom MCP server entrypoint

This module defines the MCP server and registers the tools exposed to the
Django application. The server is kept outside the Django apps package so it can
run as a separate process or service.
"""

from mcp.server.fastmcp import FastMCP

from .file_tools import list_files_impl, read_file_impl, delete_file_impl, search_files_impl


mcp = FastMCP("Agentic SecurityCustom MCP Server")



@mcp.tool()
def list_files(path: str = "") -> str:
    """
    List files and folders using the custom MCP server.
    """
    return list_files_impl(path)

@mcp.tool()
def search_files(query: str) -> str:
    """
    Search files and folders using the custom MCP server.
    """
    return search_files_impl(query)


@mcp.tool()
def read_file(path: str) -> str:
    """
    Read a file using the custom MCP server.
    """
    return read_file_impl(path)


@mcp.tool()
def delete_file(path: str) -> str:
    """
    Delete a file using the custom MCP server.
    """
    return delete_file_impl(path)


if __name__ == "__main__":
    # Use stdio because the Django MCP client already connects to MCP over stdio.
    mcp.run(transport="stdio")