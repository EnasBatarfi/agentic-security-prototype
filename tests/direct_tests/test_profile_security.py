"""Check profile security behaviour by calling the tool directly."""

import pytest

from mcp_client.tools import send_password_reset_email


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

    result = send_password_reset_email(
        alice.email,
        domain="example.test",
        use_https=True,
    )

    assert "password reset email has been sent" in result


@security_case("access_control", "cross_user_password_reset", "blocked")
def test_cross_user_password_reset_is_allowed(bob, settings):
    """Check whether one user can request another user's password reset."""

    result = send_password_reset_email(
        bob.email,
        domain="example.test",
        use_https=True,
    )

    assert "password reset email has been sent" in result
