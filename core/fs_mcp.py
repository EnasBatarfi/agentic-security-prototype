import asyncio
from pathlib import Path

# Import MCP client session and server parameters to connect to the MCP server
from mcp import ClientSession, StdioServerParameters
# stdio_client used to open connection to the MCP server over standard i/o
from mcp.client.stdio import stdio_client

from django.conf import settings


# Main root for all users data
USERS_ROOT = Path(settings.FILE_SANDBOX_ROOT).resolve()

# This is to start the MCP server 
# So Python will run this in the background:
# npx -y @modelcontextprotocol/server-filesystem <users_root>
# I passed the main users root here because the MCP server needs one allowed root
server_params = StdioServerParameters(
    command="npx",
    args=["-y","@modelcontextprotocol/server-filesystem",str(USERS_ROOT),],
)


# This helper function is to clean common junk the model may pass
# Such as `res.txt` or empty strings ... etc
def clean_rel_path(rel_path: str) -> str:
    if rel_path is None:
        raise ValueError("empty path not allowed")

    rel_path = rel_path.strip()
    rel_path = rel_path.strip("`").strip('"').strip("'")
    rel_path = rel_path.strip()

    if rel_path == "":
        raise ValueError("empty path not allowed")

    if "\x00" in rel_path:
        raise ValueError("null bytes not allowed")

    if rel_path.startswith("~"):
        raise ValueError("tilde paths not allowed")

    if "\\" in rel_path:
        raise ValueError("backslashes not allowed")

    return rel_path


def user_root(user_id: int) -> Path:
    root = USERS_ROOT / str(user_id)
    root.mkdir(parents=True, exist_ok=True)
    return root


# It makes sure the final path stays inside the current user's sandbox and avoids escaping or absolute paths
# Such as `/etc/passwd`, or `../2/secret.txt` - accessing other users' data
def resolve_safe_user_path(user_id: int, rel_path: str) -> Path:
    root = user_root(user_id)
    rel_path = clean_rel_path(rel_path)

    p = Path(rel_path)

    if p.is_absolute():
        raise ValueError("absolute paths not allowed")

    full = (root / p).resolve()
    root_resolved = root.resolve()

    if full != root_resolved and root_resolved not in full.parents:
        raise ValueError("path escapes sandbox")

    return full


# This is start a connection to the MCP server then open client session and call a tool
# It is async function because the MCP server is running asynchronously
async def _call_tool(tool_name: str, arguments: dict):
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return result


# Because mcp results are not always plain text so this helper extracts the text
# It checks the common result shapes returned by the mcp server
def _extract_text(result) -> str:
    if hasattr(result, "structuredContent") and result.structuredContent:
        content = result.structuredContent.get("content")
        if content is not None:
            return content

    if hasattr(result, "content") and result.content:
        first = result.content[0]
        if hasattr(first, "text"):
            return first.text

    # If nothing matches then return empty string
    return ""


def list_tree_mcp(user_id: int, rel_path: str = "") -> list[str]:
    base = user_root(user_id) if rel_path == "" else resolve_safe_user_path(user_id, rel_path)

    result = asyncio.run(_call_tool("list_directory", {"path": str(base)}))
    text = _extract_text(result)

    if not text:
        return []

    return text.splitlines()


def read_file_mcp(user_id: int, rel_path: str) -> str:
    target = resolve_safe_user_path(user_id, rel_path)

    result = asyncio.run( _call_tool("read_text_file", {"path": str(target)}))
    return _extract_text(result)


def write_file_mcp(user_id: int, rel_path: str, content: str) -> None:
    target = resolve_safe_user_path(user_id, rel_path)

    # Make sure the parent directory exists if not create it! 
    asyncio.run(_call_tool("create_directory", {"path": str(target.parent)}))

    asyncio.run( _call_tool("write_file", {"path": str(target), "content": content}))