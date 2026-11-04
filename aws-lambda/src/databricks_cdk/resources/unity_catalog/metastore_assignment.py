import logging

from pydantic import BaseModel

from databricks_cdk.resources.unity_catalog.metastore import get_metastore_by_name, get_metastore_url
from databricks_cdk.utils import (
    ACCOUNTS_BASE_URL,
    CnfResponse,
    ResourceNotReadyError,
    delete_request,
    get_account_id,
    get_request,
    is_not_found_error,
    put_request,
    wait_until_ready,
)

logger = logging.getLogger(__name__)


class AssignmentProperties(BaseModel):
    workspace_url: str
    workspace_id: str
    metastore_name: str
    default_catalog_name: str


class AssignmentResponse(CnfResponse):
    workspace_id: str


def get_assignment_url(workspace_url: str, workspace_id: str):
    """Getting url for job requests"""
    return f"{workspace_url}/api/2.1/unity-catalog/workspaces/{workspace_id}/metastore"


def check_metastore_assigned(workspace_id: str, metastore_id: str) -> None:
    """Raises ResourceNotReadyError until the account reports the metastore as assigned to the workspace"""
    url = f"{ACCOUNTS_BASE_URL}/api/2.0/accounts/{get_account_id()}/workspaces/{workspace_id}/metastore"
    try:
        response = get_request(url)
    except Exception as e:
        if is_not_found_error(e):
            raise ResourceNotReadyError("no metastore assigned") from e
        raise
    assigned_metastore_id = response.get("metastore_assignment", {}).get("metastore_id")
    if assigned_metastore_id != metastore_id:
        raise ResourceNotReadyError(f"assigned metastore is {assigned_metastore_id}")


def create_or_update_assignment(properties: AssignmentProperties) -> AssignmentResponse:
    """Create assignment at databricks"""
    base_url = get_assignment_url(properties.workspace_url, properties.workspace_id)
    metastore_result = get_metastore_by_name(
        properties.metastore_name, base_url=get_metastore_url(properties.workspace_url)
    )
    if metastore_result is None:
        raise RuntimeError(f"No metastore found with name {properties.metastore_name}")
    metastore_id = metastore_result["metastore_id"]
    body = {
        "metastore_id": metastore_id,
        "default_catalog_name": properties.default_catalog_name,
    }
    put_request(base_url, body=body)
    wait_until_ready(
        lambda: check_metastore_assigned(properties.workspace_id, metastore_id),
        f"Metastore assignment of {properties.metastore_name} to workspace {properties.workspace_id}",
    )
    return AssignmentResponse(
        workspace_id=properties.workspace_id,
        physical_resource_id=properties.workspace_id,
    )


def delete_assignment(properties: AssignmentProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes assignment at databricks"""
    base_url = get_assignment_url(properties.workspace_url, properties.workspace_id)
    delete_request(base_url, body={"metastore_id": properties.metastore_id})
    return CnfResponse(physical_resource_id=physical_resource_id)
