from unittest.mock import patch

import pytest
from databricks.sdk.service.provisioning import (
    AwsCredentials,
    CreateCredentialAwsCredentials,
    CreateCredentialStsRole,
    Credential,
    StsRole,
)

from databricks_cdk.resources.account.credentials import (
    CredentialsProperties,
    CredentialsResponse,
    create_or_update_credentials,
    delete_credentials,
)
from databricks_cdk.utils import CnfResponse


@patch("databricks_cdk.resources.account.credentials.get_account_client")
def test_create_credentials_non_existing(patched_get_account_client, account_client):
    aws_credentials = AwsCredentials(sts_role=StsRole(role_arn="arn:aws:iam::xxxxxx:role/xxx"))
    account_client.credentials.create.return_value = Credential(
        credentials_id="2206cf0e-ddeb-4982-a6d1-28bc887c8479",
        credentials_name="test",
        aws_credentials=aws_credentials,
        creation_time=0,
        account_id="1234",
    )

    patched_get_account_client.return_value = account_client

    props = CredentialsProperties(
        credentials_name="test",
        role_arn="arn:aws:iam::xxxxxx:role/xxx",
    )

    response = create_or_update_credentials(props)
    assert response == CredentialsResponse(
        physical_resource_id="2206cf0e-ddeb-4982-a6d1-28bc887c8479",
        credentials_name="test",
        credentials_id="2206cf0e-ddeb-4982-a6d1-28bc887c8479",
        role_arn="arn:aws:iam::xxxxxx:role/xxx",
        external_id=None,
        creation_time=0,
    )
    account_client.credentials.create.assert_called_once_with(
        credentials_name="test",
        aws_credentials=CreateCredentialAwsCredentials(
            sts_role=CreateCredentialStsRole(role_arn="arn:aws:iam::xxxxxx:role/xxx")
        ),
    )


@patch("databricks_cdk.resources.account.credentials.get_account_client")
def test_create_credentials_exists(patched_get_account_client, account_client):
    aws_credentials = AwsCredentials(sts_role=StsRole(role_arn="arn:aws:iam::xxxxxx:role/xxx"))
    current = Credential(
        credentials_id="2206cf0e-ddeb-4982-a6d1-28bc887c8479",
        credentials_name="test",
        aws_credentials=aws_credentials,
        creation_time=0,
        account_id="1234",
    )

    account_client.credentials.list.return_value = [current]
    patched_get_account_client.return_value = account_client

    props = CredentialsProperties(
        credentials_name="test",
        role_arn="arn:aws:iam::xxxxxx:role/xxx",
    )

    response = create_or_update_credentials(props)
    assert response == CredentialsResponse(
        physical_resource_id="2206cf0e-ddeb-4982-a6d1-28bc887c8479",
        credentials_name="test",
        credentials_id="2206cf0e-ddeb-4982-a6d1-28bc887c8479",
        role_arn="arn:aws:iam::xxxxxx:role/xxx",
        external_id=None,
        creation_time=0,
    )

    # make sure create is not called
    assert account_client.credentials.create.call_count == 0


@patch("databricks_cdk.resources.account.credentials.get_account_client")
def test_create_credentials_different_role_arn(patched_get_account_client, account_client):
    current = Credential(
        credentials_id="2206cf0e-ddeb-4982-a6d1-28bc887c8479",
        credentials_name="test",
        aws_credentials=AwsCredentials(sts_role=StsRole(role_arn="arn:aws:iam::xxxxxx:role/xxx")),
        creation_time=0,
        account_id="1234",
    )

    account_client.credentials.list.return_value = [current]
    patched_get_account_client.return_value = account_client

    # existing has different role_arn
    props = CredentialsProperties(
        credentials_name="test",
        role_arn="arn:aws:iam::xxxxxx:role/different",
    )

    with pytest.raises(AttributeError):
        create_or_update_credentials(props)

    # make sure create is not called
    assert account_client.credentials.create.call_count == 0


@patch("databricks_cdk.resources.account.credentials.get_account_client")
def test_delete_credentials(patched_get_account_client, account_client):
    current = Credential(
        credentials_id="2206cf0e-ddeb-4982-a6d1-28bc887c8479",
        credentials_name="test",
        aws_credentials=AwsCredentials(sts_role=StsRole(role_arn="arn:aws:iam::xxxxxx:role/xxx")),
        creation_time=0,
        account_id="1234",
    )
    account_client.credentials.get.return_value = current
    patched_get_account_client.return_value = account_client

    response = delete_credentials("2206cf0e-ddeb-4982-a6d1-28bc887c8479")
    assert response == CnfResponse(
        physical_resource_id="2206cf0e-ddeb-4982-a6d1-28bc887c8479",
    )

    account_client.credentials.delete.assert_called_once_with(credentials_id="2206cf0e-ddeb-4982-a6d1-28bc887c8479")
