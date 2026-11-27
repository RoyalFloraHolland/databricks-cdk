from typing import Any
from unittest.mock import patch

from databricks_cdk.resources.unity_catalog.storage_credentials import (
    AwsIamRole,
    StorageCredentialAws,
    StorageCredentialsProperties,
    create_or_update_storage_credential,
)


def _properties(role_arn: str = "arn:aws:iam::123:role/catalog") -> StorageCredentialsProperties:
    return StorageCredentialsProperties(
        workspace_url="https://test.cloud.databricks.com",
        storage_credential=StorageCredentialAws(name="credential", aws_iam_role=AwsIamRole(role_arn=role_arn)),
    )


def _existing(role_arn: str = "arn:aws:iam::123:role/catalog") -> dict[str, Any]:
    return {
        "id": "credential-id",
        "name": "credential",
        "aws_iam_role": {
            "role_arn": role_arn,
            "external_id": "ext",
            "unity_catalog_iam_arn": "arn:aws:iam::456:role/uc",
        },
        "read_only": False,
        "owner": "someone",
    }


@patch("databricks_cdk.resources.unity_catalog.storage_credentials.wait_until_found")
@patch("databricks_cdk.resources.unity_catalog.storage_credentials.patch_request")
@patch("databricks_cdk.resources.unity_catalog.storage_credentials.post_request", return_value={"id": "new-id"})
@patch("databricks_cdk.resources.unity_catalog.storage_credentials.get_request", side_effect=Exception("not found"))
def test_creates_a_missing_credential(get_request, post_request, patch_request, wait_until_found):
    response = create_or_update_storage_credential(_properties())

    post_request.assert_called_once_with(
        "https://test.cloud.databricks.com/api/2.1/unity-catalog/storage-credentials",
        body={"name": "credential", "comment": None, "aws_iam_role": {"role_arn": "arn:aws:iam::123:role/catalog"}},
    )
    patch_request.assert_not_called()
    wait_until_found.assert_called_once()
    assert response.storage_credential_id == "new-id"


@patch("databricks_cdk.resources.unity_catalog.storage_credentials.patch_request")
@patch("databricks_cdk.resources.unity_catalog.storage_credentials.post_request")
@patch("databricks_cdk.resources.unity_catalog.storage_credentials.get_request", return_value=_existing())
def test_does_not_update_an_unchanged_credential(get_request, post_request, patch_request):
    response = create_or_update_storage_credential(_properties())

    post_request.assert_not_called()
    patch_request.assert_not_called()
    assert response.storage_credential_id == "credential-id"
    assert response.physical_resource_id == "credential"


@patch("databricks_cdk.resources.unity_catalog.storage_credentials.patch_request", return_value={"id": "credential-id"})
@patch("databricks_cdk.resources.unity_catalog.storage_credentials.post_request")
@patch(
    "databricks_cdk.resources.unity_catalog.storage_credentials.get_request",
    return_value=_existing(role_arn="arn:aws:iam::123:role/old"),
)
def test_updates_a_changed_credential(get_request, post_request, patch_request):
    create_or_update_storage_credential(_properties())

    post_request.assert_not_called()
    patch_request.assert_called_once_with(
        "https://test.cloud.databricks.com/api/2.1/unity-catalog/storage-credentials/credential",
        body={"name": "credential", "comment": None, "aws_iam_role": {"role_arn": "arn:aws:iam::123:role/catalog"}},
    )
