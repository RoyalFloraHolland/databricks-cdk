import logging
from enum import StrEnum
from typing import Any, cast

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound, ResourceConflict
from pydantic import BaseModel, root_validator, validator

from databricks_cdk.utils import CnfResponse, get_workspace_client

logger = logging.getLogger(__name__)

# The pinned SDK only knows the legacy served_models format, which can't serve Unity Catalog models,
# so this talks to the REST API directly: https://docs.databricks.com/api/workspace/servingendpoints
SERVING_ENDPOINTS_API = "/api/2.0/serving-endpoints"
UC_MODELS_API = "/api/2.1/unity-catalog/models"


class ServingEndpointError(Exception):
    pass


class EndpointUpdateInProgressError(ServingEndpointError):
    def __init__(self, name: str):
        super().__init__(
            f"Serving endpoint {name} is already being updated. Wait for that update to finish and deploy again"
        )


class WorkloadSize(StrEnum):
    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"


class WorkloadType(StrEnum):
    CPU = "CPU"
    GPU_SMALL = "GPU_SMALL"
    GPU_MEDIUM = "GPU_MEDIUM"
    GPU_LARGE = "GPU_LARGE"
    MULTIGPU_MEDIUM = "MULTIGPU_MEDIUM"


class ConfigUpdateState(StrEnum):
    NOT_UPDATING = "NOT_UPDATING"
    IN_PROGRESS = "IN_PROGRESS"
    UPDATE_FAILED = "UPDATE_FAILED"
    UPDATE_CANCELED = "UPDATE_CANCELED"


class EndpointTag(BaseModel):
    key: str
    value: str = ""


class ServedEntityConfig(BaseModel):
    name: str
    entity_name: str
    entity_version: str | None = None
    # str instead of the enums, so endpoints configured outside CDK still parse
    workload_size: str | None = None
    workload_type: str | None = None
    scale_to_zero_enabled: bool = False
    environment_vars: dict[str, str] | None = None

    @validator("environment_vars")
    def empty_is_none(cls, value):
        return value or None

    def same_deployment(self, other: "ServedEntityConfig") -> bool:
        return self.dict(exclude={"name"}) == other.dict(exclude={"name"})


class Route(BaseModel):
    served_model_name: str
    traffic_percentage: int = 100


class TrafficConfig(BaseModel):
    routes: list[Route]


class EndpointConfig(BaseModel):
    served_entities: list[ServedEntityConfig] = []
    traffic_config: TrafficConfig | None = None

    @classmethod
    def serving(cls, entity: ServedEntityConfig) -> "EndpointConfig":
        return cls(
            served_entities=[entity], traffic_config=TrafficConfig(routes=[Route(served_model_name=entity.name)])
        )


class EndpointState(BaseModel):
    # str keeps states Databricks adds later from failing the deploy
    config_update: ConfigUpdateState | str | None = None


class ServingEndpointDetails(BaseModel):
    name: str
    state: EndpointState = EndpointState()
    config: EndpointConfig | None = None
    pending_config: EndpointConfig | None = None
    tags: list[EndpointTag] = []

    @property
    def is_updating(self) -> bool:
        return self.state.config_update == ConfigUpdateState.IN_PROGRESS

    @property
    def target_entity(self) -> ServedEntityConfig | None:
        # While an update runs (also the first one, when config is still empty) the target is in pending_config.
        config = self.pending_config if self.is_updating and self.pending_config else self.config
        return config.served_entities[0] if config and config.served_entities else None


class CreateServingEndpointRequest(BaseModel):
    name: str
    config: EndpointConfig
    tags: list[EndpointTag] | None = None


class PatchTagsRequest(BaseModel):
    add_tags: list[EndpointTag]
    delete_tags: list[str]

    @classmethod
    def between(cls, current: list[EndpointTag], desired: list[EndpointTag]) -> "PatchTagsRequest":
        current_values = {t.key: t.value for t in current}
        return cls(
            add_tags=[t for t in desired if current_values.get(t.key) != t.value],
            delete_tags=sorted(current_values.keys() - {t.key for t in desired}),
        )

    @property
    def is_empty(self) -> bool:
        return not self.add_tags and not self.delete_tags


class ModelVersionByAlias(BaseModel):
    version: str


class ServedEntity(BaseModel):
    entity_name: str
    entity_version: str | None = None
    alias: str | None = None
    workload_size: WorkloadSize = WorkloadSize.SMALL
    workload_type: WorkloadType = WorkloadType.CPU
    scale_to_zero_enabled: bool = False
    environment_vars: dict[str, str] | None = None

    @root_validator(skip_on_failure=True)
    def one_of_version_or_alias(cls, values):
        if (values.get("entity_version") is None) == (values.get("alias") is None):
            raise ValueError("Set exactly one of entity_version or alias")
        return values

    def to_config(self, version: str) -> ServedEntityConfig:
        return ServedEntityConfig(
            name=self.entity_name.split(".")[-1],
            entity_name=self.entity_name,
            entity_version=version,
            workload_size=self.workload_size,
            workload_type=self.workload_type,
            scale_to_zero_enabled=self.scale_to_zero_enabled,
            environment_vars=self.environment_vars,
        )


class ServingEndpointProperties(BaseModel):
    workspace_url: str
    name: str
    served_entity: ServedEntity
    # None leaves the endpoint's tags alone. A list (also an empty one) makes the endpoint have exactly these tags.
    tags: list[EndpointTag] | None = None
    adopt_existing: bool = False


class ServingEndpointResponse(CnfResponse):
    name: str
    entity_version: str


def create_or_update_serving_endpoint(
    properties: ServingEndpointProperties, physical_resource_id: str | None = None
) -> ServingEndpointResponse:
    """
    Doesn't wait for the endpoint to be ready: Databricks keeps serving the previous config until the new one is up.

    With an alias, the version is only resolved on create or when the served model changes, so a pipeline can
    promote versions without CDK reverting them.
    """
    workspace_client = get_workspace_client(properties.workspace_url)
    existing = get_serving_endpoint(workspace_client, properties.name)

    if physical_resource_id != properties.name:
        if existing is None:
            return create_serving_endpoint(properties, workspace_client)
        if not properties.adopt_existing:
            raise ServingEndpointError(
                f"Serving endpoint {properties.name} already exists. Set adopt_existing to manage it with CDK"
            )
        logger.warning(f"Serving endpoint {properties.name} already exists, adopting it")

    if existing is None:
        raise ServingEndpointError(f"Serving endpoint {properties.name} not found, make sure it's managed by CDK")

    return update_serving_endpoint(properties, workspace_client, existing)


def _get(workspace_client: WorkspaceClient, path: str) -> dict[str, Any]:
    # api_client.do only returns a stream for raw requests, these are all JSON
    return cast(dict[str, Any], workspace_client.api_client.do("GET", path))


def get_serving_endpoint(workspace_client: WorkspaceClient, name: str) -> ServingEndpointDetails | None:
    try:
        return ServingEndpointDetails.parse_obj(_get(workspace_client, f"{SERVING_ENDPOINTS_API}/{name}"))
    except NotFound:
        return None


def resolve_alias(workspace_client: WorkspaceClient, entity_name: str, alias: str) -> str:
    response = _get(workspace_client, f"{UC_MODELS_API}/{entity_name}/aliases/{alias}")
    return ModelVersionByAlias.parse_obj(response).version


def create_serving_endpoint(
    properties: ServingEndpointProperties, workspace_client: WorkspaceClient
) -> ServingEndpointResponse:
    version = _version_to_serve(workspace_client, properties.served_entity, current=None)
    request = CreateServingEndpointRequest(
        name=properties.name,
        config=EndpointConfig.serving(properties.served_entity.to_config(version)),
        tags=properties.tags,
    )
    workspace_client.api_client.do("POST", SERVING_ENDPOINTS_API, body=request.dict(exclude_none=True))

    return ServingEndpointResponse(name=properties.name, entity_version=version, physical_resource_id=properties.name)


def update_serving_endpoint(
    properties: ServingEndpointProperties, workspace_client: WorkspaceClient, existing: ServingEndpointDetails
) -> ServingEndpointResponse:
    current = existing.target_entity
    version = _version_to_serve(workspace_client, properties.served_entity, current)
    desired = properties.served_entity.to_config(version)

    # Every config update restarts the serving containers, so only send one when something changed.
    if current is None or not current.same_deployment(desired):
        _apply_config(workspace_client, existing, desired)

    if properties.tags is not None:
        sync_serving_endpoint_tags(workspace_client, properties.name, existing.tags, properties.tags)

    return ServingEndpointResponse(name=properties.name, entity_version=version, physical_resource_id=properties.name)


def _version_to_serve(
    workspace_client: WorkspaceClient, served_entity: ServedEntity, current: ServedEntityConfig | None
) -> str:
    if served_entity.entity_version is not None:
        return served_entity.entity_version
    if current and current.entity_name == served_entity.entity_name and current.entity_version is not None:
        return current.entity_version
    if served_entity.alias is None:
        raise ServingEndpointError("Set exactly one of entity_version or alias")
    return resolve_alias(workspace_client, served_entity.entity_name, served_entity.alias)


def _apply_config(
    workspace_client: WorkspaceClient, existing: ServingEndpointDetails, desired: ServedEntityConfig
) -> None:
    if existing.is_updating:
        raise EndpointUpdateInProgressError(existing.name)
    try:
        workspace_client.api_client.do(
            "PUT",
            f"{SERVING_ENDPOINTS_API}/{existing.name}/config",
            body=EndpointConfig.serving(desired).dict(exclude_none=True),
        )
    except ResourceConflict as e:
        raise EndpointUpdateInProgressError(existing.name) from e


def sync_serving_endpoint_tags(
    workspace_client: WorkspaceClient, name: str, current: list[EndpointTag], desired: list[EndpointTag]
) -> None:
    request = PatchTagsRequest.between(current, desired)
    if not request.is_empty:
        workspace_client.api_client.do("PATCH", f"{SERVING_ENDPOINTS_API}/{name}/tags", body=request.dict())


def delete_serving_endpoint(properties: ServingEndpointProperties, physical_resource_id: str) -> CnfResponse:
    if physical_resource_id != properties.name:
        # After a failed create, CloudFormation rolls back with a placeholder id (the log stream name),
        # so there is no endpoint to delete.
        logger.warning(f"Physical resource id {physical_resource_id} is not a serving endpoint, skipping delete")
        return CnfResponse(physical_resource_id=physical_resource_id)

    workspace_client = get_workspace_client(properties.workspace_url)
    try:
        workspace_client.api_client.do("DELETE", f"{SERVING_ENDPOINTS_API}/{physical_resource_id}")
    except NotFound:
        logger.warning("Serving endpoint not found, never existed or already removed")

    return CnfResponse(physical_resource_id=physical_resource_id)
