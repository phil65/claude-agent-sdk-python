"""Sandbox + settings merge fails closed (upstream #1426)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from clawd_code_sdk._errors import CLIConnectionError
from clawd_code_sdk.models import ClaudeAgentOptions
from clawd_code_sdk.models.settings import Sandbox


if TYPE_CHECKING:
    from pathlib import Path


def _sandbox() -> Sandbox:
    return Sandbox(enabled=True)


def test_missing_settings_file_raises(tmp_path: Path) -> None:
    options = ClaudeAgentOptions(settings=tmp_path / "missing.json", sandbox=_sandbox())
    with pytest.raises(CLIConnectionError, match="Cannot read settings file"):
        options.build_settings_value()


def test_relative_settings_path_resolves_against_cwd(tmp_path: Path) -> None:
    (tmp_path / "s.json").write_text(json.dumps({"permissions": {"allow": ["Read"]}}))
    options = ClaudeAgentOptions(settings="s.json", sandbox=_sandbox(), cwd=tmp_path)
    value = options.build_settings_value()
    assert value is not None
    merged = json.loads(value)
    assert merged["permissions"] == {"allow": ["Read"]}
    assert merged["sandbox"]["enabled"] is True


def test_non_object_settings_file_raises(tmp_path: Path) -> None:
    (tmp_path / "s.json").write_text("[1, 2]")
    options = ClaudeAgentOptions(settings=tmp_path / "s.json", sandbox=_sandbox())
    with pytest.raises(CLIConnectionError, match="must contain a JSON object"):
        options.build_settings_value()


def test_inline_settings_json_is_merged() -> None:
    options = ClaudeAgentOptions(settings='{"model": "opus"}', sandbox=_sandbox())
    value = options.build_settings_value()
    assert value is not None
    assert json.loads(value)["model"] == "opus"


def test_malformed_inline_json_raises_without_echoing_it() -> None:
    secret = '{"apiKeyHelper": "sk-secret"'
    options = ClaudeAgentOptions(settings=secret, sandbox=_sandbox())
    with pytest.raises(CLIConnectionError) as exc_info:
        options.build_settings_value()
    assert "sk-secret" not in str(exc_info.value)


def test_settings_path_without_sandbox_is_passed_through(tmp_path: Path) -> None:
    options = ClaudeAgentOptions(settings=tmp_path / "missing.json")
    assert options.build_settings_value() == str(tmp_path / "missing.json")
