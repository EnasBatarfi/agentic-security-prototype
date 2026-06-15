"""
Custom MCP server entrypoint

This module defines the MCP server and registers the tools exposed to the
Django application. The server is kept outside the Django apps package so it can
run as a separate process or service.
"""

from mcp.server.fastmcp import FastMCP

from .file_tools import list_files_impl


mcp = FastMCP("Agentic SecurityCustom MCP Server")


# Current implementation note:
# For now, only the list_files tool is here for testng but other tools can be moved here later

@mcp.tool()
def list_files(path: str = "") -> str:
    """
    List files and folders using the custom MCP server.
    """
    return list_files_impl(path)


if __name__ == "__main__":
    # Use stdio because the Django MCP client already connects to MCP over stdio.
    mcp.run(transport="stdio")