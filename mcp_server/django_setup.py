"""
Django setup helper for MCP tools that need Django application services.

Some MCP tools only use local filesystem logic. Other tools need Django
features such as authentication, forms, templates, email settings, or database
access. This helper initializes Django when the MCP server runs as a separate
process.
"""

import os

import django
from django.apps import apps


def setup_django() -> None:
    """
    Initialize Django if it has not already been initialized.
    """
    # Load Django settings from the project .env file or default settings which is settings.py inside config directory
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    if not apps.ready:
        django.setup()