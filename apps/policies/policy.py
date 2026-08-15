"""Application-specific policies used by the security system."""

from pathlib import Path
from django.conf import settings


def file_policy(user_id: int | str) -> Path:
    """Return the filesystem root allowed for the user."""

    # Build the user's allowed directory from the application storage structure
    return Path(settings.MCP_FILESYSTEM_ROOT) / "users" / str(user_id)