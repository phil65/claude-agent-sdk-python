"""Tests for message parser — error wrapping."""

from __future__ import annotations

import pytest

from clawd_code_sdk._errors import MessageParseError
from clawd_code_sdk.client import parse_message


class TestErrorWrapping:
    """parse_message wraps errors as MessageParseError with original data."""

    def test_non_dict_input(self):
        with pytest.raises(MessageParseError, match="Failed to parse message"):
            parse_message("not a dict")  # type: ignore[arg-type]

    def test_missing_type_field(self):
        with pytest.raises(MessageParseError, match="Failed to parse message"):
            parse_message({"message": {"content": []}})

    def test_unknown_message_type(self):
        with pytest.raises(MessageParseError, match="Failed to parse message"):
            parse_message({"type": "banana"})

    def test_error_preserves_original_data(self):
        data = {"type": "banana", "extra": 42}
        with pytest.raises(MessageParseError) as exc_info:
            parse_message(data)
        assert exc_info.value.data == data

    def test_result_missing_required_fields(self):
        with pytest.raises(MessageParseError, match="Failed to parse message"):
            parse_message({"type": "result", "subtype": "success"})
