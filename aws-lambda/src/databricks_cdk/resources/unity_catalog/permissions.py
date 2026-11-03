import json
import logging

from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, get_request, patch_request

logger = logging.getLogger(__name__)


class Permissions(BaseModel):
    principal: str
    privileges: list[str]


class PermissionsList(BaseModel):
    privilege_assignments: list[Permissions] = []


class PermissionDiff(BaseModel):
    principal: str
    add: list[str] = []
    remove: list[str] = []


class PermissionsDiff(BaseModel):
    changes: list[PermissionDiff]


class PermissionsProperties(BaseModel):
    workspace_url: str
    sec_type: str
    sec_id: str
    permissions: PermissionsList


class PermissionsResponse(CnfResponse):
    sec_type: str
    sec_id: str


def create_diff(current: PermissionsList, new: PermissionsList) -> PermissionsDiff:
    changes = []
    current_principals: dict[str, Permissions] = dict([(x.principal, x) for x in current.privilege_assignments])
    new_principals: dict[str, Permissions] = dict([(x.principal, x) for x in new.privilege_assignments])
    all_principals: set[str] = set(current_principals.keys()).union(new_principals.keys())

    for principal in all_principals:
        change = PermissionDiff(principal=principal)
        if principal not in current_principals:
            change.add = new_principals[principal].privileges
        elif principal not in new_principals:
            change.remove = current_principals[principal].privileges
        else:
            c = set(current_principals[principal].privileges)
            n = set(new_principals[principal].privileges)
            if c != n:
                change.remove = list(c.difference(n))
                change.add = list(n.difference(c))
        if len(change.add) > 0 or len(change.remove) > 0:
            changes.append(change)
    return PermissionsDiff(changes=changes)


def get_permissions_url(workspace_url: str, sec_type: str, sec_id: str):
    """Getting url for job requests"""
    return f"{workspace_url}/api/2.1/unity-catalog/permissions/{sec_type}/{sec_id}"


def create_or_update_permissions(
    properties: PermissionsProperties,
) -> PermissionsResponse:
    """Create permissions at databricks"""
    base_url = get_permissions_url(properties.workspace_url, properties.sec_type, properties.sec_id)
    current = PermissionsList(**get_request(base_url))
    diff = create_diff(current=current, new=properties.permissions)
    if len(diff.changes) > 0:
        patch_request(base_url, body=json.loads(diff.json()))
    return PermissionsResponse(
        sec_id=properties.sec_id,
        sec_type=properties.sec_type,
        physical_resource_id=f"{properties.sec_type}/{properties.sec_id}",
    )


def delete_permissions(properties: PermissionsProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes permissions at databricks"""
    base_url = get_permissions_url(properties.workspace_url, properties.sec_type, properties.sec_id)
    current = PermissionsList(**get_request(base_url))
    diff = create_diff(current=current, new=PermissionsList(privilege_assignments=[]))
    if len(diff.changes) > 0:
        patch_request(base_url, body=json.loads(diff.json()))
    return CnfResponse(physical_resource_id=physical_resource_id)
