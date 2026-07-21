"""Shared pytest setup, fixtures, and result recording."""

import json
import os
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
import pytest
from django.contrib.auth import get_user_model

django.setup()

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = ROOT / "tests" / "outputs"


def pytest_addoption(parser):
    """Add the command options used by agent tests."""

    parser.addoption(
        "--run-agent",
        action="store_true",
        default=False,
        help="Run tests that call the configured LLM provider.",
    )
    parser.addoption(
        "--agent-trials",
        action="store",
        type=int,
        default=1,
        help="Number of trials for each agent security case.",
    )


def pytest_configure(config):
    """Register the test markers used in this suite."""

    config.addinivalue_line(
        "markers",
        "security_case(category, attack_type, action, expected, "
        "secure_behaviour): direct security result metadata",
    )
    config.addinivalue_line(
        "markers",
        "agent: calls the configured LLM provider and may cost money",
    )
    config.addinivalue_line(
        "markers",
        "integration: starts the MCP subprocess",
    )


def pytest_collection_modifyitems(config, items):
    """Skip paid or remote agent tests unless they are requested."""

    if config.getoption("--run-agent"):
        return

    skip = pytest.mark.skip(reason="use --run-agent to run agent tests")
    for item in items:
        if "agent" in item.keywords:
            item.add_marker(skip)


def pytest_sessionstart(session):
    """Prepare empty result lists for this test session."""

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    session.config.application_results = []
    session.config.direct_security_results = []
    session.config.agent_security_results = []


def _test_type(nodeid):
    """Get the result type from the test folder."""

    if "/application_tests/" in nodeid:
        return "application_behaviour"
    if "/direct_tests/" in nodeid:
        return "direct_security"
    if "/agent_tests/" in nodeid:
        return "agent_security"
    return None


def _security_metadata(item):
    """Read security result details from the nearest marker."""

    marker = item.get_closest_marker("security_case")
    if marker is None:
        return None
    return {
        "category": marker.kwargs["category"],
        "attack_type": marker.kwargs["attack_type"],
        "action": marker.kwargs["action"],
        "expected": marker.kwargs["expected"],
        "secure_behaviour": marker.kwargs["secure_behaviour"],
    }


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Record application and direct-security results after each test."""

    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return

    test_type = _test_type(report.nodeid)
    test_id = item.name
    common = {
        "id": test_id,
        "test_type": test_type,
        "duration_sec": round(report.duration, 6),
        "failure": str(report.longrepr) if report.failed else None,
    }
    if test_type == "application_behaviour":
        item.config.application_results.append(
            {
                **common,
                "area": Path(report.nodeid.split("::", 1)[0])
                .stem.removeprefix("test_"),
                "passed": report.passed,
            }
        )
        return

    metadata = _security_metadata(item)
    if test_type == "direct_security" and metadata:
        item.config.direct_security_results.append(
            {
                **common,
                **metadata,
                "actual": (
                    metadata["expected"] if report.passed else "not_observed"
                ),
                "passed": report.passed,
            }
        )


def _write_jsonl(name, rows):
    """Write one result object per line."""

    path = OUTPUTS_DIR / name
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def pytest_sessionfinish(session, exitstatus):
    """Save only the result groups that ran in this session."""

    if session.config.application_results:
        _write_jsonl(
            "application_results.jsonl",
            session.config.application_results,
        )
    if session.config.direct_security_results:
        _write_jsonl(
            "direct_security_results.jsonl",
            session.config.direct_security_results,
        )
    if (
        session.config.agent_security_results
        and session.config.getoption("--run-agent")
    ):
        _write_jsonl(
            "agent_security_results.jsonl",
            session.config.agent_security_results,
        )

@pytest.fixture
def user_factory(db):
    """Create test users with a safe default password."""

    def create(username, email=None, password="Test-pass-123!"):
        """Create one user for a test."""

        return get_user_model().objects.create_user(
            username=username,
            email=email or f"{username}@example.com",
            password=password,
        )

    return create


@pytest.fixture
def alice(user_factory):
    """Create the main user used by the tests."""

    return user_factory("alice")


@pytest.fixture
def bob(user_factory):
    """Create the second user used for isolation tests."""

    return user_factory("bob")


@pytest.fixture
def isolated_storage(tmp_path, settings, monkeypatch):
    """Point Django and MCP file operations at isolated temporary storage."""

    root = tmp_path / "media"
    deleted_root = root / "_deleted"

    root.mkdir()
    deleted_root.mkdir()

    settings.MEDIA_ROOT = root
    settings.MCP_FILESYSTEM_ROOT = root
    settings.MCP_DELETED_ROOT = deleted_root

    from mcp_server.tools import files as file_tools

    monkeypatch.setattr(file_tools, "MCP_ROOT", root)
    monkeypatch.setattr(file_tools, "MCP_DELETED_ROOT", deleted_root)

    return root


@pytest.fixture
def make_file(isolated_storage):
    """Create files inside the temporary MCP storage."""

    def create(relative_path, content="test content"):
        """Create one file and return its full path."""

        path = isolated_storage / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    return create
