import logging

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import AlreadyExists, NotFound, ResourceAlreadyExists
from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, get_workspace_client

logger = logging.getLogger(__name__)

# Model tags are not in the Unity Catalog API, so they go through MLflow's Unity Catalog endpoints.
# See https://docs.databricks.com/database-objects/tags and
# https://github.com/mlflow/mlflow/blob/master/mlflow/store/_unity_catalog/registry/rest_store.py
MLFLOW_UC_MODELS_API = "/api/2.0/mlflow/unity-catalog/registered-models"


class RegisteredModelCreationError(Exception):
    pass


class RegisteredModelDeletionError(Exception):
    pass


class RegisteredModelTag(BaseModel):
    key: str
    value: str = ""


class MlflowRegisteredModel(BaseModel):
    tags: list[RegisteredModelTag] = []


class MlflowGetRegisteredModelResponse(BaseModel):
    registered_model: MlflowRegisteredModel = MlflowRegisteredModel()


class UnityCatalogRegisteredModel(BaseModel):
    name: str
    catalog_name: str
    schema_name: str
    comment: str | None = None
    storage_location: str | None = None
    # None leaves the model's tags alone. A list (also an empty one) makes the model have exactly these tags.
    tags: list[RegisteredModelTag] | None = None

    @property
    def full_name(self) -> str:
        return f"{self.catalog_name}.{self.schema_name}.{self.name}"


class UnityCatalogRegisteredModelProperties(BaseModel):
    workspace_url: str
    registered_model: UnityCatalogRegisteredModel
    # Off by default, so a typo or a name used by another project can't silently bring that model under this stack.
    adopt_existing: bool = False


class UnityCatalogRegisteredModelResponse(CnfResponse):
    full_name: str


def create_or_update_unity_catalog_registered_model(
    properties: UnityCatalogRegisteredModelProperties, physical_resource_id: str | None = None
) -> UnityCatalogRegisteredModelResponse:
    # Renaming in place isn't supported (the pinned SDK sends the wrong field), so a new name creates a new model.
    workspace_client = get_workspace_client(properties.workspace_url)

    if physical_resource_id is None or physical_resource_id != properties.registered_model.full_name:
        return create_unity_catalog_registered_model(properties, workspace_client)

    return update_unity_catalog_registered_model(properties, workspace_client)


def create_unity_catalog_registered_model(
    properties: UnityCatalogRegisteredModelProperties, workspace_client: WorkspaceClient
) -> UnityCatalogRegisteredModelResponse:
    model = properties.registered_model
    try:
        created = workspace_client.registered_models.create(
            catalog_name=model.catalog_name,
            schema_name=model.schema_name,
            name=model.name,
            comment=model.comment,
            storage_location=model.storage_location,
        )
    except (AlreadyExists, ResourceAlreadyExists) as e:
        if not properties.adopt_existing:
            raise RegisteredModelCreationError(
                f"Registered model {model.full_name} already exists. Set adopt_existing to manage it with CDK"
            ) from e
        logger.warning(f"Registered model {model.full_name} already exists, adopting it")
        return update_unity_catalog_registered_model(properties, workspace_client)

    if created.full_name is None:
        raise RegisteredModelCreationError("Registered model creation failed, there was no full name returned")

    sync_registered_model_tags(workspace_client, created.full_name, model.tags)

    return UnityCatalogRegisteredModelResponse(full_name=created.full_name, physical_resource_id=created.full_name)


def update_unity_catalog_registered_model(
    properties: UnityCatalogRegisteredModelProperties, workspace_client: WorkspaceClient
) -> UnityCatalogRegisteredModelResponse:
    full_name = properties.registered_model.full_name
    try:
        workspace_client.registered_models.get(full_name=full_name)
    except NotFound as e:
        raise RegisteredModelCreationError(
            f"Registered model {full_name} not found, make sure it's managed by CDK"
        ) from e

    # The SDK leaves out a None comment, so send an empty one to clear it when it was removed from the CDK object.
    workspace_client.registered_models.update(full_name=full_name, comment=properties.registered_model.comment or "")
    sync_registered_model_tags(workspace_client, full_name, properties.registered_model.tags)

    return UnityCatalogRegisteredModelResponse(full_name=full_name, physical_resource_id=full_name)


def sync_registered_model_tags(
    workspace_client: WorkspaceClient, full_name: str, tags: list[RegisteredModelTag] | None
) -> None:
    if tags is None:
        return

    response = MlflowGetRegisteredModelResponse.parse_obj(
        workspace_client.api_client.do("GET", f"{MLFLOW_UC_MODELS_API}/get", query={"name": full_name})
    )
    current = {t.key: t.value for t in response.registered_model.tags}
    desired = {t.key: t.value for t in tags}

    for key in current.keys() - desired.keys():
        workspace_client.api_client.do(
            "DELETE", f"{MLFLOW_UC_MODELS_API}/delete-tag", body={"name": full_name, "key": key}
        )

    for key, value in desired.items():
        if current.get(key) != value:
            workspace_client.api_client.do(
                "POST", f"{MLFLOW_UC_MODELS_API}/set-tag", body={"name": full_name, "key": key, "value": value}
            )


def delete_unity_catalog_registered_model(
    properties: UnityCatalogRegisteredModelProperties, physical_resource_id: str
) -> CnfResponse:
    if physical_resource_id != properties.registered_model.full_name:
        # After a failed create, CloudFormation rolls back with a placeholder id (the log stream name),
        # so there is no model to delete.
        logger.warning(f"Physical resource id {physical_resource_id} is not a registered model, skipping delete")
        return CnfResponse(physical_resource_id=physical_resource_id)

    workspace_client = get_workspace_client(properties.workspace_url)
    try:
        if next(iter(workspace_client.model_versions.list(full_name=physical_resource_id, max_results=1)), None):
            raise RegisteredModelDeletionError(
                f"Registered model {physical_resource_id} still has model versions and Unity Catalog only deletes "
                "empty models. Delete the versions first, or use the RETAIN removal policy"
            )
        workspace_client.registered_models.delete(full_name=physical_resource_id)
    except NotFound:
        logger.warning("Registered model not found, never existed or already removed")

    return CnfResponse(physical_resource_id=physical_resource_id)
