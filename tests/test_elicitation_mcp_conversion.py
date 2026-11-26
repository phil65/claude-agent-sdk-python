"""SDKControlElicitationRequest <-> mcp elicitation params on mcp 1.x and 2.x."""

from clawd_code_sdk.models import SDKControlElicitationRequest


def test_form_roundtrip() -> None:
    request = SDKControlElicitationRequest(
        mcp_server_name="srv",
        message="Pick one",
        mode="form",
        requested_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        title="Choose",
        display_name="Server",
        description="Needs input",
    )
    params = request.to_mcp()
    wire = params.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert wire["requestedSchema"]["properties"] == {"x": {"type": "string"}}
    assert wire["_meta"]["anthropic/permissionDisplay"]["displayName"] == "Server"
    back = SDKControlElicitationRequest.from_mcp(params, "srv")
    assert back.mode == "form"
    assert back.requested_schema == request.requested_schema
    assert (back.title, back.display_name, back.description) == ("Choose", "Server", "Needs input")


def test_url_roundtrip() -> None:
    request = SDKControlElicitationRequest(
        mcp_server_name="srv",
        message="Log in",
        mode="url",
        url="https://example.com/auth",
        elicitation_id="e1",
    )
    params = request.to_mcp()
    back = SDKControlElicitationRequest.from_mcp(params, "srv")
    assert back.mode == "url"
    assert back.url == "https://example.com/auth"
    assert back.elicitation_id == "e1"
    assert back.title is None
