"""Smoke test: the package imports and reports its version."""

from __future__ import annotations

import clawd_code_sdk


def test_package_imports() -> None:
    """The package can be imported and exposes a version string."""
    assert isinstance(clawd_code_sdk.__version__, str)
