import logging

from databricks.sdk.service.catalog import PermissionsList, PrivilegeAssignment, SecurableType
from pydantic import BaseModel

from databricks_cdk.resources.permissions.changes import get_permission_changes
from databricks_cdk.utils import CnfResponse, get_workspace_client

logger = logging.getLogger(__name__)


class VolumePermissionsProperties(BaseModel):
    workspace_url: str
    volume_name: str
    privilege_assignments: list[PrivilegeAssignment] = []


def create_or_update_volume_permissions(
    properties: VolumePermissionsProperties,
) -> CnfResponse:
    """Create volume permissions on volume at databricks"""
    logger.info(f"Creating volume permissions {properties.privilege_assignments} for volume {properties.volume_name}")
    workspace_client = get_workspace_client(properties.workspace_url)
    existing_grants: PermissionsList = workspace_client.grants.get(
        securable_type=SecurableType.VOLUME, full_name=properties.volume_name
    )

    permission_changes = get_permission_changes(existing_grants, properties.privilege_assignments)

    workspace_client.grants.update(
        securable_type=SecurableType.VOLUME,
        full_name=properties.volume_name,
        changes=permission_changes,
    )

    return CnfResponse(
        physical_resource_id=f"{properties.volume_name}/permissions",
    )


def delete_volume_permissions(properties: VolumePermissionsProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes all volume permissions on volume at databricks"""
    workspace_client = get_workspace_client(properties.workspace_url)
    existing_grants: PermissionsList = workspace_client.grants.get(
        securable_type=SecurableType.VOLUME, full_name=properties.volume_name
    )

    permission_changes = get_permission_changes(existing_grants, [])

    workspace_client.grants.update(
        securable_type=SecurableType.VOLUME,
        full_name=properties.volume_name,
        changes=permission_changes,
    )

    return CnfResponse(
        physical_resource_id=physical_resource_id,
    )
