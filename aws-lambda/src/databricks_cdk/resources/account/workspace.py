import logging
import time

from pydantic import BaseModel

from databricks_cdk.utils import (
    ACCOUNTS_BASE_URL,
    CnfResponse,
    delete_request,
    get_account_id,
    get_request,
    patch_request,
    post_request,
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
    """Getting workspace by name"""
    url = get_workspaces_url()
    return get_request(url=f"{url}/{workspace_id}")


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
        wait_on_provioning(workspace_id)
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
                "storage_configuration_id": properties.credentials_id,
                "network_id": properties.network_id,
                "managed_services_customer_managed_key_id": properties.managed_services_customer_managed_key_id,
                "storage_customer_managed_key_id": properties.storage_customer_managed_key_id,
            }
            patch_request(patch_url, patch_body)
        else:
            logger.info("Workspace already found and no changes detected")
        wait_on_provioning(workspace_id)
        deployment_name = current["deployment_name"]
        return WorkspaceResponse(
            physical_resource_id=workspace_id,
            workspace_name=properties.workspace_name,
            workspace_id=workspace_id,
            workspace_url=f"https://{deployment_name}.cloud.databricks.com",
            creation_time=current["creation_time"],
        )


def wait_on_provioning(workspace_id: str):
    """Wait until provisioning is done"""
    logger.info("Get status of workspace")
    url = f"{get_workspaces_url()}/{workspace_id}"
    response = get_request(url)
    while response["workspace_status"] == "PROVISIONING":
        logger.info("Status of workspace is still PROVISIONING")
        time.sleep(10)
        response = get_request(url)
    logger.info(f"Status of workspace is {response['workspace_status']}")
    if response["workspace_status"] != "RUNNING":
        raise RuntimeError(
            f"Status of workspace is {response['workspace_status']} with message: {response['workspace_status_message']}"
        )


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
