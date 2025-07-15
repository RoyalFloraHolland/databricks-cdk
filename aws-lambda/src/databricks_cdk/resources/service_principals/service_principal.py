import logging

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service.iam import ServicePrincipal
from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, get_account_client, get_workspace_client

logger = logging.getLogger(__name__)


class ServicePrincipalCreationError(Exception):
    pass


class ServicePrincipalNotFoundError(Exception):
    pass


class ServicePrincipalProperties(BaseModel):
    workspace_url: str
    service_principal: ServicePrincipal


class ServicePrincipalResponse(CnfResponse):
    name: str
    application_id: str


def create_or_update_service_principal(properties: ServicePrincipalProperties) -> ServicePrincipalResponse:
    """
    Create or update service principal on databricks. If service principal id is provided, it will update the existing service principal
    else it will create a new one.
    """
    workspace_client = get_workspace_client(properties.workspace_url)

    if properties.service_principal.id is None:
        # service principal doesn't exist yet so create new one
        return create_service_principal(properties.service_principal, workspace_client)

    # check if service principal exists
    get_service_principal(properties.service_principal.id, workspace_client)

    # update existing service principal
    return update_service_principal(properties.service_principal, workspace_client)


def get_service_principal(physical_resource_id: str, workspace_client: WorkspaceClient) -> ServicePrincipal:
    """Get service principal on databricks"""

    try:
        service_principal = workspace_client.service_principals.get(id=physical_resource_id)
    except NotFound:
        raise ServicePrincipalNotFoundError(f"Service principal with id {physical_resource_id} not found")

    return service_principal


def create_service_principal(
    service_principal: ServicePrincipal, workspace_client: WorkspaceClient
) -> ServicePrincipalResponse:
    """Create service principal on databricks"""

    created_service_principal = workspace_client.service_principals.create(
        active=service_principal.active,
        application_id=service_principal.application_id,
        display_name=service_principal.display_name,
        entitlements=service_principal.entitlements,
        external_id=service_principal.external_id,
        groups=service_principal.groups,
        id=service_principal.id,
        roles=service_principal.roles,
        schemas=service_principal.schemas,
    )

    if created_service_principal.id is None:
        raise ServicePrincipalCreationError("Service principal creation failed, there was no id found")

    return ServicePrincipalResponse(
        name=created_service_principal.display_name,
        physical_resource_id=created_service_principal.id,
        application_id=created_service_principal.application_id,
    )


def update_service_principal(
    service_principal: ServicePrincipal,
    workspace_client: WorkspaceClient,
) -> ServicePrincipalResponse:
    """Update service principal on databricks."""
    workspace_client.service_principals.update(
        id=service_principal.id,
        active=service_principal.active,
        application_id=service_principal.application_id,
        display_name=service_principal.display_name,
        entitlements=service_principal.entitlements,
        external_id=service_principal.external_id,
        groups=service_principal.groups,
        roles=service_principal.roles,
        schemas=service_principal.schemas,
    )

    return ServicePrincipalResponse(
        name=service_principal.display_name,
        physical_resource_id=service_principal.id,
        application_id=service_principal.application_id,
    )


def delete_service_principal(properties: ServicePrincipalProperties, physical_resource_id: str) -> CnfResponse:
    """Delete a service pricncipal on databricks. It will delete the service principal from workspace and account, because it's duplicated during creation."""
    workspace_client = get_workspace_client(properties.workspace_url)
    account_client = get_account_client()
    try:
        workspace_client.service_principals.delete(id=physical_resource_id)
        account_client.service_principals.delete(id=physical_resource_id)
    except NotFound:
        logger.warning("Service principal not found, never existed or already removed")

    return CnfResponse(physical_resource_id=physical_resource_id)
