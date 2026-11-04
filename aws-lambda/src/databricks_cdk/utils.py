import logging
import os
from collections.abc import Callable
from functools import lru_cache
from time import monotonic, sleep
from typing import Any, TypeVar

import boto3
from databricks.sdk import AccountClient, WorkspaceClient
from databricks.sdk.core import Config
from databricks.sdk.errors import NotFound
from pydantic import BaseModel
from requests import request
from requests.exceptions import HTTPError
from tenacity import retry, retry_if_exception, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class UnsupportedAuthMethodError(Exception):
    pass


ACCOUNT_PARAM = os.environ.get("ACCOUNT_PARAM", "/databricks/account-id")
CLIENT_SECRET_PARAM = os.environ.get("CLIENT_SECRET_PARAM", "/databricks/deploy/client-secret")

# Make sure password based authentication is not used anymore after 10th of July 2024
if CLIENT_SECRET_PARAM is None:
    raise UnsupportedAuthMethodError(
        "Password based authentication is not supported from 10th of July 2024.",
        "Please set client_id and client_secret of a service principal instead.",
        "Service principal can be created in account settings in Databricks."
        "Needs account admin and admin permissions on workspace.",
    )

CLIENT_ID_PARAM = os.environ.get("CLIENT_ID_PARAM", "/databricks/deploy/client-id")
ACCOUNTS_BASE_URL = os.environ.get("BASE_URL", "https://accounts.cloud.databricks.com")


def get_param(name: str, required: bool = False):
    ssm = boto3.client("ssm")
    response = ssm.get_parameter(
        Name=name,
        WithDecryption=True,
    )
    result = response.get("Parameter", {}).get("Value")
    if result is None and required:
        raise AttributeError(f"Parameter '{name}' not found")
    return result


@lru_cache(maxsize=1)
def get_authentication_config() -> Config:
    """
    This config can be used to authenticate with databricks using
    requests library. Not needed when using WorkspaceClient or AccountClient.
    Config is cached to avoid multiple calls to get_param
    """
    return Config(
        host=ACCOUNTS_BASE_URL,
        client_id=get_client_id(),
        client_secret=get_client_secret(),
        account_id=get_account_id(),
    )


def get_authorization_headers() -> dict[str, str]:
    """Get authorization headers"""
    return get_authentication_config().authenticate()


class CnfResponse(BaseModel):  # TODO: rename to CfnResponse
    physical_resource_id: str


def get_account_id() -> str:
    """Get databricks account id from param store"""
    return get_param(ACCOUNT_PARAM, required=True)


def get_client_secret() -> str:
    return get_param(CLIENT_SECRET_PARAM, required=True)


def get_client_id() -> str:
    return get_param(CLIENT_ID_PARAM, required=True)


@retry(
    retry=retry_if_exception_type(HTTPError) & retry_if_exception(lambda ex: ex.response.status_code == 429),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def _do_request(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generic method to do any type of request

    :param method: Request method to use when doing a request
    :param url: Url to which to make the request
    :param body: Optional body to send along with the request, defaults to None
    :param params: Optional params to send along with the request, defaults to None
    :param auth: Auth to use which is injected when not explicitely overriden, defaults to get_auth()
    :raises ValueError: If provided method is not supported
    :return: Response data
    """
    resp = request(
        method=method,
        url=url,
        json=body,
        params=params,
        headers=get_authorization_headers(),
    )

    # If the response was successful, no Exception will be raised
    if resp.status_code >= 400:
        logger.warning(resp.text)
    resp.raise_for_status()

    return resp.json()


def post_request(
    url: str,
    body: dict[str, Any],
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generic method to do post requests"""
    return _do_request(method="POST", url=url, body=body, params=params)


def put_request(
    url: str,
    body: dict[str, Any],
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generic method to do put requests"""
    return _do_request(method="PUT", url=url, body=body, params=params)


def patch_request(url: str, body: dict, params: dict | None = None) -> dict:
    """Generic method to do patch requests"""

    return _do_request(method="PATCH", url=url, body=body, params=params)


def get_request(
    url: str,
    body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generic method to do get requests"""
    return _do_request(method="GET", url=url, body=body, params=params)


def delete_request(
    url: str,
    body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generic method to do delete requests"""
    return _do_request(method="DELETE", url=url, body=body, params=params)


def get_workspace_client(workspace_url: str, config: Config | None = None) -> WorkspaceClient:
    """Get Databricks WorkspaceClient instance, either from config or from username/password
    :param workspace_url: Workspace url to connect to
    :param config: Optional config to use, when provided overwrites workspace_url provided,
        defaults to None
    """
    if config:
        return WorkspaceClient(config=config)

    return WorkspaceClient(client_id=get_client_id(), client_secret=get_client_secret(), host=workspace_url)


def get_account_client(
    config: Config | None = None, host: str = "https://accounts.cloud.databricks.com"
) -> AccountClient:
    """Get Databricks AccountClient instance, either from config defaulting to ssm params
    :param host: Url to account url to, defaults to 'https://accounts.cloud.databricks.com'
    :param config: Optional config to use, when provided overwrites workspace_url provided,
        defaults to None
    """
    if config:
        return AccountClient(config=config)

    return AccountClient(
        client_id=get_client_id(),
        client_secret=get_client_secret(),
        host=host,
        account_id=get_account_id(),
    )


T = TypeVar("T")

# The lambda runs timeout is set to 900s, every wait has to fit within a single invoke call
DEFAULT_WAIT_TIMEOUT_SECONDS = 120
WORKSPACE_WAIT_TIMEOUT_SECONDS = 840 # workspaces take longer to deploy, so increase timeout window


class ResourceNotReadyError(Exception):
    """Raised by a readiness check when a resource is not visible or usable yet"""


def is_not_found_error(error: Exception) -> bool:
    """Whether an error from the Databricks REST api or sdk means the requested resource does not exist"""
    if isinstance(error, NotFound):
        return True
    if isinstance(error, HTTPError) and error.response is not None:
        if error.response.status_code == 404:
            return True
        return "RESOURCE_DOES_NOT_EXIST" in error.response.text
    return False


def wait_until_ready[T](
    check_fn: Callable[[], T],
    description: str,
    timeout_seconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
    initial_delay: float = 2,
    max_delay: float = 30,
) -> T:
    """
    Call check_fn until it stops raising ResourceNotReadyError, with exponential backoff between attempts.

    Databricks resources can be invisible or unusable for a while after their create call returned. CloudFormation
    starts creating dependent resources as soon as the lambda responds, so waiting here prevents those from failing.

    :param check_fn: Returns the resource when it's ready, raises ResourceNotReadyError when it isn't yet
    :param description: Name of the resource, used in logs and the timeout error
    :param timeout_seconds: Maximum time to wait
    :param initial_delay: Seconds to wait after the first failed check
    :param max_delay: Upper bound for the time between two checks
    :raises TimeoutError: If the resource is still not ready after timeout_seconds
    :return: Result of check_fn
    """
    deadline = monotonic() + timeout_seconds
    delay = initial_delay
    while True:
        try:
            return check_fn()
        except ResourceNotReadyError as e:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise TimeoutError(f"{description} was not ready within {timeout_seconds}s: {e}") from e
            sleep_seconds = min(delay, remaining)
            logger.info(f"{description} is not ready yet ({e}), checking again in {sleep_seconds:.0f}s")
            sleep(sleep_seconds)
            delay = min(delay * 1.5, max_delay)


def wait_until_found[T](
    get_fn: Callable[[], T | None],
    description: str,
    timeout_seconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS,
) -> T:
    """
    Wait until get_fn returns the resource, treating both None and a not found error as not ready yet.

    :param get_fn: Fetches the resource from Databricks
    :param description: Name of the resource, used in logs and the timeout error
    :param timeout_seconds: Maximum time to wait
    :raises TimeoutError: If the resource is still not found after timeout_seconds
    :return: Result of get_fn
    """

    def check() -> T:
        try:
            result = get_fn()
        except Exception as e:
            if is_not_found_error(e):
                raise ResourceNotReadyError("not found") from e
            raise
        if result is None:
            raise ResourceNotReadyError("not found")
        return result

    return wait_until_ready(check, description, timeout_seconds=timeout_seconds)
