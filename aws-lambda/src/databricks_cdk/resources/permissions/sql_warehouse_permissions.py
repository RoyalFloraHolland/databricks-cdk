import logging

from pydantic import BaseModel

from databricks_cdk.resources.permissions.models import GroupPermission, ServicePrincipalPermission, UserPermission
from databricks_cdk.utils import CnfResponse, put_request

logger = logging.getLogger(__name__)


class Permission(BaseModel):
    permission_level: str


class SQLWarehousePermissionsProperties(BaseModel):
    action: str = "warehouse-permissions"
    workspace_url: str
    endpoint_id: str
    access_control_list: list[UserPermission | GroupPermission | ServicePrincipalPermission]


def get_warehouse_permissions_url(workspace_url: str, endpoint_id: str):
    """Getting url for warehouse permissions requests"""
    return f"{workspace_url}/api/2.0/permissions/sql/endpoints/{endpoint_id}"


def create_or_update_warehouse_permissions(
    properties: SQLWarehousePermissionsProperties,
) -> CnfResponse:
    """Replace warehouse permissions at databricks"""

    # Json data
    body = {
        "access_control_list": [a.dict() for a in properties.access_control_list],
    }
    put_request(
        f"{get_warehouse_permissions_url(properties.workspace_url, properties.endpoint_id)}",
        body=body,
    )
    return CnfResponse(
        physical_resource_id=f"{properties.endpoint_id}/permissions",
    )


def delete_warehouse_permissions(physical_resource_id: str) -> CnfResponse:
    """Call back for cloudformation purposes"""
    # no need to remove
    return CnfResponse(physical_resource_id=physical_resource_id)
