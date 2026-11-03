from unittest.mock import MagicMock, patch

import cfnresponse

from databricks_cdk.resources.handler import handler
from databricks_cdk.utils import CnfResponse


def _event(request_type: str, physical_resource_id: str | None = None) -> dict:
    event = {
        "RequestType": request_type,
        "ResponseURL": "https://example.com/response",
        "ResourceProperties": {"action": "job", "workspace_url": "https://test.cloud.databricks.com"},
    }
    if physical_resource_id is not None:
        event["PhysicalResourceId"] = physical_resource_id
    return event


@patch("databricks_cdk.resources.handler.cfnresponse.send")
@patch("databricks_cdk.resources.handler.process_event")
def test_handler_failed_update_keeps_physical_resource_id(patched_process_event, patched_send):
    patched_process_event.side_effect = RuntimeError("429 Too Many Requests")
    event = _event("Update", physical_resource_id="123456789")
    context = MagicMock(log_stream_name="2024/01/01/[$LATEST]0123456789abcdef")

    handler(event, context)

    patched_send.assert_called_once()
    assert patched_send.call_args.args[2] == cfnresponse.FAILED
    assert patched_send.call_args.kwargs["physicalResourceId"] == "123456789"
    assert "429 Too Many Requests" in patched_send.call_args.kwargs["reason"]


@patch("databricks_cdk.resources.handler.cfnresponse.send")
@patch("databricks_cdk.resources.handler.process_event")
def test_handler_failed_create_has_no_physical_resource_id(patched_process_event, patched_send):
    patched_process_event.side_effect = RuntimeError("boom")

    handler(_event("Create"), MagicMock())

    assert patched_send.call_args.args[2] == cfnresponse.FAILED
    assert patched_send.call_args.kwargs["physicalResourceId"] is None


@patch("databricks_cdk.resources.handler.cfnresponse.send")
@patch("databricks_cdk.resources.handler.process_event")
def test_handler_success_uses_new_physical_resource_id(patched_process_event, patched_send):
    patched_process_event.return_value = CnfResponse(physical_resource_id="999")

    handler(_event("Update", physical_resource_id="123"), MagicMock())

    assert patched_send.call_args.args[2] == cfnresponse.SUCCESS
    assert patched_send.call_args.kwargs["physicalResourceId"] == "999"
