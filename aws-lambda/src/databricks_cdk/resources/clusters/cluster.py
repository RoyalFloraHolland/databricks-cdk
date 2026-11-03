import logging

import requests
from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, get_authorization_headers, get_request, post_request

logger = logging.getLogger(__name__)


class AutoScale(BaseModel):
    min_workers: int
    max_workers: int


class AwsAttributes(BaseModel):
    first_on_demand: int | None = None
    availability: str | None = None
    zone_id: str | None = None
    instance_profile_arn: str | None = None
    spot_bid_price_percent: int | None = None
    ebs_volume_type: str | None = None
    ebs_volume_count: int | None = None
    ebs_volume_size: int | None = None
    ebs_volume_iops: int | None = None
    ebs_volume_throughput: int | None = None


class DockerBasicAuth(BaseModel):
    username: str
    password: str


class DockerImage(BaseModel):
    url: str
    basic_auth: DockerBasicAuth | None


class Cluster(BaseModel):
    num_workers: int | None = None
    autoscale: AutoScale | None = None
    cluster_name: str
    spark_version: str
    spark_conf: dict[str, str] = {}
    aws_attributes: AwsAttributes
    node_type_id: str | None = None
    driver_node_type_id: str | None = None
    ssh_public_keys: list[str] = []
    custom_tags: dict | None = None
    cluster_log_conf: dict | None = None
    init_scripts: list[dict] = []
    docker_image: DockerImage | None = None
    spark_env_vars: dict[str, str] = {}
    autotermination_minutes: int | None = None
    enable_elastic_disk: bool | None = None
    driver_instance_pool_id: str | None = None
    instance_pool_id: str | None = None
    idempotency_token: str | None = None
    apply_policy_default_values: bool | None = None
    enable_local_disk_encryption: bool | None = None
    data_security_mode: str | None = None
    runtime_engine: str | None = None


class ClusterProperties(BaseModel):
    action: str = "cluster"
    workspace_url: str
    cluster: Cluster


def get_cluster_url(workspace_url: str):
    """Getting url for cluster requests"""
    return f"{workspace_url}/api/2.0/clusters"


def get_cluster_by_name(cluster_name: str, workspace_url: str):
    resp = get_request(f"{get_cluster_url(workspace_url)}/list")
    clusters = resp.get("clusters", [])
    for c in clusters:
        if c.get("cluster_name") == cluster_name:
            return c
    return None


def get_cluster_by_id(cluster_id: str, workspace_url: str) -> dict | None:
    """Getting cluster based on name"""
    body = {"cluster_id": cluster_id}
    resp = requests.get(
        f"{get_cluster_url(workspace_url)}/get",
        json=body,
        headers=get_authorization_headers(),
    )
    if resp.status_code == 400 and "does not exist" in resp.text:
        return None
    resp.raise_for_status()
    return resp.json()


def create_or_update_cluster(properties: ClusterProperties, physical_resource_id: str | None) -> CnfResponse:
    """Create cluster at databricks"""
    current = None
    if physical_resource_id is not None:
        current = get_cluster_by_id(physical_resource_id, properties.workspace_url)
    if current is None:
        # Json data
        body = properties.cluster.dict()
        response = post_request(f"{get_cluster_url(properties.workspace_url)}/create", body=body)
        return CnfResponse(
            physical_resource_id=response["cluster_id"],
        )
    else:
        cluster_id = current["cluster_id"]
        body = properties.cluster.dict()
        body["cluster_id"] = cluster_id
        post_request(f"{get_cluster_url(properties.workspace_url)}/edit", body=body)
        return CnfResponse(
            physical_resource_id=cluster_id,
        )


def delete_cluster(properties: ClusterProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes cluster at databricks"""
    current = get_cluster_by_id(physical_resource_id, properties.workspace_url)
    if current is not None:
        body = {
            "cluster_id": current.get("cluster_id"),
        }
        post_request(f"{get_cluster_url(properties.workspace_url)}/permanent-delete", body=body)
    else:
        logger.warning("Already removed")
    return CnfResponse(physical_resource_id=physical_resource_id)
