from databricks.sdk.service.ml import ExperimentTag
from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, get_workspace_client


class ExperimentIdNoneError(Exception):
    pass


class ExperimentProperties(BaseModel):
    name: str
    artifact_location: str | None = None
    workspace_url: str
    description: str | None = None


class ExperimentCreateResponse(CnfResponse):
    physical_resource_id: str
    name: str


def create_or_update_experiment(properties: ExperimentProperties, physical_resource_id: str | None = None):
    """
    Creates a new experiment if there is no physical_resource_id provided, else it checks if based on the
    ExperimentProperties the experiment can be updated


    :param properties: Properties of an mlflow experiment
    :param physical_resource_id: CDK physical resource id which is 1 on 1 mapped to experiment_id,
        defaults to None
    :return: Both the physical_resouce_id (experiment_id) and the name of the experiment
    """
    workspace_client = get_workspace_client(properties.workspace_url)

    description_tag = ExperimentTag(key="mlflow.note.content", value=properties.description)
    if not physical_resource_id:
        response = workspace_client.experiments.create_experiment(
            name=properties.name, artifact_location=properties.artifact_location, tags=[description_tag]
        )
        return (
            ExperimentCreateResponse(name=properties.name, physical_resource_id=response.experiment_id)
            if response.experiment_id is not None
            else ExperimentIdNoneError("Experiment ID is None")
        )

    existing_experiment = workspace_client.experiments.get_experiment(experiment_id=physical_resource_id)

    if existing_experiment.experiment is None:
        raise ExperimentIdNoneError("Existing experiment cannot be found but physical_resouce_id is provided")

    if existing_experiment.experiment.name != properties.name:
        workspace_client.experiments.update_experiment(experiment_id=physical_resource_id, new_name=properties.name)

    existing_tags = existing_experiment.experiment.tags
    if existing_tags is not None and properties.description is not None and properties.description not in existing_tags:
        workspace_client.experiments.set_experiment_tag(
            experiment_id=physical_resource_id, key="mlflow.note.content", value=properties.description
        )

    return ExperimentCreateResponse(name=properties.name, physical_resource_id=physical_resource_id)


def delete_experiment(properties: ExperimentProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes an existing mlflow experiment"""
    workspace_client = get_workspace_client(properties.workspace_url)
    workspace_client.experiments.delete_experiment(experiment_id=physical_resource_id)
    return CnfResponse(physical_resource_id=physical_resource_id)
