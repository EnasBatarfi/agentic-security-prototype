"""Check the MCP client, wrappers, and server connection."""

from types import SimpleNamespace

import pytest

from apps.files.models import UploadedFile
from mcp_client import tools
from mcp_client.client import (
    _extract_text,
    call_custom_mcp_tool,
    list_custom_mcp_tools,
)


def test_mcp_text_extraction_handles_supported_result_shapes():
    """Check that MCP text extraction handles supported result shapes."""
    structured = SimpleNamespace(
        structuredContent={"content": {"status": "ok"}},
        content=[],
    )
    parts = SimpleNamespace(
        structuredContent=None,
        content=[
            SimpleNamespace(text="first"),
            SimpleNamespace(),
            SimpleNamespace(text="second"),
        ],
    )

    assert _extract_text(structured) == "{'status': 'ok'}"
    assert _extract_text(parts) == "first\nsecond"
    assert _extract_text(SimpleNamespace(content=[])) == ""


def test_file_wrappers_call_expected_mcp_tools(monkeypatch):
    """Check that file wrappers use scoped roots and MCP-relative paths."""

    calls = []

    monkeypatch.setattr(
        tools,
        "user_mcp_root",
        lambda user_id: f"/scoped/users/{user_id}",
    )
    monkeypatch.setattr(
        tools,
        "call_custom_mcp_tool",
        lambda name, arguments, filesystem_root=None: (
            calls.append((name, arguments, filesystem_root)) or "ok"
        ),
    )

    assert tools.list_files("users/1", user_id=1) == "ok"
    assert tools.search_files("notes", user_id=1) == "ok"
    assert tools.read_file("users/1/note.txt", user_id=1) == "ok"

    assert calls == [
        (
            "list_files",
            {"path": "."},
            "/scoped/users/1",
        ),
        (
            "search_files",
            {
                "path": ".",
                "query": "notes",
            },
            "/scoped/users/1",
        ),
        (
            "read_file",
            {"path": "note.txt"},
            "/scoped/users/1",
        ),
    ]


@pytest.mark.django_db
def test_delete_wrapper_removes_matching_database_record(monkeypatch, alice, isolated_storage):
    """Check that delete uses trusted identity and removes its DB record."""

    upload = UploadedFile.objects.create(
        owner=alice,
        title="note",
        file=f"users/{alice.pk}/note.txt",
    )
    calls = []

    monkeypatch.setattr(
        tools,
        "call_custom_mcp_tool",
        lambda name, arguments, filesystem_root=None: (
            calls.append((name, arguments, filesystem_root))
            or "Deleted note.txt"
        ),
    )

    result = tools.delete_file(
        f"users/{alice.pk}/note.txt",
        user_id=alice.pk,
    )

    assert result == "Deleted note.txt"
    assert calls == [
        (
            "delete_file",
            {"path": "note.txt"},
            str(isolated_storage / "users" / str(alice.pk)),
        )
    ]
    assert not UploadedFile.objects.filter(pk=upload.pk).exists()


@pytest.mark.integration
def test_mcp_server_exposes_expected_tools(isolated_storage):
    """Check that MCP server exposes expected tools."""
    assert set(list_custom_mcp_tools()) == {
        "list_files",
        "search_files",
        "read_file",
        "delete_file",
        "send_password_reset_email",
    }


@pytest.mark.integration
def test_mcp_round_trip_reads_file(make_file):
    """Check that MCP reads through a user-scoped filesystem root."""

    note = make_file(
        "users/1/mcp-note.txt",
        "MCP-ROUND-TRIP",
    )

    result = call_custom_mcp_tool(
        "read_file",
        {"path": note.name},
        filesystem_root=str(note.parent),
    )

    assert result == "MCP-ROUND-TRIP"
