"""Message parser for Claude Code SDK responses."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from clawd_code_sdk._errors import MessageParseError
from clawd_code_sdk.models import message_adapter


if TYPE_CHECKING:
    from clawd_code_sdk.models import Message

logger = logging.getLogger(__name__)

_RECORD_PATH = os.environ.get("CLAWD_RECORD_MESSAGES")
_record_file = open(_RECORD_PATH, "a") if _RECORD_PATH else None  # noqa: SIM115


def parse_message(data: dict[str, Any]) -> Message:
    """Parse message from CLI output into typed Message objects.

    Args:
        data: Raw message dictionary from CLI output

    Returns:
        Parsed Message object

    Raises:
        MessageParseError: If parsing fails or message type is unrecognized
    """
    if _record_file is not None:
        import json

        _record_file.write(json.dumps(data) + "\n")
        _record_file.flush()
    try:
        return message_adapter.validate_python(data)
    except ValidationError as e:
        msg_type = data.get("type", "<missing>") if isinstance(data, dict) else type(data).__name__
        raise MessageParseError(f"Failed to parse message (type={msg_type}): {e}", data) from e
