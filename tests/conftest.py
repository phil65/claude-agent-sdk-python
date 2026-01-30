"""Pytest configuration for tests."""

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def unset_anthropic_api_key():
    os.environ["ANTHROPIC_API_KEY"] = ""
