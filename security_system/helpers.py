"""Reusable helpers for implementing filesystem policies."""

import os
from pathlib import Path


def is_path_within(path, root) -> bool:
    """Return whether a path stays within a filesystem root."""

    path = Path(path)
    root = Path(root)

    # Policy helpers operate on concrete absolute filesystem paths
    if not path.is_absolute() or not root.is_absolute():
        raise ValueError("Path and root must be absolute.")

    # Normalize the access paths without following symlinks
    normalized_path = Path(os.path.abspath(path))
    normalized_root = Path(os.path.abspath(root))

    # The access path itself must belong to the configured root
    if not normalized_path.is_relative_to(normalized_root):
        return False

    # The real target must also remain inside the real root
    resolved_path = normalized_path.resolve()
    resolved_root = normalized_root.resolve()

    return resolved_path.is_relative_to(resolved_root)