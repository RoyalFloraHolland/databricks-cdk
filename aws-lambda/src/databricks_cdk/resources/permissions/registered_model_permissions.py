from enum import Enum

from pydantic import BaseModel

from databricks_cdk.resources.permissions.models import Group, ServicePrincipal, User
from databricks_cdk.utils import CnfResponse, put_request


class RegisteredModelPermission(str, Enum):
    CAN_READ = "CAN_READ"
    CAN_EDIT = "CAN_EDIT"
    CAN_MANAGE_STAGING_VERSIONS = "CAN_MANAGE_STAGING_VERSIONS"
    CAN_MANAGE_PRODUCTION_VERSIONS = "CAN_MANAGE_PRODUCTION_VERSIONS"
    CAN_MANAGE = "CAN_MANAGE"


class UserPermission(User):
    permission_level: RegisteredModelPermission


class GroupPermission(Group):
    permission_level: RegisteredModelPermission


class ServicePrincipalPermission(ServicePrincipal):
    permission_level: RegisteredModelPermission


class RegisteredModelPermissionPermissionProperties(BaseModel):
    action: str = "registered-model-permission"
    registered_model_id: str
    access_control_list: list[UserPermission | GroupPermission | ServicePrincipalPermission]
    workspace_url: str


def get_registered_model_permissions_url(workspace_url: str, registered_model_id: str):
    return f"{workspace_url}/api/2.0/permissions/registered-models/{registered_model_id}"


def create_or_update_registered_model_permissions(properties: RegisteredModelPermissionPermissionProperties):
    """
    Creates and updates the permissions on an existing registered model. It overwrites any existing
    permissions
    """
    body = {"access_control_list": [a.dict() for a in properties.access_control_list]}

    put_request(
        f"{get_registered_model_permissions_url(properties.workspace_url, properties.registered_model_id)}", body
    )

    return CnfResponse(physical_resource_id=f"{properties.registered_model_id}/permissions")


def delete_registered_model_permissions(
    properties: RegisteredModelPermissionPermissionProperties, physical_resource_id: str
):
    """Removes all of the permission properties from a registered model"""
    put_request(
        f"{get_registered_model_permissions_url(properties.workspace_url, properties.registered_model_id)}",
        {"access_control_list": []},
    )

    return CnfResponse(physical_resource_id=f"{physical_resource_id}/permissions")
