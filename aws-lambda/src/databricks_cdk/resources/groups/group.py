import logging

from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, get_request, post_request

logger = logging.getLogger(__name__)


class UserMember(BaseModel):
    user_name: str


class GroupMembers(BaseModel):
    group_name: str


class GroupProperties(BaseModel):
    action: str = "group"
    workspace_url: str
    group_name: str
    members: list[UserMember | GroupMembers]


class GroupResponse(CnfResponse):
    group_name: str


def get_groups_url(workspace_url: str):
    """Getting url for groups requests"""
    return f"{workspace_url}/api/2.0/groups"


def get_current_group_members(group_name: str, workspace_url: str) -> GroupProperties | None:
    """Return current members of a group, returns None is group does not exist"""
    body = {"group_name": group_name}
    response = get_request(f"{get_groups_url(workspace_url)}/list-members", body=body)
    if response is None:
        return None
    members = response.get("members", [])
    return GroupProperties(
        workspace_url=workspace_url,
        group_name=group_name,
        members=members,
    )


def create_or_update_group(properties: GroupProperties) -> GroupResponse:
    """Create group at databricks"""

    # Json data
    current = get_current_group_members(properties.group_name, properties.workspace_url)
    if current is None:
        create_body = {"group_name": properties.group_name}
        post_request(f"{get_groups_url(properties.workspace_url)}/create", body=create_body)
        current = GroupProperties(
            workspace_url=properties.workspace_url,
            group_name=properties.group_name,
            members=[],
        )
    for member in properties.members:
        if member not in current.members:
            # Adding users that does not exists in group
            add_member_body = member.dict()
            add_member_body["parent_name"] = properties.group_name
            post_request(
                f"{get_groups_url(properties.workspace_url)}/add-member",
                body=add_member_body,
            )
    for member in current.members:
        # Removing members from group
        if member not in properties.members:
            remove_member_body = member.dict()
            remove_member_body["parent_name"] = properties.group_name
            post_request(
                f"{get_groups_url(properties.workspace_url)}/remove-member",
                body=remove_member_body,
            )

    return GroupResponse(
        physical_resource_id=properties.group_name,
        group_name=properties.group_name,
    )


def delete_group(properties: GroupProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes group at databricks"""
    if properties.group_name not in ["admins", "users"]:
        delete_body = {"group_name": properties.group_name}
        post_request(f"{get_groups_url(properties.workspace_url)}/delete", body=delete_body)

    return CnfResponse(physical_resource_id=physical_resource_id)
