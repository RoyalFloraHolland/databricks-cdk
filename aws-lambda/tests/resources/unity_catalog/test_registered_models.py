from unittest.mock import MagicMock, call, patch

import pytest
from databricks.sdk.errors import NotFound, ResourceAlreadyExists
from databricks.sdk.service.catalog import ModelVersionInfo, RegisteredModelInfo

from databricks_cdk.resources.unity_catalog.registered_models import (
    RegisteredModelCreationError,
    RegisteredModelDeletionError,
    RegisteredModelTag,
    UnityCatalogRegisteredModel,
    UnityCatalogRegisteredModelProperties,
    UnityCatalogRegisteredModelResponse,
    create_or_update_unity_catalog_registered_model,
    create_unity_catalog_registered_model,
    delete_unity_catalog_registered_model,
    sync_registered_model_tags,
    update_unity_catalog_registered_model,
)
from databricks_cdk.utils import CnfResponse


def _properties(
    comment: str | None = "some comment", name: str = "model", adopt_existing: bool = False
) -> UnityCatalogRegisteredModelProperties:
    return UnityCatalogRegisteredModelProperties(
        workspace_url="https://test.cloud.databricks.com",
        registered_model=UnityCatalogRegisteredModel(
            catalog_name="catalog", schema_name="schema", name=name, comment=comment
        ),
        adopt_existing=adopt_existing,
    )


@patch("databricks_cdk.resources.unity_catalog.registered_models.get_workspace_client")
@patch("databricks_cdk.resources.unity_catalog.registered_models.update_unity_catalog_registered_model")
@patch("databricks_cdk.resources.unity_catalog.registered_models.create_unity_catalog_registered_model")
def test_create_or_update_creates_without_physical_id(
    patched_create, patched_update, patched_get_workspace_client, workspace_client
):
    patched_get_workspace_client.return_value = workspace_client
    properties = _properties()

    create_or_update_unity_catalog_registered_model(properties, physical_resource_id=None)

    patched_create.assert_called_once_with(properties, workspace_client)
    patched_update.assert_not_called()


@patch("databricks_cdk.resources.unity_catalog.registered_models.get_workspace_client")
@patch("databricks_cdk.resources.unity_catalog.registered_models.update_unity_catalog_registered_model")
@patch("databricks_cdk.resources.unity_catalog.registered_models.create_unity_catalog_registered_model")
def test_create_or_update_updates_same_model(
    patched_create, patched_update, patched_get_workspace_client, workspace_client
):
    patched_get_workspace_client.return_value = workspace_client
    properties = _properties()

    create_or_update_unity_catalog_registered_model(properties, physical_resource_id="catalog.schema.model")

    patched_update.assert_called_once_with(properties, workspace_client)
    patched_create.assert_not_called()


@patch("databricks_cdk.resources.unity_catalog.registered_models.get_workspace_client")
@patch("databricks_cdk.resources.unity_catalog.registered_models.update_unity_catalog_registered_model")
@patch("databricks_cdk.resources.unity_catalog.registered_models.create_unity_catalog_registered_model")
def test_create_or_update_creates_new_model_when_name_changes(
    patched_create, patched_update, patched_get_workspace_client, workspace_client
):
    patched_get_workspace_client.return_value = workspace_client
    properties = _properties(name="new_model")

    create_or_update_unity_catalog_registered_model(properties, physical_resource_id="catalog.schema.model")

    patched_create.assert_called_once_with(properties, workspace_client)
    patched_update.assert_not_called()


def test_create(workspace_client):
    workspace_client.registered_models.create.return_value = RegisteredModelInfo(full_name="catalog.schema.model")

    response = create_unity_catalog_registered_model(_properties(), workspace_client)

    assert response == UnityCatalogRegisteredModelResponse(
        full_name="catalog.schema.model", physical_resource_id="catalog.schema.model"
    )
    workspace_client.registered_models.create.assert_called_once_with(
        catalog_name="catalog",
        schema_name="schema",
        name="model",
        comment="some comment",
        storage_location=None,
    )


def test_create_without_full_name_raises(workspace_client):
    workspace_client.registered_models.create.return_value = RegisteredModelInfo(full_name=None)

    with pytest.raises(RegisteredModelCreationError):
        create_unity_catalog_registered_model(_properties(), workspace_client)


def test_create_existing_model_fails_by_default(workspace_client):
    workspace_client.registered_models.create.side_effect = ResourceAlreadyExists("exists")

    with pytest.raises(RegisteredModelCreationError, match="adopt_existing"):
        create_unity_catalog_registered_model(_properties(), workspace_client)

    workspace_client.registered_models.update.assert_not_called()


def test_adopt_existing_is_parsed_from_cloudformation_string():
    # CloudFormation sends every custom resource property as a string.
    properties = UnityCatalogRegisteredModelProperties(
        workspace_url="https://test.cloud.databricks.com",
        registered_model={"catalog_name": "catalog", "schema_name": "schema", "name": "model"},
        adopt_existing="true",
    )
    assert properties.adopt_existing is True


def test_create_adopts_existing_model(workspace_client):
    workspace_client.registered_models.create.side_effect = ResourceAlreadyExists("exists")
    workspace_client.registered_models.get.return_value = RegisteredModelInfo(full_name="catalog.schema.model")

    response = create_unity_catalog_registered_model(_properties(adopt_existing=True), workspace_client)

    assert response == UnityCatalogRegisteredModelResponse(
        full_name="catalog.schema.model", physical_resource_id="catalog.schema.model"
    )
    workspace_client.registered_models.update.assert_called_once_with(
        full_name="catalog.schema.model", comment="some comment"
    )


def test_update(workspace_client):
    workspace_client.registered_models.get.return_value = RegisteredModelInfo(full_name="catalog.schema.model")

    response = update_unity_catalog_registered_model(_properties(), workspace_client)

    assert response == UnityCatalogRegisteredModelResponse(
        full_name="catalog.schema.model", physical_resource_id="catalog.schema.model"
    )
    workspace_client.registered_models.get.assert_called_once_with(full_name="catalog.schema.model")
    workspace_client.registered_models.update.assert_called_once_with(
        full_name="catalog.schema.model", comment="some comment"
    )


def test_update_clears_removed_comment(workspace_client):
    workspace_client.registered_models.get.return_value = RegisteredModelInfo(full_name="catalog.schema.model")

    update_unity_catalog_registered_model(_properties(comment=None), workspace_client)

    workspace_client.registered_models.update.assert_called_once_with(full_name="catalog.schema.model", comment="")


def test_update_missing_model_raises(workspace_client):
    workspace_client.registered_models.get.side_effect = NotFound("missing")

    with pytest.raises(RegisteredModelCreationError):
        update_unity_catalog_registered_model(_properties(), workspace_client)

    workspace_client.registered_models.update.assert_not_called()


@patch("databricks_cdk.resources.unity_catalog.registered_models.get_workspace_client")
def test_delete(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client

    response = delete_unity_catalog_registered_model(_properties(), "catalog.schema.model")

    assert response == CnfResponse(physical_resource_id="catalog.schema.model")
    workspace_client.registered_models.delete.assert_called_once_with(full_name="catalog.schema.model")


@patch("databricks_cdk.resources.unity_catalog.registered_models.get_workspace_client")
def test_delete_missing_model_does_not_raise(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    workspace_client.registered_models.delete.side_effect = NotFound("missing")

    response = delete_unity_catalog_registered_model(_properties(), "catalog.schema.model")

    assert response == CnfResponse(physical_resource_id="catalog.schema.model")


@patch("databricks_cdk.resources.unity_catalog.registered_models.get_workspace_client")
def test_delete_skips_placeholder_id_after_failed_create(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    placeholder_id = "2026/11/11/[$LATEST]0123456789abcdef"

    response = delete_unity_catalog_registered_model(_properties(), placeholder_id)

    assert response == CnfResponse(physical_resource_id=placeholder_id)
    workspace_client.registered_models.delete.assert_not_called()


def _with_current_tags(workspace_client, tags: dict[str, str]):
    workspace_client.api_client = MagicMock()
    workspace_client.api_client.do.return_value = {
        "registered_model": {"name": "catalog.schema.model", "tags": [{"key": k, "value": v} for k, v in tags.items()]}
    }
    return workspace_client.api_client.do


def test_sync_tags_none_leaves_tags_alone(workspace_client):
    do = _with_current_tags(workspace_client, {"team": "ds"})

    sync_registered_model_tags(workspace_client, "catalog.schema.model", None)

    do.assert_not_called()


def test_sync_tags_sets_changed_and_removes_missing(workspace_client):
    do = _with_current_tags(workspace_client, {"team": "ds", "old": "x", "env": "staging"})

    sync_registered_model_tags(
        workspace_client,
        "catalog.schema.model",
        [
            RegisteredModelTag(key="team", value="ds"),
            RegisteredModelTag(key="env", value="live"),
            RegisteredModelTag(key="new", value="y"),
        ],
    )

    assert do.call_args_list == [
        call("GET", "/api/2.0/mlflow/unity-catalog/registered-models/get", query={"name": "catalog.schema.model"}),
        call(
            "DELETE",
            "/api/2.0/mlflow/unity-catalog/registered-models/delete-tag",
            body={"name": "catalog.schema.model", "key": "old"},
        ),
        call(
            "POST",
            "/api/2.0/mlflow/unity-catalog/registered-models/set-tag",
            body={"name": "catalog.schema.model", "key": "env", "value": "live"},
        ),
        call(
            "POST",
            "/api/2.0/mlflow/unity-catalog/registered-models/set-tag",
            body={"name": "catalog.schema.model", "key": "new", "value": "y"},
        ),
    ]


def test_sync_tags_empty_list_removes_all(workspace_client):
    do = _with_current_tags(workspace_client, {"team": "ds"})

    sync_registered_model_tags(workspace_client, "catalog.schema.model", [])

    do.assert_any_call(
        "DELETE",
        "/api/2.0/mlflow/unity-catalog/registered-models/delete-tag",
        body={"name": "catalog.schema.model", "key": "team"},
    )
    assert do.call_count == 2


def test_create_sets_tags(workspace_client):
    do = _with_current_tags(workspace_client, {})
    workspace_client.registered_models.create.return_value = RegisteredModelInfo(full_name="catalog.schema.model")
    properties = _properties()
    properties.registered_model.tags = [RegisteredModelTag(key="team", value="ds")]

    create_unity_catalog_registered_model(properties, workspace_client)

    do.assert_any_call(
        "POST",
        "/api/2.0/mlflow/unity-catalog/registered-models/set-tag",
        body={"name": "catalog.schema.model", "key": "team", "value": "ds"},
    )


def test_update_syncs_tags(workspace_client):
    do = _with_current_tags(workspace_client, {"team": "old"})
    workspace_client.registered_models.get.return_value = RegisteredModelInfo(full_name="catalog.schema.model")
    properties = _properties()
    properties.registered_model.tags = [RegisteredModelTag(key="team", value="ds")]

    update_unity_catalog_registered_model(properties, workspace_client)

    do.assert_any_call(
        "POST",
        "/api/2.0/mlflow/unity-catalog/registered-models/set-tag",
        body={"name": "catalog.schema.model", "key": "team", "value": "ds"},
    )


@patch("databricks_cdk.resources.unity_catalog.registered_models.get_workspace_client")
def test_delete_model_with_versions_fails_clearly(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    workspace_client.model_versions.list.return_value = iter([ModelVersionInfo(version=1)])

    with pytest.raises(RegisteredModelDeletionError, match="still has model versions"):
        delete_unity_catalog_registered_model(_properties(), "catalog.schema.model")

    workspace_client.registered_models.delete.assert_not_called()


@patch("databricks_cdk.resources.unity_catalog.registered_models.get_workspace_client")
def test_delete_model_already_gone_does_not_raise(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    workspace_client.model_versions.list.side_effect = NotFound("missing")

    response = delete_unity_catalog_registered_model(_properties(), "catalog.schema.model")

    assert response == CnfResponse(physical_resource_id="catalog.schema.model")
    workspace_client.registered_models.delete.assert_not_called()
