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


class NetworksProperties(BaseModel):
    action: str = "networks"
    network_name: str
    vpc_id: str
    subnet_ids: list[str]
    security_group_ids: list[str]
    # vpc_endpoints: dict  # TODO: no need directly


class NetworksResponse(CnfResponse):
    network_name: str
    network_id: str
    vpc_id: str
    subnet_ids: list[str]
    security_group_ids: list[str]
    creation_time: int


def get_networks_url():
    """Return url for network api requests"""
    account_id = get_account_id()

    # api-endpoint
    return f"{ACCOUNTS_BASE_URL}/api/2.0/accounts/{account_id}/networks"


def get_network_by_id(network_id: str) -> dict | None:
    """Getting network based on id"""
    url = get_networks_url()
    return get_request(url=f"{url}/{network_id}")


def get_network_by_name(network_name: str) -> dict | None:
    """Getting network based on name"""
    url = get_networks_url()
    get_response = get_request(url=url)
    current = None
    for r in get_response:
        if r.get("network_name") == network_name:
            current = r
    return current


def create_or_update_networks(properties: NetworksProperties) -> NetworksResponse:
    """Creates network at databricks"""
    url = get_networks_url()

    current = get_network_by_name(properties.network_name)
    if current is None:
        # Json data
        body = {
            "network_name": properties.network_name,
            "vpc_id": properties.vpc_id,
            "subnet_ids": properties.subnet_ids,
            "security_group_ids": properties.security_group_ids,
        }
        response = post_request(url, body=body)
        wait_until_found(lambda: get_network_by_id(response["network_id"]), f"Network {properties.network_name}")
        return NetworksResponse(
            physical_resource_id=properties.network_name,
            network_name=properties.network_name,
            network_id=response["network_id"],
            vpc_id=properties.vpc_id,
            subnet_ids=properties.subnet_ids,
            security_group_ids=properties.security_group_ids,
            creation_time=response["creation_time"],
        )
    else:
        current_vpc_id = current.get("vpc_id")
        if current_vpc_id != properties.vpc_id:
            raise AttributeError("vpc_id can't be changed after deployment")
        current_subnet_ids = current.get("subnet_ids")
        if current_subnet_ids != properties.subnet_ids:
            raise AttributeError("subnet_ids can't be changed after deployment")
        current_security_group_ids = current.get("security_group_ids")
        if current_security_group_ids != properties.security_group_ids:
            raise AttributeError("security_group_ids can't be changed after deployment")
        return NetworksResponse(
            physical_resource_id=properties.network_name,
            network_name=properties.network_name,
            network_id=current["network_id"],
            vpc_id=properties.vpc_id,
            subnet_ids=properties.subnet_ids,
            security_group_ids=properties.security_group_ids,
            creation_time=current["creation_time"],
        )


def delete_networks(properties: NetworksProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes network at databricks"""
    url = get_networks_url()

    current = get_network_by_id(physical_resource_id)
    if current is None:
        current = get_network_by_name(properties.network_name)
    if current is not None:
        network_id = current["network_id"]
        delete_request(f"{url}/{network_id}")
    else:
        logger.warning("Already removed")
    return CnfResponse(physical_resource_id=properties.network_name)
