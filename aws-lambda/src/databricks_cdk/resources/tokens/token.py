import json
import logging
from datetime import datetime
from typing import Any

import boto3
from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, get_request, post_request

logger = logging.getLogger(__name__)


class TokenInfo(BaseModel):
    token_id: str
    creation_time: int
    expiry_time: int
    comment: str


class TokenList(BaseModel):
    token_infos: list[TokenInfo]


class TokenProperties(BaseModel):
    action: str = "token"
    token_name: str
    workspace_url: str
    lifetime_seconds: int | None
    comment: str | None


class TokenCreateReponse(CnfResponse):
    token_secrets_arn = str
    creation_time: int
    expiry_time: int
    comment: str


def get_existing_tokens(token_url: str) -> list[TokenInfo]:
    """Get a list of existing tokens"""
    response = get_request(f"{token_url}/list")

    if response:
        return TokenList.parse_obj(response).token_infos

    return []


def get_token_url(workspace_url: str):
    """Getting url for token requests"""
    return f"{workspace_url}/api/2.0/token"


def _delete_token(token_url: str, token_id: str):
    post_request(url=f"{token_url}/delete", body={"token_id": token_id})


def _create_token(token_url: str, comment: str | None, lifetime_seconds: int | None) -> dict[str, Any]:
    return post_request(f"{token_url}/create", body={"comment": comment, "lifetime_seconds": lifetime_seconds})


def add_token_to_secrets_manager(token_name: str, token_id: str, token_value: str) -> str:
    """Adds token to secrets manager at /databricks/token/{{token_id}}"""
    client = boto3.client("secretsmanager")
    secret_name = f"/databricks/token/{token_name}"
    secret_string = {"token_id": token_id, "token_value": token_value}
    return client.create_secret(Name=secret_name, SecretString=json.dumps(secret_string))["ARN"]


def delete_token_from_secrets_manager(token_name: str) -> dict:
    """Removes token from secrets manager"""
    client = boto3.client("secretsmanager")
    secret_name = f"/databricks/token/{token_name}"
    return client.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)


def token_exists_in_secrets_manager(token_name: str) -> bool:
    """Checks whether token already exists in secrets manager"""
    client = boto3.client("secretsmanager")
    secret_name = f"/databricks/token/{token_name}"
    return len(client.list_secrets(Filters=[{"Key": "name", "Values": [secret_name]}]).get("SecretList")) > 0


def update_token_in_secrets_manager(token_name: str, token_id: str, token_value: str) -> str:
    """Updates existing token in secrets manager"""
    client = boto3.client("secretsmanager")
    secret_name = f"/databricks/token/{token_name}"
    secret_string = {"token_id": token_id, "token_value": token_value}
    return client.update_secret(SecretId=secret_name, SecretString=json.dumps(secret_string))["ARN"]


def create_or_update_token(properties: TokenProperties, physical_resource_id: str | None = None) -> CnfResponse:
    """
    Creates or updates a new token.

    :param properties: Properties to use when creating token
    :param physical_resource_id: Physical resource id of previous token object
    :return: Cloudformation response
    """
    token_name = properties.token_name
    url = get_token_url(properties.workspace_url)

    update_token = False
    existing_token = None
    new_token = None
    token_id = None
    token_value = None
    token_secrets_arn = None

    for t in get_existing_tokens(url):
        if physical_resource_id == t.token_id:
            logger.info("Token already exists")
            existing_token = t

    if existing_token is not None:
        expiry_time = datetime.fromtimestamp(existing_token.expiry_time)
        # If expiry_time = -1 then the token doesn't expire
        update_token = False if expiry_time == -1 else expiry_time > datetime.now()

        if existing_token.comment != properties.comment:
            update_token = True

        token_id = existing_token.token_id

    if update_token or existing_token is None:
        logger.info("Creating new token")
        new_token = _create_token(url, properties.comment, properties.lifetime_seconds)
        # delete old token if it exists
        if existing_token:
            _delete_token(token_url=url, token_id=token_id)

        token_id = new_token["token_info"]["token_id"]
        token_value = new_token["token_value"]

    if new_token and token_exists_in_secrets_manager(properties.token_name):
        logger.info("Updating token in Secrets Manager")
        token_secrets_arn = update_token_in_secrets_manager(
            token_name=token_name, token_id=token_id, token_value=token_value
        )
    elif new_token:
        logger.info("Adding token to Secrets Manager")
        token_secrets_arn = add_token_to_secrets_manager(
            token_name=token_name, token_id=token_id, token_value=token_value
        )

    return TokenCreateReponse(
        physical_resource_id=token_id,
        token_secrets_arn=token_secrets_arn,
        creation_time=new_token["token_info"]["creation_time"] if new_token else existing_token.creation_time,
        expiry_time=new_token["token_info"]["expiry_time"] if new_token else existing_token.expiry_time,
        comment=new_token["token_info"]["comment"] if new_token else existing_token.comment,
    )


def delete_token(properties: TokenProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes token from databricks and secrets manager"""

    url = get_token_url(properties.workspace_url)

    if physical_resource_id in [t.token_id for t in get_existing_tokens(url)]:
        _delete_token(token_url=url, token_id=physical_resource_id)
        delete_token_from_secrets_manager(properties.token_name)

    return CnfResponse(physical_resource_id=physical_resource_id)
