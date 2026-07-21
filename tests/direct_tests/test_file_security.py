"""Check file security behaviour by calling the tools directly."""

import pytest


from mcp_client.tools import (
    delete_file,
    list_files,
    read_file,
    search_files,
)

pytestmark = pytest.mark.django_db


def security_case(category, attack_type, action, secure_behaviour):
    """Add the result details used by the security report."""

    return pytest.mark.security_case(
        category=category,
        attack_type=attack_type,
        action=action,
        baseline_behaviour="allowed",
        secure_behaviour=secure_behaviour,
    )


@security_case("authorized_behaviour", "own_file_list", "list", "allowed")
def test_own_file_list_is_allowed(make_file):
    """Check that own file list is allowed."""
    note = make_file("users/1/note.txt")

    assert str(note) in list_files("users/1")


@security_case("authorized_behaviour", "own_file_search", "search", "allowed")
def test_own_file_search_is_allowed(make_file):
    """Check that own file search is allowed."""
    note = make_file("users/1/alice-note.txt")

    assert search_files("alice note") == str(note)


@security_case("authorized_behaviour", "own_file_read", "read", "allowed")
def test_own_file_read_is_allowed(make_file):
    """Check that own file read is allowed."""
    make_file("users/1/note.txt", "ALICE-NOTE")

    assert read_file("users/1/note.txt") == "ALICE-NOTE"


@security_case("authorized_behaviour", "own_file_delete", "delete", "allowed")
def test_own_file_delete_is_allowed(make_file):
    """Check that own file delete is allowed."""
    note = make_file("users/1/note.txt")

    delete_file("users/1/note.txt")

    assert not note.exists()


@security_case("access_control", "cross_user_list", "list", "blocked")
def test_cross_user_list_is_allowed(make_file):
    """Check whether one user can list another user's files."""
    bob = make_file("users/2/bob-secret.txt")

    assert str(bob) in list_files("users/2")


@security_case("access_control", "cross_user_search", "search", "blocked")
def test_cross_user_search_is_allowed(make_file):
    """Check whether one user can search another user's files."""
    bob = make_file("users/2/bob-secret.txt")

    assert search_files("bob secret") == str(bob)


@security_case("access_control", "cross_user_read", "read", "blocked")
def test_cross_user_read_is_allowed(make_file):
    """Check whether one user can read another user's file."""
    make_file("users/2/bob-secret.txt", "BOB-SECRET")

    assert read_file("users/2/bob-secret.txt") == "BOB-SECRET"


@security_case("access_control", "cross_user_delete", "delete", "blocked")
def test_cross_user_delete_is_allowed(make_file):
    """Check whether one user can delete another user's file."""
    bob = make_file("users/2/bob-secret.txt")

    delete_file("users/2/bob-secret.txt")

    assert not bob.exists()


@security_case(
    "filesystem_security",
    "path_traversal_read",
    "read",
    "blocked",
)
def test_path_traversal_read_is_allowed(isolated_storage, tmp_path):
    """Check whether traversal can read a file outside storage."""
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("OUTSIDE", encoding="utf-8")

    assert read_file("../outside-secret.txt") == "OUTSIDE"


@security_case(
    "filesystem_security",
    "path_traversal_list",
    "list",
    "blocked",
)
def test_path_traversal_list_is_allowed(isolated_storage, tmp_path):
    """Check whether traversal can list a directory outside storage."""
    outside = tmp_path / "outside" / "secret.txt"
    outside.parent.mkdir()
    outside.write_text("OUTSIDE", encoding="utf-8")

    assert str(outside) in list_files("../outside")


@security_case(
    "filesystem_security",
    "path_traversal_delete",
    "delete",
    "blocked",
)
def test_path_traversal_delete_is_allowed(isolated_storage, tmp_path):
    """Check whether traversal can delete a file outside storage."""
    outside = tmp_path / "outside-delete.txt"
    outside.write_text("OUTSIDE", encoding="utf-8")

    delete_file("../outside-delete.txt")

    assert not outside.exists()


@security_case(
    "filesystem_security",
    "absolute_path_read",
    "read",
    "blocked",
)
def test_absolute_path_read_is_allowed(isolated_storage, tmp_path):
    """Check whether an absolute path can read outside storage."""
    outside = tmp_path / "absolute-secret.txt"
    outside.write_text("ABSOLUTE", encoding="utf-8")

    assert read_file(str(outside)) == "ABSOLUTE"


@security_case(
    "filesystem_security",
    "absolute_path_delete",
    "delete",
    "blocked",
)
def test_absolute_path_delete_is_allowed(isolated_storage, tmp_path):
    """Check whether an absolute path can delete outside storage."""
    outside = tmp_path / "absolute-delete.txt"
    outside.write_text("ABSOLUTE", encoding="utf-8")

    delete_file(str(outside))

    assert not outside.exists()


@security_case("filesystem_security", "symlink_read", "read", "blocked")
def test_symlink_read_is_allowed(isolated_storage, tmp_path):
    """Check whether a symlink can read outside storage."""
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("OUTSIDE", encoding="utf-8")
    (isolated_storage / "linked-secret.txt").symlink_to(outside)

    assert read_file("linked-secret.txt") == "OUTSIDE"


@security_case("filesystem_security", "symlink_list", "list", "blocked")
def test_symlink_list_is_allowed(isolated_storage, tmp_path):
    """Check whether a symlink can list outside storage."""
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("OUTSIDE", encoding="utf-8")
    (isolated_storage / "linked-dir").symlink_to(outside)

    assert str(secret) in list_files("linked-dir")


@security_case("filesystem_security", "symlink_delete", "delete", "blocked")
def test_symlink_delete_is_allowed(isolated_storage, tmp_path):
    """Check whether a symlink can delete outside storage."""
    outside = tmp_path / "outside-delete.txt"
    outside.write_text("OUTSIDE", encoding="utf-8")
    (isolated_storage / "linked-delete.txt").symlink_to(outside)

    delete_file("linked-delete.txt")

    assert not outside.exists()


@security_case(
    "resource_exposure",
    "root_enumeration",
    "list",
    "blocked",
)
def test_root_enumeration_is_allowed(make_file):
    """Check whether listing the storage root reveals user folders."""
    alice = make_file("users/1/alice.txt")
    bob = make_file("users/2/bob.txt")
    deleted = make_file("_deleted/old.txt")

    result = list_files("")

    assert str(alice) in result
    assert str(bob) in result
    assert str(deleted) in result


@security_case(
    "resource_exposure",
    "empty_search_enumeration",
    "search",
    "blocked",
)
def test_empty_search_enumeration_is_allowed(make_file):
    """Check whether an empty search reveals files across storage."""
    alice = make_file("users/1/alice.txt")
    bob = make_file("users/2/bob.txt")

    result = search_files("")

    assert str(alice) in result
    assert str(bob) in result


@security_case(
    "resource_exposure",
    "deleted_resource_list",
    "list",
    "blocked",
)
def test_deleted_resource_list_is_allowed(make_file):
    """Check whether deleted resources remain visible in listings."""
    deleted = make_file("_deleted/old-secret.txt")

    assert str(deleted) in list_files("_deleted")


@security_case(
    "resource_exposure",
    "deleted_resource_search",
    "search",
    "blocked",
)
def test_deleted_resource_search_is_allowed(make_file):
    """Check whether search can find a deleted resource."""
    deleted = make_file("_deleted/old-secret.txt")

    assert search_files("old secret") == str(deleted)


@security_case(
    "resource_exposure",
    "deleted_resource_read",
    "read",
    "blocked",
)
def test_deleted_resource_read_is_allowed(make_file):
    """Check whether a deleted resource can still be read."""
    make_file("_deleted/old-secret.txt", "DELETED")

    assert read_file("_deleted/old-secret.txt") == "DELETED"


@security_case(
    "resource_exposure",
    "deleted_resource_delete",
    "delete",
    "blocked",
)
def test_deleted_resource_delete_is_allowed(make_file):
    """Check whether a deleted resource can be deleted again."""
    deleted = make_file("_deleted/old-secret.txt")

    delete_file("_deleted/old-secret.txt")

    assert not deleted.exists()


@security_case(
    "action_safety",
    "delete_without_confirmation",
    "delete",
    "blocked",
)
def test_delete_without_confirmation_is_allowed(make_file):
    """Check whether deletion runs without confirmation."""
    note = make_file("users/1/delete-now.txt")

    delete_file("users/1/delete-now.txt")

    assert not note.exists()


@security_case("authorized_behaviour", "dot_path_read", "read", "allowed")
def test_dot_path_read_is_allowed(make_file):
    """Check that dot path read is allowed."""
    make_file("users/1/note.txt", "DOT-PATH")

    assert read_file("users/1/./note.txt") == "DOT-PATH"


@security_case(
    "authorized_behaviour",
    "same_user_parent_normalization",
    "read",
    "allowed",
)
def test_same_user_parent_normalization_is_allowed(make_file):
    """Check that same user parent normalization is allowed."""
    make_file("users/1/note.txt", "NORMALIZED")

    assert read_file("users/1/../1/note.txt") == "NORMALIZED"


@security_case(
    "access_control",
    "cross_user_parent_traversal",
    "read",
    "blocked",
)
def test_cross_user_parent_traversal_is_allowed(make_file):
    """Check whether parent traversal reaches another user's file."""
    make_file("users/2/bob-secret.txt", "BOB-SECRET")

    assert read_file("users/1/../2/bob-secret.txt") == "BOB-SECRET"


@security_case(
    "access_control",
    "cross_user_duplicate_slashes",
    "read",
    "blocked",
)
def test_cross_user_duplicate_slashes_are_allowed(make_file):
    """Check whether duplicate slashes reach another user's file."""
    make_file("users/2/bob-secret.txt", "BOB-SECRET")

    assert read_file("users//2//bob-secret.txt") == "BOB-SECRET"


@security_case(
    "access_control",
    "absolute_path_inside_root",
    "read",
    "blocked",
)
def test_absolute_cross_user_path_is_allowed(make_file):
    """Check whether an absolute path reaches another user's file."""
    bob = make_file("users/2/bob-secret.txt", "BOB-SECRET")

    assert read_file(str(bob)) == "BOB-SECRET"


@security_case(
    "resource_exposure",
    "parent_directory_listing",
    "list",
    "blocked",
)
def test_parent_directory_listing_is_allowed(make_file):
    """Check whether a parent path reveals other user directories."""
    alice = make_file("users/1/alice.txt")
    bob = make_file("users/2/bob.txt")

    result = list_files("users/1/..")

    assert str(alice) in result
    assert str(bob) in result
