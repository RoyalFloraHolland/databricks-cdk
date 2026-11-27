from typing import Any
from unittest.mock import patch

from databricks_cdk.resources.unity_catalog.external_storage import (
    ExternalLocation,
    ExternalLocationProperties,
    create_or_update_external_location,
)


def _properties(url: str = "s3://bucket/prefix") -> ExternalLocationProperties:
    return ExternalLocationProperties(
        workspace_url="https://test.cloud.databricks.com",
        external_location=ExternalLocation(name="location", url=url, credential_name="credential"),
    )


def _existing(url: str = "s3://bucket/prefix") -> dict[str, Any]:
    return {
        "name": "location",
        "url": url,
        "credential_name": "credential",
        "credential_id": "credential-id",
        "read_only": False,
        "owner": "someone",
    }


@patch("databricks_cdk.resources.unity_catalog.external_storage.wait_until_found")
@patch("databricks_cdk.resources.unity_catalog.external_storage.patch_request")
@patch("databricks_cdk.resources.unity_catalog.external_storage.post_request")
@patch("databricks_cdk.resources.unity_catalog.external_storage.get_request", side_effect=Exception("not found"))
def test_creates_a_missing_location(get_request, post_request, patch_request, wait_until_found):
    create_or_update_external_location(_properties())

    post_request.assert_called_once()
    patch_request.assert_not_called()
    wait_until_found.assert_called_once()


@patch("databricks_cdk.resources.unity_catalog.external_storage.patch_request")
@patch("databricks_cdk.resources.unity_catalog.external_storage.post_request")
@patch("databricks_cdk.resources.unity_catalog.external_storage.get_request", return_value=_existing())
def test_does_not_update_an_unchanged_location(get_request, post_request, patch_request):
    response = create_or_update_external_location(_properties())

    post_request.assert_not_called()
    patch_request.assert_not_called()
    assert response.physical_resource_id == "location"


@patch("databricks_cdk.resources.unity_catalog.external_storage.patch_request")
@patch("databricks_cdk.resources.unity_catalog.external_storage.post_request")
@patch(
    "databricks_cdk.resources.unity_catalog.external_storage.get_request", return_value=_existing(url="s3://bucket/old")
)
def test_updates_a_changed_location(get_request, post_request, patch_request):
    create_or_update_external_location(_properties())

    post_request.assert_not_called()
    patch_request.assert_called_once_with(
        "https://test.cloud.databricks.com/api/2.1/unity-catalog/external-locations/location",
        body={
            "name": "location",
            "comment": None,
            "url": "s3://bucket/prefix",
            "credential_name": "credential",
            "read_only": False,
        },
    )
