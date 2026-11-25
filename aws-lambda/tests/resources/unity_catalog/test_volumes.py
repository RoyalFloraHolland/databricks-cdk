from unittest.mock import patch

import pytest

from databricks_cdk.resources.unity_catalog.volumes import (
    Volume,
    VolumeCreationError,
    VolumeInfo,
    VolumeProperties,
    VolumeResponse,
    VolumeType,
    create_or_update_volume,
    create_volume,
    delete_volume,
    update_volume,
)
from databricks_cdk.utils import CnfResponse


@patch("databricks_cdk.resources.unity_catalog.volumes.get_workspace_client")
@patch("databricks_cdk.resources.unity_catalog.volumes.update_volume")
@patch("databricks_cdk.resources.unity_catalog.volumes.create_volume")
def test_create_or_update_volume_create(
    patched_create_volume, patched_update_volume, patched_get_workspace_client, workspace_client
):
    patched_get_workspace_client.return_value = workspace_client

    mock_properties = VolumeProperties(
        workspace_url="https://test.cloud.databricks.com",
        volume=Volume(catalog_name="catalog", schema_name="schema", name="mock_name", comment="some comment"),
    )

    create_or_update_volume(properties=mock_properties, physical_resource_id=None)

    patched_create_volume.assert_called_once_with(mock_properties, workspace_client)
    patched_update_volume.assert_not_called()


@patch("databricks_cdk.resources.unity_catalog.volumes.get_workspace_client")
@patch("databricks_cdk.resources.unity_catalog.volumes.update_volume")
@patch("databricks_cdk.resources.unity_catalog.volumes.create_volume")
def test_create_or_update_volume_update(
    patched_create_volume, patched_update_volume, patched_get_workspace_client, workspace_client
):
    patched_get_workspace_client.return_value = workspace_client
    mock_physical_resource_id = "some_id"
    existing_volume = [VolumeInfo(volume_id=mock_physical_resource_id, name="mock_name", comment="some comment")]

    workspace_client.volumes.list.return_value = existing_volume

    mock_properties = VolumeProperties(
        workspace_url="https://test.cloud.databricks.com",
        volume=Volume(catalog_name="catalog", schema_name="schema", name="mock_name", comment="some comment"),
    )

    create_or_update_volume(properties=mock_properties, physical_resource_id=mock_physical_resource_id)

    patched_update_volume.assert_called_once_with(
        mock_properties, workspace_client, existing_volume[0], mock_physical_resource_id
    )
    patched_create_volume.assert_not_called()


@patch("databricks_cdk.resources.unity_catalog.volumes.get_workspace_client")
def test_create_or_update_volume_error(patch_get_workspace_client, workspace_client):
    patch_get_workspace_client.return_value = workspace_client

    mock_properties = VolumeProperties(
        workspace_url="https://test.cloud.databricks.com",
        volume=Volume(catalog_name="catalog", schema_name="schema", name="mock_name", comment="some comment"),
    )

    workspace_client.volumes.list.return_value = []

    with pytest.raises(VolumeCreationError):
        create_or_update_volume(properties=mock_properties, physical_resource_id="some_id")


def test_create_volume(workspace_client):
    mock_properties = VolumeProperties(
        workspace_url="https://test.cloud.databricks.com",
        volume=Volume(catalog_name="catalog", schema_name="schema", name="mock_name", comment="some comment"),
    )

    workspace_client.volumes.create.return_value = VolumeInfo(volume_id="some_id")

    response = create_volume(mock_properties, workspace_client)

    assert response == VolumeResponse(name="mock_name", physical_resource_id="some_id")
    workspace_client.volumes.create.assert_called_once_with(
        catalog_name="catalog",
        schema_name="schema",
        name="mock_name",
        volume_type=VolumeType.MANAGED,
        comment="some comment",
        storage_location=None,
    )


def test_create_volume_error(workspace_client):
    mock_properties = VolumeProperties(
        workspace_url="https://test.cloud.databricks.com",
        volume=Volume(catalog_name="catalog", schema_name="schema", name="mock_name", comment="some comment"),
    )

    workspace_client.volumes.create.return_value = VolumeInfo(volume_id=None)

    with pytest.raises(VolumeCreationError):
        create_volume(mock_properties, workspace_client)


def test_update_volume(workspace_client):
    mock_properties = VolumeProperties(
        workspace_url="https://test.cloud.databricks.com",
        volume=Volume(catalog_name="catalog", schema_name="schema", name="mock_name", comment="some comment"),
    )
    mock_volume_info = VolumeInfo(volume_id="some_id", full_name="catalog.schema.mock_name")

    workspace_client.volumes.update.return_value = mock_volume_info

    response = update_volume(mock_properties, workspace_client, mock_volume_info, "some_id")

    assert response == VolumeResponse(name="mock_name", physical_resource_id="some_id")
    workspace_client.volumes.update.assert_called_once_with(
        name="catalog.schema.mock_name",
        new_name="mock_name",
        comment="some comment",
    )


@patch("databricks_cdk.resources.unity_catalog.volumes.get_workspace_client")
def test_delete_volume(patched_get_workspace_client, workspace_client):

    patched_get_workspace_client.return_value = workspace_client

    mock_properties = VolumeProperties(
        workspace_url="https://test.cloud.databricks.com",
        volume=Volume(catalog_name="catalog", schema_name="schema", name="mock_name", comment="some comment"),
    )
    response = delete_volume(mock_properties, "some_id")

    assert response == CnfResponse(physical_resource_id="some_id")
    workspace_client.volumes.delete.assert_called_once_with(
        name="catalog.schema.mock_name",
    )
