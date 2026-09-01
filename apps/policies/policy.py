"""Application-specific policies used by the security system."""

from pathlib import Path

from django.conf import settings

from security_system.helpers import is_path_within
from security_system.policy import FileSystemPolicy


class ApplicationFilePolicy(FileSystemPolicy):
    """Define filesystem permissions for this application."""

    def check_read(self, identity, absolute_path: Path) -> bool:
        """Return whether the user may read the path."""

        # This application's users may read files inside their own upload directory
        user_root = Path(settings.MCP_FILESYSTEM_ROOT) / "users" / str(identity)

        return is_path_within(absolute_path, user_root)