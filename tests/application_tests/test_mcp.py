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
    """Check that file wrappers call expected mcp tools."""
    calls = []
    monkeypatch.setattr(
        tools,
        "call_custom_mcp_tool",
        lambda name, arguments: calls.append((name, arguments)) or "ok",
    )

    assert tools.list_files("users/1") == "ok"
    assert tools.search_files("notes") == "ok"
    assert tools.read_file("users/1/note.txt") == "ok"
    assert calls == [
        ("list_files", {"path": "users/1"}),
        ("search_files", {"query": "notes"}),
        ("read_file", {"path": "users/1/note.txt"}),
    ]


@pytest.mark.django_db
def test_delete_wrapper_removes_matching_database_record(monkeypatch, alice, isolated_storage):
    """Check that delete wrapper removes matching database record."""
    upload = UploadedFile.objects.create(
        owner=alice,
        title="note",
        file=f"users/{alice.pk}/note.txt",
    )
    monkeypatch.setattr(
        tools,
        "call_custom_mcp_tool",
        lambda name, arguments: f"Deleted users/{alice.pk}/note.txt",
    )

    tools.delete_file(f"users/{alice.pk}/note.txt")

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
    """Check that MCP round trip reads file."""
    make_file("users/1/mcp-note.txt", "MCP-ROUND-TRIP")

    result = call_custom_mcp_tool(
        "read_file",
        {"path": "users/1/mcp-note.txt"},
    )

    assert result == "MCP-ROUND-TRIP"
