"""Check normalization and resolution of user-scoped file paths."""

import pytest

from mcp_client.path_helpers import normalize_user_file_path, resolve_user_file_path


# Constants for test user IDs
USER_ID = 10
OTHER_USER_ID = 11


def test_relative_and_canonical_paths_resolve_to_same_file():
    """Check that relative and DB paths resolve to the same trusted file."""

    expected = ("users/10/notes/note.txt", "notes/note.txt")

    assert resolve_user_file_path("notes/note.txt", USER_ID) == expected
    assert resolve_user_file_path("users/10/notes/note.txt", USER_ID) == expected


def test_root_path_requires_allow_root():
    """Check that the user root is returned only when root access is allowed."""

    expected = ("users/10", ".")

    assert resolve_user_file_path("", USER_ID) == expected
    assert resolve_user_file_path(".", USER_ID) == expected
    assert resolve_user_file_path("users/10", USER_ID) == expected

    assert resolve_user_file_path(".", USER_ID, allow_root=False) is None
    assert resolve_user_file_path("users/10", USER_ID, allow_root=False) is None


# Parametrize the test to check multiple harmless formatting differences that should be normalized
@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("`notes\\note.txt`", "notes/note.txt"),
        ("notes/./note.txt", "notes/note.txt"),
        ("users//10//note.txt", "users/10/note.txt"),
    ],
)
def test_safe_paths_are_normalized(path, expected):
    """Check that harmless formatting differences are normalized."""

    assert normalize_user_file_path(path) == expected


# Parametrize the test to check multiple unsafe paths that should be rejected
@pytest.mark.parametrize(
    "path",
    [
        "../note.txt",
        "users/10/../11/note.txt",
        "/tmp/note.txt",
        "C:/note.txt",
        "~/note.txt",
        "media/users/10/note.txt",
        "_deleted/note.txt",
        "notes/_deleted/note.txt",
        "bad\x00name.txt",
    ],
)
def test_unsafe_paths_are_rejected(path):
    """Check that unsafe path syntax fails closed."""

    assert normalize_user_file_path(path, allow_root=False) is None


# Parametrize the test to check multiple paths that belong to another user and should be rejected
@pytest.mark.parametrize(
    "path",
    [
        "users/11/note.txt",
        "users//11//note.txt",
        "users/11",
    ],
)
def test_other_user_paths_are_rejected(path):
    """Check that paths belonging to another user cannot be resolved."""

    assert resolve_user_file_path(path, USER_ID) is None


def test_missing_user_id_is_rejected():
    """Check that path resolution requires a trusted user identity."""

    assert resolve_user_file_path("note.txt", None) is None