import logging

from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, get_request, post_request, wait_until_found

logger = logging.getLogger(__name__)


class SecretScopeProperties(BaseModel):
    action: str = "secret-scope"
    workspace_url: str
    scope: str
    initial_manage_principal: str


def get_secret_scope_url(workspace_url: str):
    """Getting url for secret_scope requests"""
    return f"{workspace_url}/api/2.0/secrets/scopes"


def get_scope(properties: SecretScopeProperties):
    url = get_secret_scope_url(properties.workspace_url)
    list_response = get_request(f"{url}/list").get("scopes", [])
    for s in list_response:
        if s.get("name") == properties.scope:
            return s
    return None


def create_or_update_secret_scope(properties: SecretScopeProperties) -> CnfResponse:
    """Create secret_scope at databricks"""

    current_scope = get_scope(properties)
    if current_scope is None:
        url = get_secret_scope_url(properties.workspace_url)
        create_body = {
            "scope": properties.scope,
            "initial_manage_principal": properties.initial_manage_principal,
        }
        post_request(f"{url}/create", body=create_body)
        wait_until_found(lambda: get_scope(properties), f"Secret scope {properties.scope}")

    return CnfResponse(physical_resource_id=properties.scope)


def delete_secret_scope(properties: SecretScopeProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes secret_scope at databricks"""
    current = get_scope(properties)
    if current is not None:
        url = get_secret_scope_url(properties.workspace_url)
        post_request(f"{url}/delete", body={"scope": properties.scope})

    return CnfResponse(physical_resource_id=physical_resource_id)
