import logging

from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, get_request, post_request

logger = logging.getLogger(__name__)


class SecretProperties(BaseModel):
    action: str = "secret"
    workspace_url: str
    scope: str
    key: str
    string_value: str


def get_secret_url(workspace_url: str):
    """Getting url for secret requests"""
    return f"{workspace_url}/api/2.0/secrets"


def list_secrets(workspace_url: str, scope: str) -> list[dict] | None:
    url = get_secret_url(workspace_url)
    response = get_request(f"{url}/list?scope={scope}")
    return response.get("secrets")


def create_or_update_secret(properties: SecretProperties) -> CnfResponse:
    """Create secret at databricks"""

    url = get_secret_url(properties.workspace_url)
    create_body = {
        "scope": properties.scope,
        "key": properties.key,
        "string_value": properties.string_value,
    }
    post_request(f"{url}/put", body=create_body)

    return CnfResponse(physical_resource_id=properties.scope)


def delete_secret(properties: SecretProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes secret at databricks"""
    secret_list = list_secrets(properties.workspace_url, properties.scope)
    if properties.key in [s.get("key") for s in secret_list]:
        url = get_secret_url(properties.workspace_url)
        post_request(f"{url}/delete", body={"scope": properties.scope, "key": properties.key})

    return CnfResponse(physical_resource_id=physical_resource_id)
