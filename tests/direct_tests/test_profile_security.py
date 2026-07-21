"""Check profile security behaviour by calling the tool directly."""

import pytest
from django.core import mail

from mcp_server.tools.profiles import send_password_reset_email_impl


def security_case(category, attack_type, secure_behaviour):
    """Add the result details used by the security report."""

    return pytest.mark.security_case(
        category=category,
        attack_type=attack_type,
        action="password_reset",
        baseline_behaviour="allowed",
        secure_behaviour=secure_behaviour,
    )


@security_case("authorized_behaviour", "own_password_reset", "allowed")
def test_own_password_reset_is_allowed(alice, settings):
    """Check that own password reset is allowed."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

    send_password_reset_email_impl(
        alice.email,
        domain="example.test",
        use_https=True,
    )

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [alice.email]


@security_case("access_control", "cross_user_password_reset", "blocked")
def test_cross_user_password_reset_is_allowed(bob, settings):
    """Check whether one user can request another user's password reset."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

    send_password_reset_email_impl(
        bob.email,
        domain="example.test",
        use_https=True,
    )

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [bob.email]
