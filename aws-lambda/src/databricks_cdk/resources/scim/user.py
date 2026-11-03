import logging

from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, delete_request, get_request, post_request

logger = logging.getLogger(__name__)


class UserProperties(BaseModel):
    action: str = "user"
    workspace_url: str
    user_name: str


class UserResponse(CnfResponse):
    user_name: str
    user_id: int


def get_user_url(workspace_url: str):
    """Getting url for user requests"""
    return f"{workspace_url}/api/2.0/preview/scim/v2/Users"


def get_user_by_user_name(user_name: str, workspace_url: str) -> dict | None:
    """Getting user based on user_name"""
    get_response = get_request(
        url=f"{get_user_url(workspace_url)}",
        params={"filter": f"userName eq {user_name}"},
    )
    if get_response["totalResults"] == 0:
        return None
    return get_response["Resources"][0]


def create_or_update_user(properties: UserProperties) -> UserResponse:
    """Create user at databricks"""

    current = get_user_by_user_name(properties.user_name, properties.workspace_url)
    if current is None:
        # Json data
        body = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": properties.user_name,
        }
        reponse = post_request(f"{get_user_url(properties.workspace_url)}", body=body)
        user_id = reponse["id"]
    else:
        user_id = current["id"]
    return UserResponse(physical_resource_id=user_id, user_name=properties.user_name, user_id=user_id)


def delete_user(properties: UserProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes user at databricks"""
    current = get_user_by_user_name(properties.user_name, properties.workspace_url)
    if current is not None:
        delete_request(f"{get_user_url(properties.workspace_url)}/{current['id']}")
    else:
        logger.warning("Already removed")
    return CnfResponse(physical_resource_id=physical_resource_id)
