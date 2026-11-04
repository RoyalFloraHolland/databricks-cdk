import json
import logging

from pydantic import BaseModel, Field

from databricks_cdk.utils import CnfResponse, delete_request, get_request, patch_request, post_request, wait_until_found

logger = logging.getLogger(__name__)


class Schema(BaseModel):
    name: str
    catalog_name: str
    comment: str | None
    properties: dict[str, str] = {}
    owner: str | None


class SchemaProperties(BaseModel):
    workspace_url: str
    schema_object: Schema = Field(alias="schema")


class SchemaResponse(CnfResponse):
    catalog_name: str
    name: str


def get_schema_url(workspace_url: str):
    """Getting url for job requests"""
    return f"{workspace_url}/api/2.1/unity-catalog/schemas"


def get_schema_by_name(catalog_name: str, schema_name: str, base_url: str) -> dict | None:
    try:
        return get_request(f"{base_url}/{catalog_name}.{schema_name}")
    except Exception as e:
        logger.info(f"Schema not found, returning None. Exception: {e}")
        return None


def create_or_update_schema(properties: SchemaProperties) -> SchemaResponse:
    """Create schema at databricks"""
    current: dict | None = None
    base_url = get_schema_url(properties.workspace_url)
    if current is None:
        current = get_schema_by_name(
            properties.schema_object.catalog_name,
            properties.schema_object.name,
            base_url=base_url,
        )
    body = json.loads(properties.schema_object.json())

    if current is None:
        post_request(
            base_url,
            params={"catalog_name": properties.schema_object.catalog_name},
            body=body,
        )
        wait_until_found(
            lambda: get_schema_by_name(
                properties.schema_object.catalog_name, properties.schema_object.name, base_url=base_url
            ),
            f"Schema {properties.schema_object.catalog_name}.{properties.schema_object.name}",
        )
    else:
        patch_request(
            f"{base_url}/{properties.schema_object.catalog_name}.{properties.schema_object.name}",
            params={"catalog_name": properties.schema_object.catalog_name},
            body=body,
        )
    return SchemaResponse(
        name=properties.schema_object.name,
        catalog_name=properties.schema_object.catalog_name,
        physical_resource_id=f"{properties.schema_object.catalog_name}/{properties.schema_object.name}",
    )


def delete_schema(properties: SchemaProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes schema at databricks"""
    base_url = get_schema_url(properties.workspace_url)
    current = get_schema_by_name(
        properties.schema_object.catalog_name,
        properties.schema_object.name,
        base_url=base_url,
    )
    if current is not None:
        delete_request(
            f"{base_url}/{properties.schema_object.catalog_name}.{properties.schema_object.name}",
            params={"catalog_name": properties.schema_object.catalog_name},
        )
    else:
        logger.warning("Already removed")
    return CnfResponse(physical_resource_id=physical_resource_id)
