import json
import logging

from pydantic import BaseModel

from databricks_cdk.resources.unity_catalog.storage_credentials import (
    AwsIamRole,
    StorageCredentialAws,
    StorageCredentialsProperties,
    create_or_update_storage_credential,
)
from databricks_cdk.utils import CnfResponse, delete_request, get_request, patch_request, post_request

logger = logging.getLogger(__name__)


class Metastore(BaseModel):
    name: str
    storage_root: str
    owner: str | None


class MetastoreProperties(BaseModel):
    workspace_url: str
    metastore: Metastore
    iam_role: str


class MetastoreResponse(CnfResponse):
    metastore_id: str
    global_metastore_id: str


def get_metastore_url(workspace_url: str):
    """Getting url for job requests"""
    return f"{workspace_url}/api/2.1/unity-catalog/metastores"


def get_metastore_by_id(metastore_id: str, base_url: str) -> dict | None:
    return get_request(f"{base_url}/{metastore_id}")


def get_metastore_by_name(metastore_name: str, base_url: str) -> dict | None:
    results = get_request(base_url).get("metastores", [])
    for m in results:
        if m.get("name") == metastore_name:
            return m
    return None


def create_or_update_metastore(properties: MetastoreProperties, physical_resource_id: str | None) -> MetastoreResponse:
    """Create metastore at databricks"""
    current: dict | None = None
    credential_result = create_or_update_storage_credential(
        StorageCredentialsProperties(
            workspace_url=properties.workspace_url,
            storage_credential=StorageCredentialAws(name="root", aws_iam_role=AwsIamRole(role_arn=properties.iam_role)),
        )
    )
    base_url = get_metastore_url(properties.workspace_url)
    if physical_resource_id is not None:
        current = get_metastore_by_id(physical_resource_id, base_url=base_url)
    if current is None:
        current = get_metastore_by_name(properties.metastore.name, base_url=base_url)
    if current is None:
        # create metastore
        current = post_request(base_url, body=json.loads(properties.metastore.json()))
    metastore_id = current.get("metastore_id")
    body = json.loads(properties.metastore.json())
    body["storage_root_credential_id"] = credential_result.storage_credential_id
    if current.get("storage_root").startswith(properties.metastore.storage_root):
        del body["storage_root"]
    else:
        new_storage_root = f"{properties.metastore.storage_root}/{metastore_id}"
        raise RuntimeError(
            f"storage_root can't be changed after first deployment, old: {current.get('storage_root')}, new: {new_storage_root}"
        )
    update_response = patch_request(f"{base_url}/{metastore_id}", body=body)
    global_metastore_id = update_response.get("global_metastore_id")
    return MetastoreResponse(
        metastore_id=metastore_id,
        global_metastore_id=global_metastore_id,
        physical_resource_id=metastore_id,
    )


def delete_metastore(properties: MetastoreProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes metastore at databricks"""
    base_url = get_metastore_url(properties.workspace_url)
    current = None
    if physical_resource_id is not None:
        current = get_metastore_by_id(physical_resource_id, base_url=base_url)
    if current is None:
        current = get_metastore_by_name(properties.metastore.name, base_url=base_url)
    if current is not None:
        metastore_id = current.get("metastore_id")
        delete_request(f"{base_url}/{metastore_id}")
    else:
        logger.warning("Already removed")
    return CnfResponse(physical_resource_id=physical_resource_id)
