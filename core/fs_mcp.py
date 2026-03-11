import asyncio
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from django.conf import settings


USERS_ROOT = Path(settings.FILE_SANDBOX_ROOT).resolve()

server_params = StdioServerParameters(
    command="npx",
    args=[
        "-y",
        "@modelcontextprotocol/server-filesystem",
        str(USERS_ROOT),
    ],
)


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


async def _call_tool(tool_name: str, arguments: dict):
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return result


def _extract_text(result) -> str:
    if hasattr(result, "structuredContent") and result.structuredContent:
        content = result.structuredContent.get("content")
        if content is not None:
            return content

    if hasattr(result, "content") and result.content:
        first = result.content[0]
        if hasattr(first, "text"):
            return first.text

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

    asyncio.run(_call_tool("create_directory", {"path": str(target.parent)}))

    asyncio.run( _call_tool("write_file", {"path": str(target), "content": content}))