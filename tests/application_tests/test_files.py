"""Check the normal file upload, list, and delete behaviour."""

from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.files.models import UploadedFile, uploaded_file_path


def test_uploaded_file_path_uses_owner_directory(alice):
    """Check that uploaded files use the owner directory."""
    upload = UploadedFile(owner=alice)

    assert uploaded_file_path(upload, "notes.txt") == (
        f"users/{alice.pk}/notes.txt"
    )


def test_upload_uses_original_filename_when_title_is_empty(client, alice, isolated_storage):
    """Check that upload uses original filename when title is empty."""
    client.force_login(alice)

    response = client.post(
        reverse("file_upload"),
        {"title": "", "file": SimpleUploadedFile("report.txt", b"REPORT")},
    )

    record = UploadedFile.objects.get(owner=alice)
    assert response.status_code == 302
    assert record.title == "report.txt"
    assert record.file.name == f"users/{alice.pk}/report.txt"
    assert Path(record.file.path).read_text(encoding="utf-8") == "REPORT"


def test_invalid_upload_does_not_create_record(client, alice, isolated_storage):
    """Check that invalid upload does not create record."""
    client.force_login(alice)

    response = client.post(reverse("file_upload"), {"title": "No file"})

    assert response.status_code == 200
    assert not UploadedFile.objects.filter(owner=alice).exists()


def test_file_list_shows_current_users_records(client, alice, bob, isolated_storage):
    """Check that the file list only shows the current user’s records."""
    UploadedFile.objects.create(
        owner=alice,
        title="Alice file",
        file=f"users/{alice.pk}/a.txt",
    )
    UploadedFile.objects.create(
        owner=bob,
        title="Bob file",
        file=f"users/{bob.pk}/b.txt",
    )
    client.force_login(alice)

    response = client.get(reverse("file_list"))

    assert [item.title for item in response.context["files"]] == ["Alice file"]


def test_file_delete_calls_mcp_with_owned_path(client, alice, isolated_storage, monkeypatch):
    """Check that file deletion sends the owned path to MCP."""
    upload = UploadedFile.objects.create(
        owner=alice,
        title="Alice file",
        file=f"users/{alice.pk}/alice.txt",
    )
    calls = []
    monkeypatch.setattr(
        "apps.files.views.mcp_delete_file",
        lambda path: calls.append(path) or "Deleted",
    )
    client.force_login(alice)

    response = client.post(reverse("file_delete", args=[upload.pk]))

    assert response.status_code == 302
    assert calls == [f"users/{alice.pk}/alice.txt"]


def test_file_delete_failure_preserves_record(client, alice, isolated_storage, monkeypatch):
    """Check that a failed file deletion preserves the database record."""
    upload = UploadedFile.objects.create(
        owner=alice,
        title="Alice file",
        file=f"users/{alice.pk}/alice.txt",
    )

    def fail(_path):
        """Simulate the MCP delete call being unavailable."""

        raise RuntimeError("MCP unavailable")

    monkeypatch.setattr("apps.files.views.mcp_delete_file", fail)
    client.force_login(alice)

    response = client.post(
        reverse("file_delete", args=[upload.pk]),
        follow=True,
    )

    assert response.status_code == 200
    assert UploadedFile.objects.filter(pk=upload.pk).exists()
    assert "File delete failed." in {
        str(message) for message in response.context["messages"]
    }


def test_file_list_displays_saved_path(client, alice, isolated_storage):
    """Check that file list displays saved path."""
    UploadedFile.objects.create(
        owner=alice,
        title="Path check",
        file=f"users/{alice.pk}/path-check.txt",
    )
    client.force_login(alice)

    response = client.get(reverse("file_list"))

    assert f"users/{alice.pk}/path-check.txt" in response.content.decode()


def test_get_request_does_not_delete_file(client, alice, isolated_storage, monkeypatch):
    """Check that get request does not delete file."""
    upload = UploadedFile.objects.create(
        owner=alice,
        title="Keep me",
        file=f"users/{alice.pk}/keep.txt",
    )
    calls = []
    monkeypatch.setattr(
        "apps.files.views.mcp_delete_file",
        lambda path: calls.append(path),
    )
    client.force_login(alice)

    response = client.get(reverse("file_delete", args=[upload.pk]))

    assert response.status_code == 302
    assert calls == []
    assert UploadedFile.objects.filter(pk=upload.pk).exists()
