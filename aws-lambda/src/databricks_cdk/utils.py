import logging
import os
from functools import lru_cache
from typing import Any

import boto3
from databricks.sdk import AccountClient, WorkspaceClient
from databricks.sdk.core import Config
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
