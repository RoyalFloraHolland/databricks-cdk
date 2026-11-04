import os
from unittest.mock import MagicMock, patch

import pytest
from databricks.sdk import AccountClient, CredentialsAPI, ExperimentsAPI, ModelRegistryAPI, VolumesAPI, WorkspaceClient
from databricks.sdk.service.iam import AccountServicePrincipalsAPI, ServicePrincipalsAPI
from databricks.sdk.service.oauth2 import ServicePrincipalSecretsAPI


@pytest.fixture(scope="function", autouse=True)
def aws_credentials():
    """Generate fake AWS environment variables so boto3 is never called with 'real' values"""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "eu-west-1"


@pytest.fixture(scope="function", autouse=True)
def patched_sleep():
    """Make readiness waits instant, sleeping advances a fake clock instead of real time"""
    clock = {"now": 0.0}

    def fake_sleep(seconds: float):
        clock["now"] += seconds

    with (
        patch("databricks_cdk.utils.monotonic", side_effect=lambda: clock["now"]),
        patch("databricks_cdk.utils.sleep", side_effect=fake_sleep) as patched,
    ):
        yield patched


@pytest.fixture(scope="function")
def workspace_client():
    workspace_client = MagicMock(spec=WorkspaceClient)

    # mock all of the underlying service api's
    workspace_client.model_registry = MagicMock(spec=ModelRegistryAPI)
    workspace_client.experiments = MagicMock(spec=ExperimentsAPI)
    workspace_client.volumes = MagicMock(spec=VolumesAPI)
    workspace_client.service_principals = MagicMock(spec=ServicePrincipalsAPI)

    return workspace_client


@pytest.fixture(scope="function")
def account_client():
    account_client = MagicMock(spec=AccountClient)

    # mock all of the underlying service api's
    account_client.credentials = MagicMock(spec=CredentialsAPI)
    account_client.service_principal_secrets = MagicMock(spec=ServicePrincipalSecretsAPI)
    account_client.service_principals = MagicMock(spec=AccountServicePrincipalsAPI)

    return account_client
