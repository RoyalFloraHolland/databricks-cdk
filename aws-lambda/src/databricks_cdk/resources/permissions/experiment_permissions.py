from enum import Enum

from pydantic import BaseModel

from databricks_cdk.resources.permissions.models import Group, ServicePrincipal, User
from databricks_cdk.utils import CnfResponse, put_request


class ExperimentPermission(str, Enum):
    CAN_READ = "CAN_READ"
    CAN_EDIT = "CAN_EDIT"
    CAN_MANAGE = "CAN_MANAGE"


class UserPermission(User):
    permission_level: ExperimentPermission


class GroupPermission(Group):
    permission_level: ExperimentPermission


class ServicePrincipalPermission(ServicePrincipal):
    permission_level: ExperimentPermission


class ExperimentPermissionProperties(BaseModel):
    action: str = "experiment-permission"
    experiment_id: str
    access_control_list: list[UserPermission | GroupPermission | ServicePrincipalPermission]
    workspace_url: str


def get_experiment_permissions_url(workspace_url: str, experiment_id: str):
    return f"{workspace_url}/api/2.0/permissions/experiments/{experiment_id}"


def create_or_update_experiment_permissions(properties: ExperimentPermissionProperties):
    """
    Creates and updates the permissions on an existing experiment. It overwrites any existing
    permissions
    """
    body = {"access_control_list": [a.dict() for a in properties.access_control_list]}

    put_request(f"{get_experiment_permissions_url(properties.workspace_url, properties.experiment_id)}", body)

    return CnfResponse(physical_resource_id=f"{properties.experiment_id}/permissions")


def delete_experiment_permissions(properties: ExperimentPermissionProperties, physical_resource_id: str):
    """Removes all of the permission properties from an experiment"""
    put_request(
        f"{get_experiment_permissions_url(properties.workspace_url, properties.experiment_id)}",
        {"access_control_list": []},
    )

    return CnfResponse(physical_resource_id=f"{physical_resource_id}/permissions")
