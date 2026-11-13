from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest
from databricks.sdk.errors import NotFound, ResourceConflict
from pydantic import ValidationError

from databricks_cdk.resources.serving.serving_endpoints import (
    EndpointTag,
    PatchTagsRequest,
    ServingEndpointError,
    ServingEndpointProperties,
    ServingEndpointResponse,
    WorkloadSize,
    WorkloadType,
    create_or_update_serving_endpoint,
    delete_serving_endpoint,
    sync_serving_endpoint_tags,
)
from databricks_cdk.utils import CnfResponse


def _properties(**served_entity) -> ServingEndpointProperties:
    entity = {"entity_name": "catalog.schema.model", "alias": "champion", **served_entity}
    return ServingEndpointProperties(
        workspace_url="https://test.cloud.databricks.com", name="endpoint", served_entity=entity
    )


def _existing(entity_version="3", workload_size="Small", config_update="NOT_UPDATING", tags=None) -> dict[str, Any]:
    return {
        "name": "endpoint",
        "state": {"ready": "READY", "config_update": config_update},
        "config": {
            "served_entities": [
                {
                    "name": "model",
                    "entity_name": "catalog.schema.model",
                    "entity_version": entity_version,
                    "workload_size": workload_size,
                    "workload_type": "CPU",
                    "scale_to_zero_enabled": False,
                }
            ]
        },
        "tags": tags or [],
    }


def _api(
    workspace_client,
    existing: dict[str, Any] | None = None,
    alias_version: str = "7",
    put_error: Exception | None = None,
):
    """Fake REST API: the endpoint GET returns `existing` (or 404), the alias lookup returns `alias_version`."""

    def do(method, path, query=None, body=None):
        if method == "GET" and path == "/api/2.0/serving-endpoints/endpoint":
            if existing is None:
                raise NotFound("missing")
            return existing
        if method == "GET" and path == "/api/2.1/unity-catalog/models/catalog.schema.model/aliases/champion":
            return {"version": int(alias_version)}
        if method == "PUT" and put_error is not None:
            raise put_error
        return {}

    workspace_client.api_client = MagicMock()
    workspace_client.api_client.do.side_effect = do
    return workspace_client.api_client.do


def _config(version: str, workload_size: str = "Small") -> dict[str, Any]:
    return {
        "served_entities": [
            {
                "name": "model",
                "entity_name": "catalog.schema.model",
                "entity_version": version,
                "workload_size": workload_size,
                "workload_type": "CPU",
                "scale_to_zero_enabled": False,
            }
        ],
        "traffic_config": {"routes": [{"served_model_name": "model", "traffic_percentage": 100}]},
    }


def test_requires_exactly_one_of_version_or_alias():
    with pytest.raises(ValidationError):
        _properties(alias=None)
    with pytest.raises(ValidationError):
        _properties(entity_version="1")


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_create_resolves_alias(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    do = _api(workspace_client, existing=None, alias_version="7")
    properties = _properties()
    properties.tags = [EndpointTag(key="team", value="ds")]

    response = create_or_update_serving_endpoint(properties, None)

    assert response == ServingEndpointResponse(name="endpoint", entity_version="7", physical_resource_id="endpoint")
    do.assert_any_call(
        "POST",
        "/api/2.0/serving-endpoints",
        body={"name": "endpoint", "config": _config("7"), "tags": [{"key": "team", "value": "ds"}]},
    )


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_create_with_pinned_version_skips_alias(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    do = _api(workspace_client, existing=None)

    create_or_update_serving_endpoint(_properties(alias=None, entity_version="2"), None)

    paths = [c.args[1] for c in do.call_args_list]
    assert "/api/2.1/unity-catalog/models/catalog.schema.model/aliases/champion" not in paths
    do.assert_any_call("POST", "/api/2.0/serving-endpoints", body={"name": "endpoint", "config": _config("2")})


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_create_existing_endpoint_fails_without_adopt(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    _api(workspace_client, existing=_existing())

    with pytest.raises(ServingEndpointError, match="adopt_existing"):
        create_or_update_serving_endpoint(_properties(), None)


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_create_adopts_existing_endpoint_and_keeps_its_version(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    do = _api(workspace_client, existing=_existing(entity_version="3"))
    properties = _properties(workload_size="Medium")
    properties.adopt_existing = True

    response = create_or_update_serving_endpoint(properties, None)

    assert response.entity_version == "3"
    do.assert_any_call("PUT", "/api/2.0/serving-endpoints/endpoint/config", body=_config("3", "Medium"))


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_update_without_changes_does_not_restart_endpoint(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    do = _api(workspace_client, existing=_existing(entity_version="3"), alias_version="9")

    response = create_or_update_serving_endpoint(_properties(), "endpoint")

    # The alias points to 9, but the pipeline deployed 3: CDK keeps 3 and sends nothing.
    assert response.entity_version == "3"
    assert [c.args[0] for c in do.call_args_list] == ["GET"]


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_update_workload_keeps_served_version(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    do = _api(workspace_client, existing=_existing(entity_version="3"))

    create_or_update_serving_endpoint(_properties(workload_size="Medium"), "endpoint")

    do.assert_any_call("PUT", "/api/2.0/serving-endpoints/endpoint/config", body=_config("3", "Medium"))


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_update_pinned_version(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    do = _api(workspace_client, existing=_existing(entity_version="3"))

    create_or_update_serving_endpoint(_properties(alias=None, entity_version="4"), "endpoint")

    do.assert_any_call("PUT", "/api/2.0/serving-endpoints/endpoint/config", body=_config("4"))


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_update_to_another_model_resolves_alias(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    existing = _existing(entity_version="3")
    existing["config"]["served_entities"][0]["entity_name"] = "catalog.schema.old_model"
    do = _api(workspace_client, existing=existing, alias_version="7")

    response = create_or_update_serving_endpoint(_properties(), "endpoint")

    assert response.entity_version == "7"
    do.assert_any_call("PUT", "/api/2.0/serving-endpoints/endpoint/config", body=_config("7"))


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_update_while_endpoint_is_updating_fails(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    do = _api(workspace_client, existing=_existing(config_update="IN_PROGRESS"))

    with pytest.raises(ServingEndpointError, match="already being updated"):
        create_or_update_serving_endpoint(_properties(workload_size="Medium"), "endpoint")

    assert "PUT" not in [c.args[0] for c in do.call_args_list]


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_update_conflict_gives_clear_error(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    _api(workspace_client, existing=_existing(), put_error=ResourceConflict("conflict"))

    with pytest.raises(ServingEndpointError, match="already being updated"):
        create_or_update_serving_endpoint(_properties(workload_size="Medium"), "endpoint")


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_update_missing_endpoint_fails(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    _api(workspace_client, existing=None)

    with pytest.raises(ServingEndpointError, match="not found"):
        create_or_update_serving_endpoint(_properties(), "endpoint")


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_update_without_tags_leaves_tags_alone(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    do = _api(workspace_client, existing=_existing(tags=[{"key": "team", "value": "ds"}]))

    create_or_update_serving_endpoint(_properties(), "endpoint")

    assert "PATCH" not in [c.args[0] for c in do.call_args_list]


def test_patch_tags_between():
    request = PatchTagsRequest.between(
        current=[EndpointTag(key="team", value="ds"), EndpointTag(key="old", value="x")],
        desired=[EndpointTag(key="team", value="ds"), EndpointTag(key="env", value="live")],
    )

    assert request == PatchTagsRequest(add_tags=[EndpointTag(key="env", value="live")], delete_tags=["old"])
    assert not request.is_empty
    assert PatchTagsRequest.between(
        [EndpointTag(key="team", value="ds")], [EndpointTag(key="team", value="ds")]
    ).is_empty


def test_sync_tags_adds_changed_and_removes_missing(workspace_client):
    workspace_client.api_client = MagicMock()
    current = [
        EndpointTag(key="team", value="ds"),
        EndpointTag(key="env", value="staging"),
        EndpointTag(key="old", value="x"),
    ]

    sync_serving_endpoint_tags(
        workspace_client,
        "endpoint",
        current,
        [EndpointTag(key="team", value="ds"), EndpointTag(key="env", value="live")],
    )

    assert workspace_client.api_client.do.call_args_list == [
        call(
            "PATCH",
            "/api/2.0/serving-endpoints/endpoint/tags",
            body={"add_tags": [{"key": "env", "value": "live"}], "delete_tags": ["old"]},
        )
    ]


def test_sync_tags_without_changes_sends_nothing(workspace_client):
    workspace_client.api_client = MagicMock()

    sync_serving_endpoint_tags(
        workspace_client, "endpoint", [EndpointTag(key="team", value="ds")], [EndpointTag(key="team", value="ds")]
    )

    workspace_client.api_client.do.assert_not_called()


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_delete(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    workspace_client.api_client = MagicMock()

    response = delete_serving_endpoint(_properties(), "endpoint")

    assert response == CnfResponse(physical_resource_id="endpoint")
    workspace_client.api_client.do.assert_called_once_with("DELETE", "/api/2.0/serving-endpoints/endpoint")


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_delete_missing_endpoint_does_not_raise(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    workspace_client.api_client = MagicMock()
    workspace_client.api_client.do.side_effect = NotFound("missing")

    response = delete_serving_endpoint(_properties(), "endpoint")

    assert response == CnfResponse(physical_resource_id="endpoint")


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_delete_skips_placeholder_id_after_failed_create(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    workspace_client.api_client = MagicMock()

    response = delete_serving_endpoint(_properties(), "2026/11/13/[$LATEST]0123456789abcdef")

    assert response == CnfResponse(physical_resource_id="2026/11/13/[$LATEST]0123456789abcdef")
    workspace_client.api_client.do.assert_not_called()


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_update_matching_pending_config_is_a_no_op(patched_get_workspace_client, workspace_client):
    # During the first rollout config is still empty and the target is in pending_config. A deploy (or a
    # CloudFormation rollback) asking for that same target must not fail.
    patched_get_workspace_client.return_value = workspace_client
    existing = _existing(entity_version="1", config_update="IN_PROGRESS")
    existing["pending_config"] = existing.pop("config")
    existing["config"] = {}
    do = _api(workspace_client, existing=existing, alias_version="1")

    response = create_or_update_serving_endpoint(_properties(), "endpoint")

    assert response.entity_version == "1"
    assert [c.args[0] for c in do.call_args_list] == ["GET"]


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_update_differing_from_pending_config_fails(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    existing = _existing(entity_version="1", config_update="IN_PROGRESS")
    existing["pending_config"] = existing.pop("config")
    existing["config"] = {}
    _api(workspace_client, existing=existing)

    with pytest.raises(ServingEndpointError, match="already being updated"):
        create_or_update_serving_endpoint(_properties(workload_size="Medium"), "endpoint")


def test_workload_fields_are_validated():
    entity = _properties(workload_size="Medium", workload_type="GPU_SMALL").served_entity
    assert entity.workload_size is WorkloadSize.MEDIUM
    assert entity.workload_type is WorkloadType.GPU_SMALL

    with pytest.raises(ValidationError):
        _properties(workload_size="Huge")
    with pytest.raises(ValidationError):
        _properties(workload_type="TPU")


@patch("databricks_cdk.resources.serving.serving_endpoints.get_workspace_client")
def test_unknown_config_update_state_is_not_treated_as_in_progress(patched_get_workspace_client, workspace_client):
    patched_get_workspace_client.return_value = workspace_client
    do = _api(workspace_client, existing=_existing(config_update="SOME_NEW_STATE"))

    create_or_update_serving_endpoint(_properties(workload_size="Medium"), "endpoint")

    do.assert_any_call("PUT", "/api/2.0/serving-endpoints/endpoint/config", body=_config("3", "Medium"))
