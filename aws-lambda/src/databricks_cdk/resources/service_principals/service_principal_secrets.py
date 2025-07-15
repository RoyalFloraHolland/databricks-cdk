import json
import logging
from typing import Optional

import boto3
from databricks.sdk import AccountClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service.iam import ServicePrincipal
from databricks.sdk.service.oauth2 import SecretInfo
from pydantic import BaseModel

from databricks_cdk.resources.service_principals.service_principal import get_service_principal
from databricks_cdk.utils import CnfResponse, get_account_client

SECRETS_MANAGER_RESOURCE_PREFIX = "/databricks/service_principal/secrets"

logger = logging.getLogger(__name__)


class ServicePrincipalSecretsCreationError(Exception):
    pass


class ServicePrincipalSecretsProperties(BaseModel):
    service_principal_id: int


class ServicePrincipalSecretsResponse(CnfResponse):
    secrets_manager_arn: str
    secrets_manager_name: str


def create_or_update_service_principal_secrets(
    properties: ServicePrincipalSecretsProperties, physical_resource_id: Optional[str] = None
) -> ServicePrincipalSecretsResponse:
    """
    Create or update service principal secrets on databricks.
    If service principal secrets already exist, it will return the existing service principal secrets.
    If service principal secrets doesn't exist, it will create a new one.
    """
    account_client = get_account_client()

    if physical_resource_id:
        return get_existing_service_principal_secrets_response(properties, physical_resource_id, account_client)

    return create_service_principal_secrets(properties, account_client)


def get_service_principal_secrets(
    service_principal_id: int, physical_resource_id: str, account_client: AccountClient
) -> SecretInfo:
    """Get service principal secrets on databricks based on physical resource id and service principal id."""
    existing_service_principal_secrets = account_client.service_principal_secrets.list(
        service_principal_id=service_principal_id
    )

    for secret_info in existing_service_principal_secrets:
        if secret_info is not None and secret_info.id == physical_resource_id:
            return secret_info
    else:
        raise NotFound(f"Service principal secrets with id {physical_resource_id} not found")


def create_service_principal_secrets(
    properties: ServicePrincipalSecretsProperties, account_client: AccountClient
) -> ServicePrincipalSecretsResponse:
    """
    Create service principal secrets on databricks.
    It will create a new service principal secrets and store it in secrets manager.
    """
    service_principal = get_service_principal(properties.service_principal_id, account_client)
    created_service_principal_secrets = account_client.service_principal_secrets.create(
        service_principal_id=properties.service_principal_id
    )

    if created_service_principal_secrets.id is None:
        raise ServicePrincipalSecretsCreationError("Failed to create service principal secrets")

    secret_name = _construct_secret_name(service_principal, created_service_principal_secrets.id)
    secrets_manager_resource = add_to_secrets_manager(
        secret_name=secret_name,
        client_id=service_principal.application_id,
        client_secret=created_service_principal_secrets.secret,
    )
    return ServicePrincipalSecretsResponse(
        physical_resource_id=created_service_principal_secrets.id,
        secrets_manager_arn=secrets_manager_resource["ARN"],
        secrets_manager_name=secrets_manager_resource["Name"],
    )


def get_existing_service_principal_secrets_response(
    properties: ServicePrincipalSecretsProperties,
    physical_resource_id: str,
    account_client: AccountClient,
) -> ServicePrincipalSecretsResponse:
    """
    Get existing service principal secrets response.
    It will fetch the existing service principal secrets and secrets manager resource.
    """
    service_principal = get_service_principal(properties.service_principal_id, account_client)
    existing_service_principal_secrets = get_service_principal_secrets(
        service_principal_id=properties.service_principal_id,
        physical_resource_id=physical_resource_id,
        account_client=account_client,
    )
    secret_name = _construct_secret_name(service_principal, existing_service_principal_secrets.id)
    secrets_manager_resource = get_from_secrets_manager(secret_name)
    return ServicePrincipalSecretsResponse(
        physical_resource_id=existing_service_principal_secrets.id,
        secrets_manager_arn=secrets_manager_resource["ARN"],
        secrets_manager_name=secrets_manager_resource["Name"],
    )


def delete_service_principal_secrets(
    properties: ServicePrincipalSecretsProperties, physical_resource_id: str
) -> CnfResponse:
    """Delete service pricncipal secrets on databricks. It will delete the service principal secrets from databricks and secrets manager."""
    account_client = get_account_client()

    try:
        account_client.service_principal_secrets.delete(
            service_principal_id=properties.service_principal_id, secret_id=physical_resource_id
        )
    except NotFound:
        logger.warning("Service principal secrets with id %s not found", physical_resource_id)

    service_principal = get_service_principal(properties.service_principal_id, account_client)
    secret_name = _construct_secret_name(service_principal, physical_resource_id)
    delete_from_secrets_manager(secret_name)
    return CnfResponse(physical_resource_id=physical_resource_id)


def get_from_secrets_manager(secret_name: str) -> dict:
    """
    Get information from secrets manager at /{{SECRETS_MANAGER_RESOURCE_PREFIX}}/{{secret_name}}.
    This will only retrieve general information about the secret, not the actual secret value.
    """
    client = boto3.client("secretsmanager")
    return client.describe_secret(SecretId=secret_name)


def add_to_secrets_manager(secret_name: str, client_id: str, client_secret: str) -> dict:
    """Adds credentials to secrets manager at /{{SECRETS_MANAGER_RESOURCE_PREFIX}}/{{secret_name}}"""
    client = boto3.client("secretsmanager")
    secret_string = {"client_id": client_id, "client_secret": client_secret}
    return client.create_secret(Name=secret_name, SecretString=json.dumps(secret_string))


def delete_from_secrets_manager(secret_name: str) -> None:
    """Removes credentials from secrets manager at /{{SECRETS_MANAGER_RESOURCE_PREFIX}}/{{secret_name}}"""
    client = boto3.client("secretsmanager")
    try:
        client.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)
    except client.exceptions.ResourceNotFoundException:
        logger.warning("Secrets are not found in secrets manager")


def _construct_secret_name(service_principal: ServicePrincipal, secrets_id: str) -> str:
    return f"{SECRETS_MANAGER_RESOURCE_PREFIX}/{service_principal.display_name}/{service_principal.id}/{secrets_id}"
