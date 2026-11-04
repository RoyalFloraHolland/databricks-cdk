import logging

from pydantic import BaseModel
from requests.exceptions import HTTPError

from databricks_cdk.utils import (
    ACCOUNTS_BASE_URL,
    WORKSPACE_WAIT_TIMEOUT_SECONDS,
    CnfResponse,
    ResourceNotReadyError,
    delete_request,
    get_account_id,
    get_request,
    is_not_found_error,
    patch_request,
    post_request,
    wait_until_ready,
)

logger = logging.getLogger(__name__)


class WorkspaceProperties(BaseModel):
    action: str = "workspaces"
    workspace_name: str
    deployment_name: str | None = None
    aws_region: str
    credentials_id: str
    storage_configuration_id: str
    network_id: str | None = None
    managed_services_customer_managed_key_id: str | None = None
    pricing_tier: str | None = None
    storage_customer_managed_key_id: str | None = None


class WorkspaceResponse(CnfResponse):
    workspace_name: str
    workspace_id: str
    workspace_url: str
    creation_time: int


def get_workspaces_url():
    """Getting workspace api url"""
    account_id = get_account_id()

    # api-endpoint
    return f"{ACCOUNTS_BASE_URL}/api/2.0/accounts/{account_id}/workspaces"


def get_workspace_by_id(workspace_id: str) -> dict | None:
    """Getting workspace by id, returns None if it does not exist"""
    url = get_workspaces_url()
    try:
        return get_request(url=f"{url}/{workspace_id}")
    except HTTPError as e:
        if is_not_found_error(e):
            return None
        raise


def get_workspace_by_name(workspace_name: str) -> dict | None:
    """Getting workspace by name"""
    url = get_workspaces_url()
    get_response = get_request(url=url)
    current = None
    for r in get_response:
        if r.get("workspace_name") == workspace_name:
            current = r
    return current


def create_or_update_workspaces(properties: WorkspaceProperties) -> WorkspaceResponse:
    """Create or updates a workspace"""
    url = get_workspaces_url()

    current = get_workspace_by_name(properties.workspace_name)
    if current is None:
        logger.info("Workspace not found yet, creating now")
        # Json data
        body = properties.dict()
        del body["action"]
        response = post_request(url, body=body)
        workspace_id = response["workspace_id"]
        wait_on_provisioning(workspace_id)
        deployment_name = response["deployment_name"]
        return WorkspaceResponse(
            physical_resource_id=workspace_id,
            workspace_name=properties.workspace_name,
            workspace_id=workspace_id,
            workspace_url=f"https://{deployment_name}.cloud.databricks.com",
            creation_time=response["creation_time"],
        )
    else:
        workspace_id = current["workspace_id"]
        current_deployment_name = current.get("deployment_name")
        if properties.deployment_name is not None and current_deployment_name != properties.deployment_name:
            raise AttributeError("deployment_name can't be changed after deployment")
        current_pricing_tier = current.get("pricing_tier")
        if properties.pricing_tier is not None and current_pricing_tier != properties.pricing_tier:
            raise AttributeError("pricing_tier can't be changed after deployment")
        if (
            properties.aws_region != current["aws_region"]
            or properties.credentials_id != current["credentials_id"]
            or properties.storage_configuration_id != current["storage_configuration_id"]
            or properties.network_id != current.get("network_id")
            or properties.managed_services_customer_managed_key_id
            != current.get("managed_services_customer_managed_key_id")
            or properties.storage_customer_managed_key_id != current.get("storage_customer_managed_key_id")
        ):
            logger.info("Workspace found already, patching now")
            patch_url = f"{url}/{workspace_id}"
            patch_body = {
                "aws_region": properties.aws_region,
                "credentials_id": properties.credentials_id,
                "storage_configuration_id": properties.storage_configuration_id,
                "network_id": properties.network_id,
                "managed_services_customer_managed_key_id": properties.managed_services_customer_managed_key_id,
                "storage_customer_managed_key_id": properties.storage_customer_managed_key_id,
            }
            patch_request(patch_url, patch_body)
        else:
            logger.info("Workspace already found and no changes detected")
        wait_on_provisioning(workspace_id)
        deployment_name = current["deployment_name"]
        return WorkspaceResponse(
            physical_resource_id=workspace_id,
            workspace_name=properties.workspace_name,
            workspace_id=workspace_id,
            workspace_url=f"https://{deployment_name}.cloud.databricks.com",
            creation_time=current["creation_time"],
        )


def get_running_workspace(workspace_id: str) -> dict:
    """Get workspace, raises ResourceNotReadyError while it is still being provisioned"""
    response = get_workspace_by_id(workspace_id)
    if response is None:
        raise ResourceNotReadyError("not found")
    status = response["workspace_status"]
    if status in ("NOT_PROVISIONED", "PROVISIONING"):
        raise ResourceNotReadyError(f"status is {status}")
    if status != "RUNNING":
        raise RuntimeError(f"Status of workspace is {status} with message: {response.get('workspace_status_message')}")
    return response


def wait_on_provisioning(workspace_id: str):
    """Wait until provisioning is done"""
    wait_until_ready(
        lambda: get_running_workspace(workspace_id),
        f"Workspace {workspace_id}",
        timeout_seconds=WORKSPACE_WAIT_TIMEOUT_SECONDS,
    )
    logger.info(f"Workspace {workspace_id} is RUNNING")


def delete_workspaces(properties: WorkspaceProperties, physical_resource_id: str) -> CnfResponse:
    """Deleting a workspace"""
    url = get_workspaces_url()
    current = get_workspace_by_id(physical_resource_id)
    if current is None:
        current = get_workspace_by_name(properties.workspace_name)
    if current is not None:
        workspace_id = current["workspace_id"]
        delete_request(f"{url}/{workspace_id}")
    else:
        logger.warning("Already removed")
    return CnfResponse(physical_resource_id=properties.workspace_name)
