"""System module for enforcing application policies."""

import os
from pathlib import Path


class System:
    """Enforce application policies before protected operations."""

    def __init__(self, policy):
        """Initialize the system with the application policy."""

        self.policy = policy

    # 1. Get the filesystem boundary granted to the current identity by the application policy
    def _allowed_root(self, identity) -> Path:
        """Return the filesystem root allowed by the policy."""

        return Path(os.path.abspath(self.policy(identity)))

    # Resolve the real filesystem location of the allowed root
    # This is used when comparing resolved targets, especially when symlinks are involved
    def _resolve_allowed_root(self, allowed_root) -> Path:
        """Resolve the real filesystem location of the allowed root."""

        return allowed_root.resolve()

    # 2. Build possible interpretations of the untrusted path
    def _candidate_paths(self, path, allowed_root):
        """Return possible filesystem targets for an untrusted path."""

        requested_path = Path(path)

        # Case 1: an absolute path already identifies its starting location
        if requested_path.is_absolute():
            return [requested_path]

        # Case 2: a relative path may be expressed from different levels of the filesystem
        # Start from the allowed root and each of its ancestors to support these representations
        roots = [allowed_root, *allowed_root.parents]
        return [root / requested_path for root in roots]

    # 3. Check whether a path stays inside a given allowed boundary
    def _is_within_allowed_root(self, path, allowed_root) -> bool:
        """Return whether a path stays inside the allowed root."""

        try:
            path.relative_to(allowed_root)
            return True
        except ValueError:
            return False
    
    # 4. Resolve the candidates and keep only paths that respect the allowed boundary
    # Two checks are required:
    # - the normalized access path must belong to the allowed namespace
    # - the real target after resolution must still belong to the allowed filesystem boundary
    def _resolve_allowed_candidates(self, path, allowed_root):
        """Resolve path candidates whose paths and real locations stay inside the allowed root."""

        allowed_candidates = []

        # Resolve the allowed root so it can be compared with resolved filesystem targets
        resolved_allowed_root = self._resolve_allowed_root(allowed_root)

        for candidate in self._candidate_paths(path, allowed_root):
            # Normalize the access path without following symlinks
            # This handles path forms such as ".", "..", and relative paths
            normalized_candidate = Path(os.path.abspath(candidate))

            # First check: the path being used to access the resource must stay inside the allowed namespace
            # This prevents access through another user's path even if that path later resolves back inside
            if not self._is_within_allowed_root(normalized_candidate, allowed_root):
                continue

            # Resolve the real filesystem target, including parent traversal and symlinks
            target = candidate.resolve()

            # Second check: the real target must also stay inside the resolved allowed boundary
            # This prevents a path inside the user's area from resolving to another user's file or outside resource
            if not self._is_within_allowed_root(target, resolved_allowed_root):
                continue

            # Different candidate interpretations may resolve to the same target, so keep it only once
            if target not in allowed_candidates:
                allowed_candidates.append(target)

        return allowed_candidates

    # 5. Keep only allowed targets that currently exist
    def _existing_allowed_candidates(self, path, allowed_root):
        """Return existing allowed candidates for an untrusted path."""

        candidates = self._resolve_allowed_candidates(path, allowed_root)

        return [candidate for candidate in candidates if candidate.exists()]
    
    # 6. Make the final path access decision and return exactly one target
    # At this point the target has already passed the boundary and existence checks
    def _enforce_path_access(self, path, identity) -> Path:
        """Enforce path access and return one allowed existing target."""

        # Get the identity's allowed root and find all existing candidates that pass enforcement
        allowed_root = self._allowed_root(identity)
        existing_candidates = self._existing_allowed_candidates(path, allowed_root)

        # Case 1: no existing allowed target was found
        if not existing_candidates:
            raise FileNotFoundError("Path was not found or is not allowed.")

        # Case 2: the input could refer to more than one allowed target, so fail instead of guessing
        if len(existing_candidates) > 1:
            raise ValueError("Path is ambiguous.")

        # Case 3: exactly one existing allowed target passed all path checks
        return existing_candidates[0]

    # 7. Enforce the resource type required by read_text
    def _enforce_file_access(self, path, identity) -> Path:
        """Enforce access to an existing allowed file."""

        target = self._enforce_path_access(path, identity)

        # read_text only accepts regular files, not directories or other filesystem objects
        if not target.is_file():
            raise FileNotFoundError("Path was not found or is not an allowed file.")

        return target

    # 8. Read the file only after all security checks pass
    #
    # Overall read_text flow:
    # 1. Get the filesystem boundary granted by the application policy
    # 2. Build possible interpretations of the untrusted path
    # 3. Normalize the access path and check that it belongs to the allowed namespace
    # 4. Resolve the real target and check that it still stays inside the allowed boundary
    # 5. Keep only targets that currently exist
    # 6. Require exactly one allowed target
    # 7. Require the target to be a regular file
    # 8. Read the file
    #
    # path + identity
    #       -> policy boundary
    #       -> candidate paths
    #       -> access-path check
    #       -> resolved-target check
    #       -> existence check
    #       -> one target
    #       -> file check
    #       -> read
    def read_text(self, path, identity) -> str:
        """Read text from an allowed filesystem target."""

        target = self._enforce_file_access(path, identity)

        return target.read_text(encoding="utf-8")