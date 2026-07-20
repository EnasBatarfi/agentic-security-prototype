"""Check runtime authorization before an agent tool is executed (Tool Invocation Enforcement)."""

import pytest

from apps.agents import enforcement
from apps.authorization.actions import FILE_CONTEXT, FILE_READ, PROFILE_CONTEXT, TOOL_READ_FILE, TOOL_SEND_PASSWORD_RESET_EMAIL
from apps.files.models import UploadedFile


pytestmark = pytest.mark.django_db


def test_own_file_is_allowed_with_trusted_database_path(alice):
    """Check that an owned file is allowed using its trusted DB path."""

    # Create a file owned by the user
    upload = UploadedFile.objects.create(
        owner=alice,
        title="Note",
        file=f"users/{alice.pk}/note.txt",
    )

    # Check that the file is allowed
    authorization = enforcement.authorize_tool_invocation(
        alice,
        FILE_CONTEXT,
        TOOL_READ_FILE,
        {
            "path": "note.txt",
            "untrusted_extra": "remove me",
        },
    )

    assert authorization.allowed is True
    assert authorization.safe_args == {"path": str(upload.file)}
    assert authorization.decision is not None
    assert authorization.decision.code == "allowed"


def test_other_users_file_is_denied(alice, bob):
    """Check that policy sees and denies another user's DB resource."""

    UploadedFile.objects.create(
        owner=bob,
        title="Bob secret",
        file=f"users/{bob.pk}/secret.txt",
    )

    authorization = enforcement.authorize_tool_invocation(
        alice,
        FILE_CONTEXT,
        TOOL_READ_FILE,
        {"path": f"users/{bob.pk}/secret.txt"},
    )

    # Check the authorization result is a denial
    assert authorization.allowed is False
    assert authorization.safe_args == {}
    assert authorization.decision is not None
    assert authorization.decision.code == "default_deny"


def test_unknown_file_resource_is_denied(alice):
    """Check that a missing or unresolved file fails closed."""

    authorization = enforcement.authorize_tool_invocation(
        alice,
        FILE_CONTEXT,
        TOOL_READ_FILE,
        {"path": "missing.txt"},
    )

    assert authorization.allowed is False
    assert authorization.safe_args == {}
    assert authorization.decision is not None
    assert authorization.decision.code == "default_deny"


def test_own_password_reset_uses_trusted_account_email(alice):
    """Check that an own reset uses the authenticated account email."""

    authorization = enforcement.authorize_tool_invocation(
        alice,
        PROFILE_CONTEXT,
        TOOL_SEND_PASSWORD_RESET_EMAIL,
        {},
    )

    assert authorization.allowed is True
    assert authorization.safe_args == {
        "email": alice.email,
    }


def test_other_users_password_reset_is_denied(alice, bob):
    """Check that a user cannot reset another user's account."""

    authorization = enforcement.authorize_tool_invocation(
        alice,
        PROFILE_CONTEXT,
        TOOL_SEND_PASSWORD_RESET_EMAIL,
        {"email": bob.email},
    )

    assert authorization.allowed is False
    assert authorization.safe_args == {}
    assert authorization.decision is not None
    assert authorization.decision.code == "default_deny"


def test_unknown_tool_is_denied(alice):
    """Check that an unmapped tool fails closed."""

    authorization = enforcement.authorize_tool_invocation(
        alice,
        FILE_CONTEXT,
        "unknown_tool",
        {"path": "note.txt"},
    )

    assert authorization.allowed is False
    assert authorization.safe_args == {}
    assert authorization.decision is None


def test_tool_invocation_decision_is_audited(alice, monkeypatch):
    """Check that PEP 2 audits the trusted resource and policy decision."""

    upload = UploadedFile.objects.create(
        owner=alice,
        title="Note",
        file=f"users/{alice.pk}/note.txt",
    )
    audited = []

    monkeypatch.setattr(
        enforcement,
        "audit_decision",
        lambda request, decision: audited.append((request, decision)),
    )

    authorization = enforcement.authorize_tool_invocation(
        alice,
        FILE_CONTEXT,
        TOOL_READ_FILE,
        {"path": "note.txt"},
    )

    assert len(audited) == 1

    request, decision = audited[0]

    assert request.principal.id == str(alice.pk)
    assert request.action == FILE_READ
    assert request.resource.id == str(upload.pk)
    assert request.resource.owner_id == str(upload.owner_id)
    assert request.resource.attributes["stored_path"] == str(upload.file)
    assert request.resource.attributes["title"] == upload.title
    assert request.context.name == FILE_CONTEXT
    assert request.context.tool == TOOL_READ_FILE
    assert decision is authorization.decision
    assert decision.code == "allowed"