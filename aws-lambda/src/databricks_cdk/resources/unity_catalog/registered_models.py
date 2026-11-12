import logging

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import AlreadyExists, NotFound, ResourceAlreadyExists
from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, get_workspace_client

logger = logging.getLogger(__name__)

# The Unity Catalog API in the pinned SDK has no model tags, so they go through MLflow's Unity Catalog endpoints.
MLFLOW_UC_MODELS_API = "/api/2.0/mlflow/unity-catalog/registered-models"


class RegisteredModelCreationError(Exception):
    pass


class RegisteredModelTag(BaseModel):
    key: str
    value: str


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
        """The three-level (fully qualified) name of the registered model"""
        return f"{self.catalog_name}.{self.schema_name}.{self.name}"


class UnityCatalogRegisteredModelProperties(BaseModel):
    workspace_url: str
    registered_model: UnityCatalogRegisteredModel
    # Take over a model that already exists instead of failing. Off by default, so a typo or a name used by another
    # project can't silently bring an existing model (and, with a DESTROY removal policy, its versions) under this stack.
    adopt_existing: bool = False


class UnityCatalogRegisteredModelResponse(CnfResponse):
    full_name: str


def create_or_update_unity_catalog_registered_model(
    properties: UnityCatalogRegisteredModelProperties, physical_resource_id: str | None = None
) -> UnityCatalogRegisteredModelResponse:
    """
    Create or update a registered model in Unity Catalog. The physical_resource_id is the model's full name.

    Only the model itself is managed here. Model versions and aliases are created by ML pipelines.

    A change of name, catalog or schema creates a new model, which CloudFormation treats as a replacement.
    Renaming in place is not supported because the pinned SDK sends the wrong field for it.
    """
    workspace_client = get_workspace_client(properties.workspace_url)

    if physical_resource_id is None or physical_resource_id != properties.registered_model.full_name:
        return create_unity_catalog_registered_model(properties, workspace_client)

    return update_unity_catalog_registered_model(properties, workspace_client)


def create_unity_catalog_registered_model(
    properties: UnityCatalogRegisteredModelProperties, workspace_client: WorkspaceClient
) -> UnityCatalogRegisteredModelResponse:
    """
    Create a registered model in Unity Catalog.
    If it already exists, it is adopted and its comment is updated when adopt_existing is set, otherwise this fails.
    """
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
    """Update the comment and tags of an existing registered model in Unity Catalog"""
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
    """
    Make the model's tags match the given list: set new and changed tags, and remove tags that are not in the list.
    Does nothing when tags is None.
    """
    if tags is None:
        return

    response = workspace_client.api_client.do("GET", f"{MLFLOW_UC_MODELS_API}/get", query={"name": full_name})
    current = {t["key"]: t.get("value", "") for t in response.get("registered_model", {}).get("tags", [])}
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
    """
    Delete a registered model in Unity Catalog, including all of its versions.

    The CDK construct retains the model by default, so this only runs when the removal policy is set to DESTROY.
    """
    if physical_resource_id != properties.registered_model.full_name:
        # After a failed create, CloudFormation rolls back with a placeholder id (the log stream name),
        # so there is no model to delete.
        logger.warning(f"Physical resource id {physical_resource_id} is not a registered model, skipping delete")
        return CnfResponse(physical_resource_id=physical_resource_id)

    workspace_client = get_workspace_client(properties.workspace_url)
    try:
        workspace_client.registered_models.delete(full_name=physical_resource_id)
    except NotFound:
        logger.warning("Registered model not found, never existed or already removed")

    return CnfResponse(physical_resource_id=physical_resource_id)
