import json
import logging

from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, get_request, post_request, wait_until_found

logger = logging.getLogger(__name__)


Value = int | bool | str


class PolicyElement(BaseModel):
    type: str
    value: Value | None
    hidden: bool | None
    defaultValue: Value | None
    isOptional: bool | None
    minValue: int | None
    maxValue: int | None
    values: list[Value] | None
    pattern: str | None


class ClusterPolicy(BaseModel):
    name: str
    description: str | None
    definition: dict[str, PolicyElement]


class ClusterPolicyProperties(BaseModel):
    workspace_url: str
    cluster_policy: ClusterPolicy


def get_cluster_policy_url(workspace_url: str) -> str:
    """Getting url for job requests"""
    return f"{workspace_url}/api/2.0/policies/clusters"


def get_cluster_policy_by_id(cluster_policy_id: str, workspace_url: str) -> dict | None:
    """Getting cluster policy by id"""
    body = {"policy_id": cluster_policy_id}
    resp = get_request(url=f"{get_cluster_policy_url(workspace_url)}/get", body=body)
    return resp


def create_or_update_cluster_policy(
    properties: ClusterPolicyProperties, physical_resource_id: str | None
) -> CnfResponse:
    """Create cluster policy at databricks"""
    current = None
    base_url = get_cluster_policy_url(properties.workspace_url)
    body = json.loads(properties.cluster_policy.json(exclude_none=True))
    body["definition"] = json.dumps(body["definition"])

    if physical_resource_id is not None:
        current = get_cluster_policy_by_id(
            cluster_policy_id=physical_resource_id,
            workspace_url=properties.workspace_url,
        )
    if current is None:
        response = post_request(url=f"{base_url}/create", body=body)
        wait_until_found(
            lambda: get_cluster_policy_by_id(response["policy_id"], properties.workspace_url),
            f"Cluster policy {properties.cluster_policy.name}",
        )
        return CnfResponse(physical_resource_id=response["policy_id"])
    else:
        policy_id = current["policy_id"]
        body["policy_id"] = policy_id
        post_request(url=f"{base_url}/edit", body=body)
    return CnfResponse(physical_resource_id=policy_id)


def delete_cluster_policy(properties: ClusterPolicyProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes cluster policy at databricks"""
    base_url = get_cluster_policy_url(properties.workspace_url)
    current = get_cluster_policy_by_id(physical_resource_id, properties.workspace_url)
    if current is not None:
        body = {"policy_id": current.get("policy_id")}
        post_request(url=f"{base_url}/delete", body=body)
    else:
        logger.warning("Already removed")
    return CnfResponse(physical_resource_id=physical_resource_id)
