"""Pytest configuration for e2e tests."""

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def api_key():
    os.environ["ANTHROPIC_API_KEY"] = ""


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default event loop policy for all async tests."""
    import asyncio

    return asyncio.get_event_loop_policy()


def pytest_configure(config):
    """Add e2e marker."""
    config.addinivalue_line("markers", "e2e: marks tests as e2e tests requiring API key")
