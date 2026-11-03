import json
import logging

from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, delete_request, get_request, patch_request, post_request

logger = logging.getLogger(__name__)


class StorageCredential(BaseModel):
    name: str
    comment: str | None


class AwsIamRole(BaseModel):
    role_arn: str


class StorageCredentialAws(StorageCredential):
    aws_iam_role: AwsIamRole


class AzureServicePrincipal(BaseModel):
    directory_id: str
    application_id: str
    client_secret: str


class StorageCredentialAzure(StorageCredential):
    azure_service_principal: AzureServicePrincipal


class GcpServiceAccountKey(BaseModel):
    email: str
    private_key_id: str
    private_key: str


class StorageCredentialGcp(StorageCredential):
    gcp_service_account_key: GcpServiceAccountKey


class StorageCredentialsProperties(BaseModel):
    workspace_url: str
    storage_credential: StorageCredentialAws | StorageCredentialAzure | StorageCredentialGcp


class StorageCredentialsResponse(CnfResponse):
    storage_credential_id: str
    storage_credential_name: str


def get_storage_credential_url(workspace_url: str) -> str:
    """Getting url for job requests"""
    return f"{workspace_url}/api/2.1/unity-catalog/storage-credentials"


def get_storage_credential_by_name(name: str, base_url: str) -> dict | None:
    try:
        return get_request(f"{base_url}/{name}")
    except Exception as e:
        logger.info(f"Storage credential not found, returning None. Exception: {e}")
        return None


def create_or_update_storage_credential(
    properties: StorageCredentialsProperties,
) -> StorageCredentialsResponse:
    """Create storage_credentials at databricks"""
    base_url = get_storage_credential_url(properties.workspace_url)
    current = get_storage_credential_by_name(properties.storage_credential.name, base_url=base_url)
    body = json.loads(properties.storage_credential.json())
    if current is None:
        response = post_request(base_url, body=body)
    else:
        response = patch_request(f"{base_url}/{properties.storage_credential.name}", body=body)
    return StorageCredentialsResponse(
        storage_credential_name=properties.storage_credential.name,
        storage_credential_id=response.get("id"),
        physical_resource_id=properties.storage_credential.name,
    )


def delete_storage_credential(properties: StorageCredentialsProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes schema at databricks"""
    base_url = get_storage_credential_url(properties.workspace_url)
    current = get_storage_credential_by_name(properties.storage_credential.name, base_url=base_url)
    if current is not None:
        delete_request(f"{base_url}/{properties.storage_credential.name}")
    else:
        logger.warning("Already removed")
    return CnfResponse(physical_resource_id=physical_resource_id)
