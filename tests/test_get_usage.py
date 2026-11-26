"""The get_usage control response (real response shape, trimmed)."""

from typing import Any

from clawd_code_sdk.models import SDKControlGetUsageResponse


WINDOW_EXTRAS = {"limit_dollars": None, "used_dollars": None, "locked_reason": None}

RESPONSE: dict[str, Any] = {
    "session": {
        "total_cost_usd": 0,
        "total_api_duration_ms": 0,
        "total_duration_ms": 475,
        "total_lines_added": 0,
        "total_lines_removed": 0,
        "model_usage": {},
    },
    "subscription_type": "pro",
    "rate_limits_available": True,
    "rate_limits": {
        "five_hour": {
            "utilization": 66,
            "resets_at": "2026-11-20T09:39:59.762577+00:00",
            **WINDOW_EXTRAS,
        },
        "seven_day": {
            "utilization": 35,
            "resets_at": "2026-11-22T12:59:59.762597+00:00",
            **WINDOW_EXTRAS,
        },
        "seven_day_opus": None,
        "extra_usage": {
            "is_enabled": False,
            "monthly_limit": None,
            "used_credits": None,
            "utilization": None,
            "currency": None,
            "spend_limit_reached": False,
        },
        "limits": [
            {
                "kind": "session",
                "group": "session",
                "percent": 66,
                "resets_at": "2026-11-20T09:39:59.762577+00:00",
                "severity": "normal",
                "is_active": True,
                "scope": None,
            },
            {
                "kind": "weekly_scoped",
                "group": "weekly",
                "percent": 0,
                "resets_at": "2026-11-22T13:00:00+00:00",
                "severity": "normal",
                "is_active": False,
                "scope": {"model": {"id": None, "display_name": "Fable"}, "surface": None},
            },
        ],
        "model_scoped": [
            {"display_name": "Fable", "utilization": 0, "resets_at": "2026-11-22T13:00:00+00:00"}
        ],
        # Undocumented, experimental fields are ignored (spend is modelled)
        "pace": {"status": "on_track"},
        "spend": {
            "used": {"amount_minor": 1250, "currency": "USD", "exponent": 2},
            "limit": {"amount_minor": 5000, "currency": "USD", "exponent": 2},
            "percent": 25,
            "severity": "normal",
            "enabled": True,
            "disclaimer": "Usage credits cover you when you hit your plan limits.",
        },
    },
    "behaviors": None,
}


def test_parses_real_response() -> None:
    usage = SDKControlGetUsageResponse.model_validate(RESPONSE)
    assert usage.subscription_type == "pro"
    limits = usage.rate_limits
    assert limits is not None
    assert limits.five_hour is not None
    assert limits.five_hour.utilization == 66
    assert limits.seven_day_opus is None
    assert limits.model_scoped is not None
    assert limits.model_scoped[0].display_name == "Fable"
    assert limits.limits is not None
    assert [row.kind for row in limits.limits] == ["session", "weekly_scoped"]
    assert limits.spend is not None
    assert limits.spend.enabled
    assert limits.spend.percent == 25
    assert limits.spend.used is not None
    assert limits.spend.used.amount == 12.5


def test_without_plan_limits() -> None:
    data = {**RESPONSE, "subscription_type": None, "rate_limits_available": False}
    usage = SDKControlGetUsageResponse.model_validate({**data, "rate_limits": None})
    assert usage.rate_limits is None
