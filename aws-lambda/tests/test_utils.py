from unittest.mock import MagicMock, patch

import pytest
from databricks.sdk.core import Config
from databricks.sdk.errors import NotFound
from requests.exceptions import HTTPError
from requests.models import Response

from databricks_cdk.utils import (
    ResourceNotReadyError,
    _do_request,
    delete_request,
    get_account_client,
    get_account_id,
    get_client_id,
    get_client_secret,
    get_request,
    get_workspace_client,
    is_not_found_error,
    patch_request,
    post_request,
    put_request,
    wait_until_found,
    wait_until_ready,
)


@patch("databricks_cdk.utils.get_authorization_headers")
@patch("databricks_cdk.utils.request")
def test__do_request_success(patched_requests, patched_get_authorization_headers):
    # Prepare
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    expected_response = {"result": "success"}
    mock_response.json.return_value = expected_response

    patched_requests.return_value = mock_response
    expected_url = "https://example.com"
    expected_body = {"key": "value"}
    expected_params = {"param": "value"}

    # Execute POST
    result = _do_request("POST", expected_url, body=expected_body, params=expected_params)

    # Verify
    patched_requests.assert_called_once_with(
        method="POST",
        url=expected_url,
        json=expected_body,
        params=expected_params,
        headers=patched_get_authorization_headers.return_value,
    )
    mock_response.raise_for_status.assert_called_once()
    assert result == expected_response


@patch("databricks_cdk.utils.get_authentication_config")
@patch("databricks_cdk.utils.request")
def test__do_request_http_error_retry(patched_requests, patched_get_authentication_config):
    # Prepare
    _do_request.retry.sleep = MagicMock()  # remove sleep in between
    expected_url = "https://example.com"
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 429
    mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)

    patched_requests.return_value = mock_response
    # Execute
    with pytest.raises(HTTPError):
        _do_request("POST", expected_url)

    # Verify
    assert patched_requests.call_count == 5  # Retried 5 times


@patch("databricks_cdk.utils.get_authorization_headers")
@patch("databricks_cdk.utils.request")
def test__do_request_http_error_no_retry(patched_requests, patched_get_authorization_headers):
    # Prepare
    expected_url = "https://example.com"
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)

    patched_requests.return_value = mock_response
    # Execute
    with pytest.raises(HTTPError):
        _do_request("POST", expected_url)

    # Verify
    assert patched_requests.call_count == 1  # Not retried


@patch("databricks_cdk.utils.get_authorization_headers")
def test__do_request_unsupported_method(patched_get_authorization_headers):
    # Prepare
    expected_url = "https://example.com"

    # Execute and Verify
    with pytest.raises(HTTPError):
        _do_request("INVALID_METHOD", expected_url)


@patch("databricks_cdk.utils._do_request")
def test_post_request(patched__do_request):
    expected_url = "test.com"
    expected_body = {"test", "value"}
    post_request(expected_url, expected_body)

    patched__do_request.assert_called_once_with(method="POST", url=expected_url, body=expected_body, params=None)


@patch("databricks_cdk.utils._do_request")
def test_put_request(patched__do_request):
    expected_url = "test.com"
    expected_body = {"test", "value"}
    put_request(expected_url, expected_body)

    patched__do_request.assert_called_once_with(method="PUT", url=expected_url, body=expected_body, params=None)


@patch("databricks_cdk.utils._do_request")
def test_patch_request(patched__do_request):
    expected_url = "test.com"
    expected_body = {"test", "value"}
    patch_request(expected_url, expected_body)

    patched__do_request.assert_called_once_with(method="PATCH", url=expected_url, body=expected_body, params=None)


@patch("databricks_cdk.utils._do_request")
def test_get_request(patched__do_request):
    expected_url = "test.com"
    expected_body = {"test", "value"}
    get_request(expected_url, expected_body)

    patched__do_request.assert_called_once_with(method="GET", url=expected_url, body=expected_body, params=None)


@patch("databricks_cdk.utils._do_request")
def test_delete_request(patched__do_request):
    expected_url = "test.com"
    expected_body = {"test", "value"}
    delete_request(expected_url, expected_body)

    patched__do_request.assert_called_once_with(method="DELETE", url=expected_url, body=expected_body, params=None)


@patch("databricks_cdk.utils.get_param")
def test_get_client_secret(patched_get_param):
    from databricks_cdk.utils import CLIENT_SECRET_PARAM

    result = get_client_secret()

    assert result == patched_get_param.return_value
    patched_get_param.assert_called_once_with(CLIENT_SECRET_PARAM, required=True)


@patch("databricks_cdk.utils.get_param")
def test_get_client_id(patched_get_param):
    from databricks_cdk.utils import CLIENT_ID_PARAM

    result = get_client_id()

    assert result == patched_get_param.return_value
    patched_get_param.assert_called_once_with(CLIENT_ID_PARAM, required=True)


@patch("databricks_cdk.utils.get_param")
def test_get_account_id(patched_get_param):
    from databricks_cdk.utils import ACCOUNT_PARAM

    result = get_account_id()

    assert result == patched_get_param.return_value
    patched_get_param.assert_called_once_with(ACCOUNT_PARAM, required=True)


@patch("databricks_cdk.utils.get_client_secret")
@patch("databricks_cdk.utils.get_client_id")
@patch("databricks_cdk.utils.WorkspaceClient")
def test_get_workspace_client(patched_workspace_client, patched_get_client_id, patched_get_client_secret):
    result = get_workspace_client("https://example.com")

    assert result == patched_workspace_client.return_value
    patched_workspace_client.assert_called_once_with(
        client_id=patched_get_client_id.return_value,
        client_secret=patched_get_client_secret.return_value,
        host="https://example.com",
    )


@patch("databricks_cdk.utils.WorkspaceClient")
def test_get_workspace_client_with_config(
    patched_workspace_client,
):
    config = MagicMock(spec=Config)
    result = get_workspace_client("https://example.com", config=config)

    assert result == patched_workspace_client.return_value
    patched_workspace_client.assert_called_once_with(config=config)


@patch("databricks_cdk.utils.get_client_secret")
@patch("databricks_cdk.utils.get_client_id")
@patch("databricks_cdk.utils.get_account_id")
@patch("databricks_cdk.utils.AccountClient")
def test_get_account_client(
    patched_account_client,
    patched_get_account_id,
    patched_get_client_id,
    patched_get_client_secret,
):
    result = get_account_client()

    assert result == patched_account_client.return_value
    patched_account_client.assert_called_once_with(
        client_id=patched_get_client_id.return_value,
        client_secret=patched_get_client_secret.return_value,
        host="https://accounts.cloud.databricks.com",
        account_id=patched_get_account_id.return_value,
    )



def test_wait_until_ready_returns_when_ready(patched_sleep):
    check_fn = MagicMock(side_effect=[ResourceNotReadyError("pending"), ResourceNotReadyError("pending"), "ready"])

    assert wait_until_ready(check_fn, "test resource") == "ready"

    assert check_fn.call_count == 3
    # exponential backoff between the checks
    assert [c.args[0] for c in patched_sleep.call_args_list] == [2, 3]


def test_wait_until_ready_no_sleep_when_ready_immediately(patched_sleep):
    assert wait_until_ready(lambda: "ready", "test resource") == "ready"

    patched_sleep.assert_not_called()


def test_wait_until_ready_backoff_capped(patched_sleep):
    check_fn = MagicMock(side_effect=[ResourceNotReadyError("pending")] * 10 + ["ready"])

    wait_until_ready(check_fn, "test resource", timeout_seconds=1000, max_delay=10)

    assert max(c.args[0] for c in patched_sleep.call_args_list) == 10


def test_wait_until_ready_timeout(patched_sleep):
    check_fn = MagicMock(side_effect=ResourceNotReadyError("pending"))

    with pytest.raises(TimeoutError, match="test resource was not ready within 60s: pending"):
        wait_until_ready(check_fn, "test resource", timeout_seconds=60)

    # never sleeps past the deadline
    assert sum(c.args[0] for c in patched_sleep.call_args_list) == 60


def test_wait_until_ready_other_errors_are_raised(patched_sleep):
    check_fn = MagicMock(side_effect=ValueError("broken"))

    with pytest.raises(ValueError, match="broken"):
        wait_until_ready(check_fn, "test resource")

    assert check_fn.call_count == 1
    patched_sleep.assert_not_called()


def test_wait_until_found_timeout():
    get_fn = MagicMock(return_value=None)

    with pytest.raises(TimeoutError, match="test resource was not ready within 30s: not found"):
        wait_until_found(get_fn, "test resource", timeout_seconds=30)
