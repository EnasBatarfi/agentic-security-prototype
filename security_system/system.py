"""System module for enforcing application policies."""

from pathlib import Path

from .policy import FileSystemPolicy


class System:
    """Enforce application policies before protected operations."""

    def __init__(self, policy: FileSystemPolicy):
        """Initialize the system with an application policy."""

        # Require applications to use the filesystem policy interface
        if not isinstance(policy, FileSystemPolicy):
            raise TypeError("policy must implement FileSystemPolicy.")

        self.policy = policy

    def _enforce_read(self, absolute_path, identity) -> Path:
        """Enforce the application's read policy."""

        path = Path(absolute_path)

        # The application must provide one concrete absolute resource
        if not path.is_absolute():
            raise ValueError("System requires an absolute path.")

        # The application decides whether this identity may read the resource
        if self.policy.check_read(identity, path) is not True:
            raise PermissionError("Access denied.")

        # read_text only operates on existing regular files
        if not path.is_file():
            raise FileNotFoundError("Path is not a readable regular file.")

        return path

    def read_text(self, absolute_path, identity) -> str:
        """Read text only after the application policy allows it."""

        path = self._enforce_read(absolute_path, identity)

        return path.read_text(encoding="utf-8")