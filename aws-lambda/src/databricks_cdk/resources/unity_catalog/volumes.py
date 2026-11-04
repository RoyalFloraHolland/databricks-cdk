import logging

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service.catalog import VolumeInfo, VolumeType
from pydantic import BaseModel

from databricks_cdk.utils import CnfResponse, get_workspace_client, wait_until_found

logger = logging.getLogger(__name__)


class VolumeCreationError(Exception):
    pass


class Volume(BaseModel):
    name: str
    catalog_name: str
    schema_name: str
    volume_type: VolumeType = VolumeType.MANAGED
    comment: str | None = None
    storage_location: str | None = None

    @property
    def full_name(self) -> str:
        """The three-level (fully qualified) name of the volume"""
        return f"{self.catalog_name}.{self.schema_name}.{self.name}"


class VolumeProperties(BaseModel):
    workspace_url: str
    volume: Volume


class VolumeResponse(CnfResponse):
    name: str


def create_or_update_volume(properties: VolumeProperties, physical_resource_id: str | None = None) -> VolumeResponse:
    """
    Create or update volume on databricks. If physical_resource_id is provided, it will update the existing volume
    else it will create a new one.
    """
    workspace_client = get_workspace_client(properties.workspace_url)

    if physical_resource_id is None:
        # volume doesn't exist yet so create new one
        return create_volume(properties, workspace_client)

    # update existing volume
    existing_volume = [
        v
        for v in workspace_client.volumes.list(
            catalog_name=properties.volume.catalog_name, schema_name=properties.volume.schema_name
        )
        if v.volume_id == physical_resource_id
    ]

    if len(existing_volume) == 0:
        raise VolumeCreationError(
            f"Volume with id {physical_resource_id} not found but id is provided, make sure it's managed by CDK"
        )

    return update_volume(properties, workspace_client, existing_volume[0], physical_resource_id)


def create_volume(properties: VolumeProperties, workspace_client: WorkspaceClient) -> VolumeResponse:
    """Create volume on databricks"""

    created_volume = workspace_client.volumes.create(
        catalog_name=properties.volume.catalog_name,
        schema_name=properties.volume.schema_name,
        name=properties.volume.name,
        volume_type=properties.volume.volume_type,
        comment=properties.volume.comment,
        storage_location=properties.volume.storage_location,
    )

    if created_volume.volume_id is None:
        raise VolumeCreationError("Volume creation failed, there was no id found")

    wait_until_found(
        lambda: workspace_client.volumes.read(full_name_arg=properties.volume.full_name),
        f"Volume {properties.volume.full_name}",
    )

    return VolumeResponse(name=properties.volume.name, physical_resource_id=created_volume.volume_id)


def update_volume(
    properties: VolumeProperties,
    workspace_client: WorkspaceClient,
    existing_volume: VolumeInfo,
    physical_resource_id: str,
) -> VolumeResponse:
    """Update volume on databricks based on physical_resource_id"""
    workspace_client.volumes.update(
        full_name_arg=existing_volume.full_name,
        name=properties.volume.name,
        comment=properties.volume.comment,
    )

    return VolumeResponse(name=properties.volume.name, physical_resource_id=physical_resource_id)


def delete_volume(properties: VolumeProperties, physical_resource_id: str) -> CnfResponse:
    """Delete a volume on databricks"""
    workspace_client = get_workspace_client(properties.workspace_url)
    try:
        workspace_client.volumes.delete(full_name_arg=properties.volume.full_name)
    except NotFound:
        logger.warning("Volume not found, never existed or already removed")

    return CnfResponse(physical_resource_id=physical_resource_id)
