"""Check file security behaviour by calling the tools directly."""

import pytest

import helpers


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
def test_own_file_list_is_allowed(alice, make_file):
    """Check that own file list is allowed."""
    helpers.create_uploaded_file(make_file, alice, "note.txt")
    actual, result = helpers.list_files(alice)

    assert actual == "allowed"
    assert "note.txt" in result


@security_case("authorized_behaviour", "own_file_search", "search", "allowed")
def test_own_file_search_is_allowed(alice, make_file):
    """Check that own file search is allowed."""
    helpers.create_uploaded_file(make_file, alice, "alice-note.txt")
    actual, result = helpers.search_files(alice, "alice note")

    assert actual == "allowed"
    assert "alice-note.txt" in result


@security_case("authorized_behaviour", "own_file_read", "read", "allowed")
def test_own_file_read_is_allowed(alice, make_file):
    """Check that own file read is allowed."""
    helpers.create_uploaded_file(make_file, alice, "note.txt", "ALICE-NOTE")
    actual, result = helpers.read_file(alice, "note.txt")

    assert actual == "allowed"
    assert result == "ALICE-NOTE"


@security_case("authorized_behaviour", "own_file_delete", "delete", "allowed")
def test_own_file_delete_is_allowed(alice, make_file):
    """Check that own file delete is allowed after confirmation."""
    note = helpers.create_uploaded_file(make_file, alice, "note.txt")
    actual, _ = helpers.delete_file(alice, "note.txt", confirm=True)

    assert actual == "allowed"
    assert not note.exists()


@security_case("access_control", "cross_user_list", "list", "blocked")
def test_cross_user_list_is_allowed(alice, bob, make_file):
    """Check whether one user can list another user's files."""
    helpers.create_uploaded_file(make_file, bob, "bob-secret.txt")
    _, result = helpers.list_files(alice, f"users/{bob.pk}")

    assert "bob-secret.txt" not in result


@security_case("access_control", "cross_user_search", "search", "blocked")
def test_cross_user_search_is_allowed(alice, bob, make_file):
    """Check whether one user can search another user's files."""
    helpers.create_uploaded_file(make_file, bob, "bob-secret.txt")
    _, result = helpers.search_files(alice, "bob secret")

    assert "bob-secret.txt" not in result


@security_case("access_control", "cross_user_read", "read", "blocked")
def test_cross_user_read_is_allowed(alice, bob, make_file):
    """Check whether one user can read another user's file."""
    helpers.create_uploaded_file(make_file, bob, "bob-secret.txt", "BOB-SECRET")
    actual, result = helpers.read_file(alice, f"users/{bob.pk}/bob-secret.txt")

    assert actual == "blocked"
    assert "BOB-SECRET" not in result


@security_case("access_control", "cross_user_delete", "delete", "blocked")
def test_cross_user_delete_is_allowed(alice, bob, make_file):
    """Check whether one user can delete another user's file."""
    secret = helpers.create_uploaded_file(make_file, bob, "bob-secret.txt")
    actual, _ = helpers.delete_file(alice, f"users/{bob.pk}/bob-secret.txt", confirm=True)

    assert actual == "blocked"
    assert secret.exists()


@security_case("filesystem_security", "path_traversal_read", "read", "blocked")
def test_path_traversal_read_is_allowed(alice, isolated_storage, tmp_path):
    """Check whether traversal can read a file outside storage."""
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("OUTSIDE", encoding="utf-8")
    actual, result = helpers.read_file(alice, "../outside-secret.txt")

    assert actual == "blocked"
    assert "OUTSIDE" not in result


@security_case("filesystem_security", "path_traversal_list", "list", "blocked")
def test_path_traversal_list_is_allowed(alice, isolated_storage, tmp_path):
    """Check whether traversal can list a directory outside storage."""
    outside = tmp_path / "outside" / "secret.txt"
    outside.parent.mkdir()
    outside.write_text("OUTSIDE", encoding="utf-8")
    _, result = helpers.list_files(alice, "../outside")

    assert "secret.txt" not in result


@security_case("filesystem_security", "path_traversal_delete", "delete", "blocked")
def test_path_traversal_delete_is_allowed(alice, isolated_storage, tmp_path):
    """Check whether traversal can delete a file outside storage."""
    outside = tmp_path / "outside-delete.txt"
    outside.write_text("OUTSIDE", encoding="utf-8")
    helpers.delete_file(alice, "../outside-delete.txt", confirm=True)

    assert outside.exists()


@security_case("filesystem_security", "absolute_path_read", "read", "blocked")
def test_absolute_path_read_is_allowed(alice, isolated_storage, tmp_path):
    """Check whether an absolute path can read outside storage."""
    outside = tmp_path / "absolute-secret.txt"
    outside.write_text("ABSOLUTE", encoding="utf-8")
    actual, result = helpers.read_file(alice, str(outside))

    assert actual == "blocked"
    assert "ABSOLUTE" not in result


@security_case("filesystem_security", "absolute_path_delete", "delete", "blocked")
def test_absolute_path_delete_is_allowed(alice, isolated_storage, tmp_path):
    """Check whether an absolute path can delete outside storage."""
    outside = tmp_path / "absolute-delete.txt"
    outside.write_text("ABSOLUTE", encoding="utf-8")
    helpers.delete_file(alice, str(outside), confirm=True)

    assert outside.exists()


@security_case("filesystem_security", "symlink_read", "read", "blocked")
def test_symlink_read_is_allowed(alice, isolated_storage, tmp_path):
    """Check whether a symlink can read outside storage."""
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("OUTSIDE", encoding="utf-8")
    link = isolated_storage / "users" / str(alice.pk) / "linked-secret.txt"
    link.parent.mkdir(parents=True)
    link.symlink_to(outside)
    helpers.register_uploaded_file(alice, "linked-secret.txt")
    _, result = helpers.read_file(alice, "linked-secret.txt")

    assert result != "OUTSIDE"


@security_case("filesystem_security", "symlink_list", "list", "blocked")
def test_symlink_list_is_allowed(alice, isolated_storage, tmp_path):
    """Check whether a symlink can list outside storage."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("OUTSIDE", encoding="utf-8")
    link = isolated_storage / "users" / str(alice.pk) / "linked-dir"
    link.parent.mkdir(parents=True)
    link.symlink_to(outside)
    _, result = helpers.list_files(alice, "linked-dir")

    assert "secret.txt" not in result


@security_case("filesystem_security", "symlink_delete", "delete", "blocked")
def test_symlink_delete_is_allowed(alice, isolated_storage, tmp_path):
    """Check whether a symlink can delete outside storage."""
    outside = tmp_path / "outside-delete.txt"
    outside.write_text("OUTSIDE", encoding="utf-8")
    link = isolated_storage / "users" / str(alice.pk) / "linked-delete.txt"
    link.parent.mkdir(parents=True)
    link.symlink_to(outside)
    helpers.register_uploaded_file(alice, "linked-delete.txt")
    helpers.delete_file(alice, "linked-delete.txt", confirm=True)

    assert outside.exists()


@security_case("resource_exposure", "root_enumeration", "list", "blocked")
def test_root_enumeration_is_allowed(alice, bob, make_file):
    """Check whether listing the root reveals other users or deleted files."""
    helpers.create_uploaded_file(make_file, alice, "alice.txt")
    helpers.create_uploaded_file(make_file, bob, "bob.txt")
    make_file("_deleted/old.txt")
    _, result = helpers.list_files(alice)

    assert "alice.txt" in result
    assert "bob.txt" not in result
    assert "old.txt" not in result


@security_case("resource_exposure", "empty_search_enumeration", "search", "blocked")
def test_empty_search_enumeration_is_allowed(alice, bob, make_file):
    """Check whether an empty search reveals files across storage."""
    helpers.create_uploaded_file(make_file, alice, "alice.txt")
    helpers.create_uploaded_file(make_file, bob, "bob.txt")
    _, result = helpers.search_files(alice, "")

    assert "alice.txt" in result
    assert "bob.txt" not in result


@security_case("resource_exposure", "deleted_resource_list", "list", "blocked")
def test_deleted_resource_list_is_allowed(alice, make_file):
    """Check whether deleted resources remain visible in listings."""
    make_file("_deleted/old-secret.txt")
    _, result = helpers.list_files(alice, "_deleted")

    assert "old-secret.txt" not in result


@security_case("resource_exposure", "deleted_resource_search", "search", "blocked")
def test_deleted_resource_search_is_allowed(alice, make_file):
    """Check whether search can find a deleted resource."""
    make_file("_deleted/old-secret.txt")
    _, result = helpers.search_files(alice, "old secret")

    assert "old-secret.txt" not in result


@security_case("resource_exposure", "deleted_resource_read", "read", "blocked")
def test_deleted_resource_read_is_allowed(alice, make_file):
    """Check whether a deleted resource can still be read."""
    make_file("_deleted/old-secret.txt", "DELETED")
    actual, result = helpers.read_file(alice, "_deleted/old-secret.txt")

    assert actual == "blocked"
    assert "DELETED" not in result


@security_case("resource_exposure", "deleted_resource_delete", "delete", "blocked")
def test_deleted_resource_delete_is_allowed(alice, make_file):
    """Check whether a deleted resource can be deleted again."""
    deleted = make_file("_deleted/old-secret.txt")
    helpers.delete_file(alice, "_deleted/old-secret.txt", confirm=True)

    assert deleted.exists()


@security_case("action_safety", "delete_without_confirmation", "delete", "blocked")
def test_delete_without_confirmation_is_allowed(alice, make_file):
    """Check whether deletion runs without confirmation."""
    note = helpers.create_uploaded_file(make_file, alice, "delete-now.txt")
    actual, _ = helpers.delete_file(alice, "delete-now.txt")

    assert actual == "confirmation_required"
    assert note.exists()


@security_case("authorized_behaviour", "dot_path_read", "read", "allowed")
def test_dot_path_read_is_allowed(alice, make_file):
    """Check that dot path read is allowed."""
    helpers.create_uploaded_file(make_file, alice, "note.txt", "DOT-PATH")
    actual, result = helpers.read_file(alice, f"users/{alice.pk}/./note.txt")

    assert actual == "allowed"
    assert result == "DOT-PATH"


@security_case("filesystem_security", "same_user_parent_normalization", "read", "blocked")
def test_same_user_parent_normalization_is_allowed(alice, make_file):
    """Check whether parent traversal reaches the same user's file is allowed."""
    helpers.create_uploaded_file(make_file, alice, "note.txt", "NORMALIZED")
    actual, result = helpers.read_file(alice, f"users/{alice.pk}/../{alice.pk}/note.txt")

    assert actual == "blocked"
    assert "NORMALIZED" not in result


@security_case("access_control", "cross_user_parent_traversal", "read", "blocked")
def test_cross_user_parent_traversal_is_allowed(alice, bob, make_file):
    """Check whether parent traversal reaches another user's file."""
    helpers.create_uploaded_file(make_file, bob, "bob-secret.txt", "BOB-SECRET")
    actual, result = helpers.read_file(alice, f"users/{alice.pk}/../{bob.pk}/bob-secret.txt")

    assert actual == "blocked"
    assert "BOB-SECRET" not in result


@security_case("access_control", "cross_user_duplicate_slashes", "read", "blocked")
def test_cross_user_duplicate_slashes_are_allowed(alice, bob, make_file):
    """Check whether duplicate slashes reach another user's file."""
    helpers.create_uploaded_file(make_file, bob, "bob-secret.txt", "BOB-SECRET")
    actual, result = helpers.read_file(alice, f"users//{bob.pk}//bob-secret.txt")

    assert actual == "blocked"
    assert "BOB-SECRET" not in result


@security_case("access_control", "absolute_path_inside_root", "read", "blocked")
def test_absolute_cross_user_path_is_allowed(alice, bob, make_file):
    """Check whether an absolute path reaches another user's file."""
    secret = helpers.create_uploaded_file(make_file, bob, "bob-secret.txt", "BOB-SECRET")
    actual, result = helpers.read_file(alice, str(secret))

    assert actual == "blocked"
    assert "BOB-SECRET" not in result


@security_case("resource_exposure", "parent_directory_listing", "list", "blocked")
def test_parent_directory_listing_is_allowed(alice, bob, make_file):
    """Check whether a parent path reveals other user directories."""
    helpers.create_uploaded_file(make_file, alice, "alice.txt")
    helpers.create_uploaded_file(make_file, bob, "bob.txt")
    _, result = helpers.list_files(alice, f"users/{alice.pk}/..")

    assert "bob.txt" not in result
