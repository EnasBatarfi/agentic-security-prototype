"""
Profile operation helpers for the custom MCP server.

This module contains reusable profile/account logic used by MCP tools. The
functions are kept separate from the MCP server entrypoint so the tool behavior
can be updated independently.
"""

from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm


def send_password_reset_email_impl(
    email: str,
    domain: str = "localhost:8000",
    use_https: bool = False,
) -> str:
    """
    Send a password reset email using Django's password reset flow.
    """
    form = PasswordResetForm({"email": email})

    if not form.is_valid():
        return "Enter a valid email address."

    form.save(
        domain_override=domain,
        subject_template_name="registration/password_reset_subject.txt",
        email_template_name="registration/password_reset_email.html",
        use_https=use_https,
        from_email=settings.DEFAULT_FROM_EMAIL,
    )
    
    return "If an account exists with that email address, a password reset email has been sent."