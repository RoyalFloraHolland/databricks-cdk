from databricks.sdk import WorkspaceClient
from databricks.sdk.service.ml import ModelTag
from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, get_workspace_client


class RegisteredModelProperties(BaseModel):
    name: str
    tags: list[ModelTag] | None = []
    description: str | None
    workspace_url: str


class RegisteredModelCreateResponse(CnfResponse):
    physical_resource_id: str


def _update_registered_model_tags(
    workspace_client: WorkspaceClient,
    properties: RegisteredModelProperties,
    current_tags: list[ModelTag],
):
    """Updates the registered model tags"""
    tags_to_delete = []

    if not properties.tags:
        tags_to_delete = current_tags
    elif current_tags is not None:
        new_keys = [t.key for t in properties.tags]
        tags_to_delete = [t for t in current_tags if t.key not in new_keys]

    if tags_to_delete:
        # delete tags that are not on the cdk object anymore
        [workspace_client.model_registry.delete_model_tag(properties.name, t.key) for t in tags_to_delete]

    if properties.tags:
        # Overwrites / updates existing tags
        [
            workspace_client.model_registry.set_model_tag(properties.name, t.key, t.value)
            for t in properties.tags
            if t.key and t.value is not None
        ]


def create_or_update_registered_model(properties: RegisteredModelProperties, physical_resource_id: str | None = None):
    """
    Creates a new registered model if no physical_resource_id is provided. Otherwise, this function checks whether the
    registered model needs to be updated based on the provided properties.

    :param properties: Properties of an mlflow Registered Model
    :param physical_resource_id: CDK Physical Resource Id belonging to the Registered Model (if exists). Defaults to None
    :return:physical_resource_id of the Registered Model, which equals the name of the Registered Model
    """

    workspace_client = get_workspace_client(properties.workspace_url)

    if physical_resource_id is None:
        response = workspace_client.model_registry.create_model(
            name=properties.name, description=properties.description, tags=properties.tags
        )

        name = response.registered_model.name if response.registered_model else None
        if name is not None:
            return RegisteredModelCreateResponse(physical_resource_id=name)

    registered_model = workspace_client.model_registry.get_model(name=physical_resource_id)
    if registered_model is None:
        raise ValueError(f"Registered model cannot be found but physical_resouce_id {physical_resource_id} is provided")

    if registered_model.registered_model_databricks is not None and (
        properties.name != registered_model.registered_model_databricks.name
        or properties.description != registered_model.registered_model_databricks.description
    ):
        workspace_client.model_registry.update_model(name=properties.name, description=properties.description)
        return RegisteredModelCreateResponse(physical_resource_id=physical_resource_id)

    new_tags = properties.tags
    if properties.tags is not None:
        new_tags = sorted(new_tags, key=lambda t: t.key)

    current_tags = registered_model.tags
    if current_tags is not None:
        current_tags = sorted(current_tags, key=lambda t: t.key)

    if new_tags != current_tags:
        _update_registered_model_tags(workspace_client, properties, registered_model.tags)

    return RegisteredModelCreateResponse(physical_resource_id=physical_resource_id)


def delete_registered_model(properties: RegisteredModelProperties, physical_resource_id: str):
    """Deletes an existing registered model"""
    workspace_client = get_workspace_client(properties.workspace_url)
    workspace_client.model_registry.delete_model(name=physical_resource_id)
    return CnfResponse(physical_resource_id=physical_resource_id)
