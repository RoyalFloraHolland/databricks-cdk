import logging

from pydantic import BaseModel

from databricks_cdk.utils import (
    ACCOUNTS_BASE_URL,
    CnfResponse,
    delete_request,
    get_account_id,
    get_request,
    post_request,
    wait_until_found,
)

logger = logging.getLogger(__name__)


class StorageConfigProperties(BaseModel):
    action: str = "storage-configurations"
    storage_configuration_name: str
    bucket_name: str


class StorageConfigResponse(CnfResponse):
    storage_configuration_name: str
    storage_configuration_id: str
    bucket_name: str
    creation_time: int


def get_storage_configuration_url():
    """Return url for storage config requests"""
    account_id = get_account_id()

    # api-endpoint
    return f"{ACCOUNTS_BASE_URL}/api/2.0/accounts/{account_id}/storage-configurations"


def get_storage_by_id(storage_configuration_id: str) -> dict | None:
    """Get storage config based on id"""
    url = get_storage_configuration_url()
    return get_request(url=f"{url}/{storage_configuration_id}")


def get_storage_by_name(storage_configuration_name: str) -> dict | None:
    """Get storage config based on name"""
    url = get_storage_configuration_url()
    get_response = get_request(url=url)
    current = None
    for r in get_response:
        if r.get("storage_configuration_name") == storage_configuration_name:
            current = r
    return current


def create_or_update_storage_configuration(
    properties: StorageConfigProperties,
) -> StorageConfigResponse:
    """Creates storage config at databricks"""
    url = get_storage_configuration_url()

    current = get_storage_by_name(properties.storage_configuration_name)
    if current is None:
        # Json data
        body = {
            "storage_configuration_name": properties.storage_configuration_name,
            "root_bucket_info": {"bucket_name": properties.bucket_name},
        }
        response = post_request(url, body=body)
        wait_until_found(
            lambda: get_storage_by_id(response["storage_configuration_id"]),
            f"Storage configuration {properties.storage_configuration_name}",
        )
        return StorageConfigResponse(
            physical_resource_id=properties.storage_configuration_name,
            storage_configuration_name=properties.storage_configuration_name,
            storage_configuration_id=response["storage_configuration_id"],
            bucket_name=properties.bucket_name,
            creation_time=response["creation_time"],
        )
    else:
        current_bucket_name = current.get("root_bucket_info", {}).get("bucket_name")
        if current_bucket_name != properties.bucket_name:
            raise AttributeError("Bucket name can't be changed after deployment")
        return StorageConfigResponse(
            physical_resource_id=properties.storage_configuration_name,
            storage_configuration_name=properties.storage_configuration_name,
            storage_configuration_id=current["storage_configuration_id"],
            bucket_name=properties.bucket_name,
            creation_time=current["creation_time"],
        )


def delete_storage_configuration(properties: StorageConfigProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes storage config at databricks"""
    url = get_storage_configuration_url()
    current = get_storage_by_id(physical_resource_id)
    if current is None:
        current = get_storage_by_name(properties.storage_configuration_name)
    if current is not None:
        storage_configuration_id = current["storage_configuration_id"]
        delete_request(f"{url}/{storage_configuration_id}")
    else:
        logger.warning("Already removed")
    return CnfResponse(physical_resource_id=properties.storage_configuration_name)
