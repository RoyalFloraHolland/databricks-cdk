import logging

from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, get_request, post_request

logger = logging.getLogger(__name__)


class InstanceProfileProperties(BaseModel):
    action: str = "instance-profile"
    workspace_url: str
    instance_profile_arn: str
    is_meta_instance_profile: bool = False
    skip_validation: bool = False


def get_instance_profile_url(workspace_url: str):
    """Getting url for instance_profile requests"""
    return f"{workspace_url}/api/2.0/instance-profiles"


def get_instance_profile_by_arn(instance_profile_arn: str, workspace_url: str) -> dict | None:
    """Getting instance_profile based on arn"""
    get_response = get_request(url=f"{get_instance_profile_url(workspace_url)}/list")
    if "instance_profiles" in get_response:
        for r in get_response["instance_profiles"]:
            if r.get("instance_profile_arn") == instance_profile_arn:
                return r
    return None


def create_or_update_instance_profile(
    properties: InstanceProfileProperties,
) -> CnfResponse:
    """Create instance_profile at databricks"""

    current = get_instance_profile_by_arn(properties.instance_profile_arn, properties.workspace_url)
    if current is None:
        # Json data
        body = {
            "instance_profile_arn": properties.instance_profile_arn,
            "is_meta_instance_profile": properties.is_meta_instance_profile,
            "skip_validation": properties.skip_validation,
        }
        post_request(f"{get_instance_profile_url(properties.workspace_url)}/add", body=body)
        return CnfResponse(
            physical_resource_id=properties.instance_profile_arn,
        )
    else:
        if current["is_meta_instance_profile"] != properties.is_meta_instance_profile:
            raise AttributeError("is_meta_instance_profile can't changed after deployment")
        return CnfResponse(
            physical_resource_id=properties.instance_profile_arn,
        )


def delete_instance_profile(properties: InstanceProfileProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes instance_profile at databricks"""
    current = get_instance_profile_by_arn(properties.instance_profile_arn, properties.workspace_url)
    if current is not None:
        body = {
            "instance_profile_arn": physical_resource_id,
        }
        post_request(f"{get_instance_profile_url(properties.workspace_url)}/remove", body=body)
    else:
        logger.warning("Already removed")
    return CnfResponse(physical_resource_id=physical_resource_id)
