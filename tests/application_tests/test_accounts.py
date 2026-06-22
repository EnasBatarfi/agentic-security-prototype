"""Check the normal signup, login, and profile behaviour."""

import pytest
from django.urls import reverse

from apps.accounts.views import SignUpForm


def test_signup_creates_and_logs_in_user(client, db):
    """Check that signup creates and logs in user."""
    response = client.post(
        reverse("signup"),
        {
            "username": "new-user",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
            "password1": "Safe-pass-123!",
            "password2": "Safe-pass-123!",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("file_list")
    assert "_auth_user_id" in client.session


def test_signup_normalizes_identity_fields(db):
    """Check that signup normalizes identity fields."""
    form = SignUpForm(
        {
            "username": "  Alice  ",
            "email": "  ALICE@EXAMPLE.COM ",
            "first_name": " Alice ",
            "last_name": " Example ",
            "password1": "Safe-pass-123!",
            "password2": "Safe-pass-123!",
        }
    )

    assert form.is_valid(), form.errors
    user = form.save()
    assert user.username == "alice"
    assert user.email == "alice@example.com"
    assert user.first_name == "Alice"
    assert user.last_name == "Example"


@pytest.mark.parametrize(
    "field,value",
    [
        ("username", "ALICE"),
        ("email", "ALICE@EXAMPLE.COM"),
    ],
)
def test_signup_rejects_duplicate_identity_case_insensitively(alice, field, value):
    """Check that signup rejects duplicate identity case insensitively."""
    data = {
        "username": "different",
        "email": "different@example.com",
        "first_name": "A",
        "last_name": "B",
        "password1": "Safe-pass-123!",
        "password2": "Safe-pass-123!",
    }
    data[field] = value

    form = SignUpForm(data)

    assert not form.is_valid()
    assert field in form.errors


@pytest.mark.parametrize(
    "url_name",
    ["file_list", "file_upload", "file_chat", "profile_chat", "profile"],
)
def test_protected_pages_require_login(client, url_name):
    """Check that protected pages require login."""
    response = client.get(reverse(url_name))

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


def test_profile_page_shows_logged_in_user(client, alice):
    """Check that profile page shows logged in user."""
    client.force_login(alice)

    response = client.get(reverse("profile"))

    assert response.status_code == 200
    assert response.context["profile_user"] == alice


def test_signup_page_shows_required_identity_fields(client):
    """Check that signup page shows required identity fields."""
    response = client.get(reverse("signup"))

    assert response.status_code == 200
    for label in (
        "Username",
        "Email",
        "First name",
        "Last name",
        "Password",
        "Password confirmation",
    ):
        assert label in response.content.decode()


def test_signup_rejects_empty_required_fields(client, db):
    """Check that signup rejects empty required fields."""
    response = client.post(reverse("signup"), {})

    assert response.status_code == 200
    assert {
        "username",
        "email",
        "first_name",
        "last_name",
        "password1",
        "password2",
    } <= set(response.context["form"].errors)


def test_login_rejects_invalid_credentials(client, db):
    """Check that login rejects invalid credentials."""
    response = client.post(
        reverse("login"),
        {"username": "missing-user", "password": "wrong-password"},
    )

    assert response.status_code == 200
    assert response.context["form"].non_field_errors()
    assert "_auth_user_id" not in client.session


def test_logout_ends_authenticated_session(client, alice):
    """Check that logout ends authenticated session."""
    client.force_login(alice)

    response = client.post(reverse("logout"))

    assert response.status_code == 302
    assert response.url == reverse("login")
    assert "_auth_user_id" not in client.session
