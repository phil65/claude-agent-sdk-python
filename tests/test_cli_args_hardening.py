"""CLI argument and CLI discovery hardening ported from the upstream Python SDK."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from clawd_code_sdk import ClaudeAgentOptions
from clawd_code_sdk._errors import CLIConnectionError
from clawd_code_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
from clawd_code_sdk._internal.transport.subprocess_utils import (
    find_cli,
    is_windows_batch_cli,
    reject_windows_batch_cli,
    to_cli_args,
)


# --- extra_args value binding (upstream #1127) ---


def test_extra_args_dash_leading_value_uses_equals_form() -> None:
    args = to_cli_args(ClaudeAgentOptions(extra_args={"foo": "-x", "bar": "y", "flag": None}))
    assert "--foo=-x" in args
    assert args[args.index("--bar") + 1] == "y"
    assert "--flag" in args


# --- Windows batch-script refusal (upstream #1127) ---


@pytest.mark.parametrize(
    "path",
    [
        r"C:\npm\claude.cmd",
        r"C:\npm\CLAUDE.BAT",
        r"C:\npm\claude.cmd. ",
        r"C:\npm\claude.cmd:stream",
        r"C:\npm\claude:evil.cmd",
        "C:claude.cmd",
        r"C:\x\claude.cmd\..\claude.exe",
        ".cmd",
    ],
)
def test_batch_scripts_detected_on_windows(path: str) -> None:
    with patch("platform.system", return_value="Windows"):
        assert is_windows_batch_cli(path)
        with pytest.raises(CLIConnectionError, match="batch script"):
            reject_windows_batch_cli(path)


@pytest.mark.parametrize("path", [r"C:\bin\claude.exe", r"C:\cmd tools\claude.exe", "claude"])
def test_native_executables_allowed_on_windows(path: str) -> None:
    with patch("platform.system", return_value="Windows"):
        assert not is_windows_batch_cli(path)
        reject_windows_batch_cli(path)


def test_batch_check_is_windows_only() -> None:
    with patch("platform.system", return_value="Linux"):
        assert not is_windows_batch_cli("/opt/claude.cmd")


async def test_connect_refuses_batch_script_before_spawning() -> None:
    transport = SubprocessCLITransport(ClaudeAgentOptions(cli_path=r"C:\npm\claude.cmd"))
    with (
        patch("platform.system", return_value="Windows"),
        patch("anyio.open_process") as open_process,
        pytest.raises(CLIConnectionError, match="batch script"),
    ):
        await transport.connect()
    open_process.assert_not_called()


# --- Windows CLI discovery (upstream #1484) ---


def test_windows_lookup_uses_only_absolute_path_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    relative = Path("rel")
    absolute = tmp_path / "abs"
    for directory in (tmp_path / relative, absolute):
        directory.mkdir()
        (directory / "claude.exe").write_text("")
        (directory / "claude.cmd").write_text("")
    path_env = os.pathsep.join([str(relative), str(absolute)])
    monkeypatch.chdir(tmp_path)  # The relative entry would resolve here
    find_cli.cache_clear()
    try:
        with (
            patch("platform.system", return_value="Windows"),
            patch(
                "clawd_code_sdk._internal.transport.subprocess_utils.find_bundled_cli",
                return_value=None,
            ),
            patch.dict(os.environ, {"PATH": path_env}),
            patch("shutil.which", side_effect=AssertionError("which() must not be used")),
        ):
            assert find_cli() == str(absolute / "claude.exe")
    finally:
        find_cli.cache_clear()
