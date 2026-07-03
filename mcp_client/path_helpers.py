"""
Path helpers for user-scoped MCP file access.

The MCP server is started with one user's filesystem root:

    media/users/<user_id>

So MCP tools expect paths relative to that root:

    note.txt
    notes/note.txt
    .

Django FileField stores paths with the user folder included:

    users/<user_id>/note.txt

This module is the boundary between the Django storage path format and
the MCP-relative path format.
Also, it normalizes and validates user paths.
"""

from pathlib import PurePosixPath

def normalize_user_file_path(path: str, *, allow_root: bool = True) -> str | None:
    """
    Normalize and validate a user-provided file path.

    Args:
        path: The raw path from the user, agent, or tool arguments.
        allow_root: Whether "." or an empty path is allowed.

    Returns:
        A normalized POSIX path string, or None if the path is invalid.

    Examples:
        "note.txt" -> "note.txt"
        "notes\\note.txt" -> "notes/note.txt"
        "`note.txt`" -> "note.txt"
        "." -> "." when allow_root=True
    """

    # Clean up the path by removing leading and trailing whitespace, quotes, and backslashes
    raw = str(path or "").strip()
    raw = raw.strip("`").strip('"').strip("'").strip()
    raw = raw.replace("\\", "/")

    # 1. If the path is empty, return invalid msg. Example: ""
    if not raw or raw == ".":
        # 2. If allow_root is True, return "." which means the root folder. Example: "."
        if allow_root:
            return "."
        return None

    # 3. If the path contains null bytes, return invalid msg. Example: "\x00"
    if "\x00" in raw:
        return None

    # 4. If the path starts with a tilde, return invalid msg. Example: "~" (Home directory)
    if raw.startswith("~"):
        return None

    # Split the path into parts
    pure_path = PurePosixPath(raw)
    parts = pure_path.parts

    # 5. If the path is absolute, return invalid msg. Example: "/note.txt"
    if pure_path.is_absolute():
        return None

    # 6. If the path contains a colon, return invalid msg. Example: "C:/note.txt" (Windows absolute path)
    if parts and ":" in parts[0]:
        return None

    # 7. If the path contains "..", return invalid msg. Example: "../note.txt"
    if ".." in parts:
        return None

    # 8. If the parts are empty, return invalid msg. 
    if not parts:
        return None

    # 9. If the first part is "media" or "_deleted", return invalid msg. Example: "media/note.txt" bc shouldn't pass the storage root, or "_deleted/note.txt" bc it shouldn't be accessable
    if parts[0] in {"media"}:
        return None
    
    # 10. If any parts contain _deleted, return invalid msg
    if "_deleted" in parts:
        return None

    # Return the normalized path
    return pure_path.as_posix()


def resolve_user_file_path(path: str, user_id: int | str, *,allow_root: bool = True,) -> tuple[str, str] | None:
    """
    Resolve user path input into Django storage path and MCP path.

    Args:
        path: The raw path from the user, agent, or tool arguments.
        user_id: The signed-in user's id.
        allow_root: Whether "." or the user's root folder is allowed.

    Returns:
        A tuple of:
            database_path: Django FileField path, like users/10/note.txt
            mcp_path: MCP-relative path, like note.txt

        Returns None if the path is invalid or outside the signed-in
        user's folder.

    Examples for user_id=10:
        "note.txt"
            -> ("users/10/note.txt", "note.txt")

        "notes/note.txt"
            -> ("users/10/notes/note.txt", "notes/note.txt")

        "users/10/note.txt"
            -> ("users/10/note.txt", "note.txt")

        "users/9/note.txt"
            -> None

        "users/10/../9/note.txt"
            -> None
    """

    if user_id is None:
        # --- DEBUGGING ---
        print(f"[SECURITY][PATH HELPER] Blocked path={path!r}: missing user ID")
        return None

    normalized_path = normalize_user_file_path(path, allow_root=allow_root)

    # If the path is None, return invalid msg. It means invalid path for any of the reasons above
    if normalized_path is None:
        # --- DEBUGGING ---
        print(f"[SECURITY][PATH HELPER] Blocked path={path!r}: invalid path syntax")
        return None

    # Get the root folder for the user
    user_root = f"users/{user_id}"

    # If the path is ".", return the user's root folder. Example: "users/10", "."
    if normalized_path == ".":
        return user_root, "."

    parts = PurePosixPath(normalized_path).parts

    # We have 2 cases:
    # 1. The path is canonical, like "users/10/note.txt" 

    # If the first part is "users":
    if parts[0] == "users":
        # If the length is less than 2 or the second part is not the user_id, return invalid msg. 
        if len(parts) < 2 or parts[1] != str(user_id):
            # --- DEBUGGING ---
            print(f"[SECURITY][PATH HELPER] Blocked path={path!r}: path belongs to another user")
            return None

        # If the length more than 2 and the second part is the user_id:
        # Check the remaining path to see if it's a valid MCP path
        remaining_parts = parts[2:]

        # If the remaining path is empty, return invalid msg
        if not remaining_parts:
            # If allow_root is True, return the user root folder
            if allow_root:
                return user_root, "."
            # --- DEBUGGING ---
            print(f"[SECURITY][PATH HELPER] Blocked path={path!r}: root path is not allowed")
            return None

        mcp_path = PurePosixPath(*remaining_parts).as_posix()
        database_path = f"{user_root}/{mcp_path}"

        return database_path, mcp_path

    # 2. The path is not canonical, like "note.txt"
    mcp_path = normalized_path
    database_path = f"{user_root}/{mcp_path}"

    return database_path, mcp_path
