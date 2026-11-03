import logging

from pydantic import BaseModel

from databricks_cdk.resources.permissions.models import GroupPermission, ServicePrincipalPermission, UserPermission
from databricks_cdk.utils import CnfResponse, put_request

logger = logging.getLogger(__name__)


class ClusterPolicyPermissionsProperties(BaseModel):
    action: str = "cluster-policy-permissions"
    workspace_url: str
    cluster_policy_id: str
    access_control_list: list[UserPermission | GroupPermission | ServicePrincipalPermission]


def get_cluster_policy_permissions_url(workspace_url: str, cluster_policy_id: str):
    """Getting url for creating policy permissions requests"""
    return f"{workspace_url}/api/2.0/permissions/cluster-policies/{cluster_policy_id}"


def create_or_update_cluster_policy_permissions(
    properties: ClusterPolicyPermissionsProperties,
) -> CnfResponse:
    """Create cluster policy permissions at databricks"""

    # Json data
    body = {
        "access_control_list": [a.dict() for a in properties.access_control_list],
    }
    put_request(
        f"{get_cluster_policy_permissions_url(properties.workspace_url, properties.cluster_policy_id)}",
        body=body,
    )
    return CnfResponse(
        physical_resource_id=properties.cluster_policy_id,
    )


def delete_cluster_policy_permissions(physical_resource_id: str) -> CnfResponse:
    """Deletes cluster policy permissions at databricks"""
    # no need to remove
    return CnfResponse(physical_resource_id=physical_resource_id)
