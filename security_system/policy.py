"""Policy interfaces required by the security system."""

from abc import ABC, abstractmethod
from pathlib import Path


class FileSystemPolicy(ABC):
    """Define application-specific filesystem permissions."""

    @abstractmethod
    def check_read(self, identity, absolute_path: Path) -> bool:
        """Return whether the identity may read the path."""

        raise NotImplementedError