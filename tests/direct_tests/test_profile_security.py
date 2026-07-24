"""Check profile security behaviour by calling the tool directly."""

import pytest

import helpers


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
def test_own_password_reset_is_allowed(alice):
    """Check that own password reset requires confirmation, then succeeds."""

    pending_actual, _ = helpers.password_reset(alice, alice.email)

    assert pending_actual == "confirmation_required"

    actual, result = helpers.password_reset(alice, alice.email, confirm=True)

    assert actual == "allowed"
    assert "password reset email has been sent" in result


@security_case("access_control", "cross_user_password_reset", "blocked")
def test_cross_user_password_reset_is_allowed(alice, bob):
    """Check whether one user can request another user's password reset."""
    actual, result = helpers.password_reset(alice, bob.email, confirm=True)

    assert actual == "blocked"
    assert "did not allow" in result
