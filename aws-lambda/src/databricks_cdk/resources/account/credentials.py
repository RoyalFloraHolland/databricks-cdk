import logging

from databricks.sdk.service.provisioning import CreateCredentialAwsCredentials, CreateCredentialStsRole
from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, get_account_client, wait_until_found

logger = logging.getLogger(__name__)


class CredentialsProperties(BaseModel):
    action: str = "credentials"
    credentials_name: str
    role_arn: str


class CredentialsResponse(CnfResponse):
    credentials_name: str
    credentials_id: str
    role_arn: str
    external_id: str
    creation_time: int


def create_or_update_credentials(
    properties: CredentialsProperties,
) -> CredentialsResponse:
    """Create credentials config at databricks"""
    account_client = get_account_client()
    all_credentials = account_client.credentials.list()
    current = next((c for c in all_credentials if c.credentials_name == properties.credentials_name), None)

    if current is None:
        # create credential
        credential = account_client.credentials.create(
            credentials_name=properties.credentials_name,
            aws_credentials=CreateCredentialAwsCredentials(CreateCredentialStsRole(properties.role_arn)),
        )
        wait_until_found(
            lambda: account_client.credentials.get(credentials_id=credential.credentials_id),
            f"Credentials {properties.credentials_name}",
        )
        return CredentialsResponse(
            physical_resource_id=credential.credentials_id,
            credentials_name=properties.credentials_name,
            credentials_id=credential.credentials_id,
            role_arn=properties.role_arn,
            external_id=credential.aws_credentials.sts_role.external_id,
            creation_time=credential.creation_time,
        )
    else:
        if current.aws_credentials.sts_role.role_arn != properties.role_arn:
            raise AttributeError("Role arn can't be changed after deployment")
        return CredentialsResponse(
            physical_resource_id=current.credentials_id,
            credentials_name=properties.credentials_name,
            credentials_id=current.credentials_id,
            role_arn=properties.role_arn,
            external_id=current.aws_credentials.sts_role.external_id,
            creation_time=current.creation_time,
        )


def delete_credentials(physical_resource_id: str) -> CnfResponse:
    """Deletes credentials config at databricks"""
    account_client = get_account_client()

    current = account_client.credentials.get(credentials_id=physical_resource_id)
    if current is not None:
        account_client.credentials.delete(credentials_id=physical_resource_id)
    else:
        logger.warning("Already removed")

    return CnfResponse(physical_resource_id=physical_resource_id)
