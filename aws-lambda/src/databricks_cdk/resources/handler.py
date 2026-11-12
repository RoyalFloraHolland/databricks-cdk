import logging

import cfnresponse
from pydantic import BaseModel, ValidationError

from databricks_cdk.resources.account.credentials import (
    CredentialsProperties,
    create_or_update_credentials,
    delete_credentials,
)
from databricks_cdk.resources.account.networks import NetworksProperties, create_or_update_networks, delete_networks
from databricks_cdk.resources.account.storage_config import (
    StorageConfigProperties,
    create_or_update_storage_configuration,
    delete_storage_configuration,
)
from databricks_cdk.resources.account.workspace import (
    WorkspaceProperties,
    create_or_update_workspaces,
    delete_workspaces,
)
from databricks_cdk.resources.cluster_policies.cluster_policy import (
    ClusterPolicyProperties,
    create_or_update_cluster_policy,
    delete_cluster_policy,
)
from databricks_cdk.resources.clusters.cluster import ClusterProperties, create_or_update_cluster, delete_cluster
from databricks_cdk.resources.dbfs.dbfs_file import DbfsFileProperties, create_or_update_dbfs_file, delete_dbfs_file
from databricks_cdk.resources.groups.group import GroupProperties, create_or_update_group, delete_group
from databricks_cdk.resources.instance_pools.instance_pools import (
    InstancePoolProperties,
    create_or_update_instance_pool,
    delete_instance_pool,
)
from databricks_cdk.resources.instance_profiles.instance_profile import (
    InstanceProfileProperties,
    create_or_update_instance_profile,
    delete_instance_profile,
)
from databricks_cdk.resources.jobs.job import JobProperties, create_or_update_job, delete_job
from databricks_cdk.resources.mlflow.experiment import (
    ExperimentProperties,
    create_or_update_experiment,
    delete_experiment,
)
from databricks_cdk.resources.mlflow.registered_model import (
    RegisteredModelProperties,
    create_or_update_registered_model,
    delete_registered_model,
)
from databricks_cdk.resources.permissions.cluster_permissions import (
    ClusterPermissionsProperties,
    create_or_update_cluster_permissions,
    delete_cluster_permissions,
)
from databricks_cdk.resources.permissions.cluster_policy_permissions import (
    ClusterPolicyPermissionsProperties,
    create_or_update_cluster_policy_permissions,
    delete_cluster_policy_permissions,
)
from databricks_cdk.resources.permissions.experiment_permissions import (
    ExperimentPermissionProperties,
    create_or_update_experiment_permissions,
    delete_experiment_permissions,
)
from databricks_cdk.resources.permissions.job_permissions import (
    JobPermissionsProperties,
    create_or_update_job_permissions,
    delete_job_permissions,
)
from databricks_cdk.resources.permissions.registered_model_permissions import (
    RegisteredModelPermissionPermissionProperties,
    create_or_update_registered_model_permissions,
    delete_registered_model_permissions,
)
from databricks_cdk.resources.permissions.sql_warehouse_permissions import (
    SQLWarehousePermissionsProperties,
    create_or_update_warehouse_permissions,
    delete_warehouse_permissions,
)
from databricks_cdk.resources.permissions.volume_permissions import (
    VolumePermissionsProperties,
    create_or_update_volume_permissions,
    delete_volume_permissions,
)
from databricks_cdk.resources.scim.user import UserProperties, create_or_update_user, delete_user
from databricks_cdk.resources.secrets.secret import SecretProperties, create_or_update_secret, delete_secret
from databricks_cdk.resources.secrets.secret_scope import (
    SecretScopeProperties,
    create_or_update_secret_scope,
    delete_secret_scope,
)
from databricks_cdk.resources.service_principals.service_principal import (
    ServicePrincipalProperties,
    create_or_update_service_principal,
    delete_service_principal,
)
from databricks_cdk.resources.service_principals.service_principal_secrets import (
    ServicePrincipalSecretsProperties,
    create_or_update_service_principal_secrets,
    delete_service_principal_secrets,
)
from databricks_cdk.resources.sql_warehouses.sql_warehouses import (
    SQLWarehouseProperties,
    create_or_update_warehouse,
    delete_warehouse,
)
from databricks_cdk.resources.tokens.token import TokenProperties, create_or_update_token, delete_token
from databricks_cdk.resources.unity_catalog.catalogs import CatalogProperties, create_or_update_catalog, delete_catalog
from databricks_cdk.resources.unity_catalog.external_storage import (
    ExternalLocationProperties,
    create_or_update_external_location,
    delete_external_location,
)
from databricks_cdk.resources.unity_catalog.metastore import (
    MetastoreProperties,
    create_or_update_metastore,
    delete_metastore,
)
from databricks_cdk.resources.unity_catalog.metastore_assignment import (
    AssignmentProperties,
    create_or_update_assignment,
    delete_assignment,
)
from databricks_cdk.resources.unity_catalog.permissions import (
    PermissionsProperties,
    create_or_update_permissions,
    delete_permissions,
)
from databricks_cdk.resources.unity_catalog.registered_models import (
    UnityCatalogRegisteredModelProperties,
    create_or_update_unity_catalog_registered_model,
    delete_unity_catalog_registered_model,
)
from databricks_cdk.resources.unity_catalog.schemas import SchemaProperties, create_or_update_schema, delete_schema
from databricks_cdk.resources.unity_catalog.storage_credentials import (
    StorageCredentialsProperties,
    create_or_update_storage_credential,
    delete_storage_credential,
)
from databricks_cdk.resources.unity_catalog.volumes import VolumeProperties, create_or_update_volume, delete_volume
from databricks_cdk.utils import CnfResponse

logger = logging.getLogger(__name__)


class DatabricksEvent(BaseModel):
    RequestType: str
    ResourceProperties: dict
    PhysicalResourceId: str | None = None

    def action(self):
        return self.ResourceProperties.get("action")


def create_or_update_resource(event: DatabricksEvent) -> CnfResponse:
    """Creates or update a given resource"""
    action = event.action()
    if action == "credentials":
        return create_or_update_credentials(CredentialsProperties(**event.ResourceProperties))
    elif action == "storage-configurations":
        return create_or_update_storage_configuration(StorageConfigProperties(**event.ResourceProperties))
    elif action == "networks":
        return create_or_update_networks(NetworksProperties(**event.ResourceProperties))
    elif action == "workspaces":
        return create_or_update_workspaces(WorkspaceProperties(**event.ResourceProperties))
    elif action == "instance-profile":
        return create_or_update_instance_profile(InstanceProfileProperties(**event.ResourceProperties))
    elif action == "cluster":
        return create_or_update_cluster(ClusterProperties(**event.ResourceProperties), event.PhysicalResourceId)

    elif action == "cluster-permissions":
        return create_or_update_cluster_permissions(ClusterPermissionsProperties(**event.ResourceProperties))
    elif action == "cluster-policy":
        return create_or_update_cluster_policy(
            ClusterPolicyProperties(**event.ResourceProperties),
            event.PhysicalResourceId,
        )
    elif action == "cluster-policy-permissions":
        return create_or_update_cluster_policy_permissions(
            ClusterPolicyPermissionsProperties(**event.ResourceProperties)
        )
    elif action == "user":
        return create_or_update_user(UserProperties(**event.ResourceProperties))
    elif action == "job-permissions":
        return create_or_update_job_permissions(JobPermissionsProperties(**event.ResourceProperties))
    elif action == "group":
        return create_or_update_group(GroupProperties(**event.ResourceProperties))
    elif action == "dbfs-file":
        return create_or_update_dbfs_file(DbfsFileProperties(**event.ResourceProperties))
    elif action == "secret-scope":
        return create_or_update_secret_scope(SecretScopeProperties(**event.ResourceProperties))
    elif action == "secret":
        return create_or_update_secret(SecretProperties(**event.ResourceProperties))
    elif action == "job":
        return create_or_update_job(JobProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "instance-pool":
        return create_or_update_instance_pool(
            InstancePoolProperties(**event.ResourceProperties), event.PhysicalResourceId
        )
    elif action == "warehouse":
        return create_or_update_warehouse(SQLWarehouseProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "warehouse-permissions":
        return create_or_update_warehouse_permissions(SQLWarehousePermissionsProperties(**event.ResourceProperties))
    elif action == "metastore" or action == "unity-metastore":
        return create_or_update_metastore(MetastoreProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "metastore-assignment" or action == "unity-metastore-assignment":
        return create_or_update_assignment(AssignmentProperties(**event.ResourceProperties))
    elif action == "catalog" or action == "unity-catalog":
        return create_or_update_catalog(CatalogProperties(**event.ResourceProperties))
    elif action == "schema" or action == "unity-schema":
        return create_or_update_schema(SchemaProperties(**event.ResourceProperties))
    elif action == "catalog-permission" or action == "unity-catalog-permission":
        return create_or_update_permissions(PermissionsProperties(**event.ResourceProperties))
    elif action == "registered-model-permission":
        return create_or_update_registered_model_permissions(
            RegisteredModelPermissionPermissionProperties(**event.ResourceProperties)
        )
    elif action == "volume-permissions":
        return create_or_update_volume_permissions(VolumePermissionsProperties(**event.ResourceProperties))
    elif action == "experiment-permission":
        return create_or_update_experiment_permissions(ExperimentPermissionProperties(**event.ResourceProperties))
    elif action == "token":
        return create_or_update_token(TokenProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "unity-storage-credentials":
        return create_or_update_storage_credential(StorageCredentialsProperties(**event.ResourceProperties))
    elif action == "unity-external-location":
        return create_or_update_external_location(ExternalLocationProperties(**event.ResourceProperties))
    elif action == "mlflow-experiment":
        return create_or_update_experiment(ExperimentProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "mlflow-registered-model":
        return create_or_update_registered_model(
            RegisteredModelProperties(**event.ResourceProperties),
            event.PhysicalResourceId,
        )
    elif action == "volume":
        return create_or_update_volume(VolumeProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "unity-registered-model":
        return create_or_update_unity_catalog_registered_model(
            UnityCatalogRegisteredModelProperties(**event.ResourceProperties), event.PhysicalResourceId
        )
    elif action == "service-principal":
        return create_or_update_service_principal(ServicePrincipalProperties(**event.ResourceProperties))
    elif action == "service-principal-secrets":
        return create_or_update_service_principal_secrets(
            ServicePrincipalSecretsProperties(**event.ResourceProperties),
            event.PhysicalResourceId,
        )
    else:
        raise RuntimeError(f"Unknown action: {action}")


def delete_resource(event: DatabricksEvent) -> CnfResponse:
    """Delete a given resource"""
    action = event.action()
    if action == "credentials":
        return delete_credentials(event.PhysicalResourceId)
    elif action == "storage-configurations":
        return delete_storage_configuration(
            StorageConfigProperties(**event.ResourceProperties),
            event.PhysicalResourceId,
        )
    elif action == "networks":
        return delete_networks(NetworksProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "workspaces":
        return delete_workspaces(WorkspaceProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "instance-profile":
        return delete_instance_profile(
            InstanceProfileProperties(**event.ResourceProperties),
            event.PhysicalResourceId,
        )
    elif action == "cluster":
        return delete_cluster(ClusterProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "cluster-policy":
        return delete_cluster_policy(
            ClusterPolicyProperties(**event.ResourceProperties),
            event.PhysicalResourceId,
        )
    elif action == "cluster-policy-permissions":
        return delete_cluster_policy_permissions(
            event.PhysicalResourceId,
        )
    elif action == "user":
        return delete_user(UserProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "cluster-permissions":
        return delete_cluster_permissions(event.PhysicalResourceId)
    elif action == "experiment-permission":
        return delete_experiment_permissions(
            ExperimentPermissionProperties(**event.ResourceProperties), event.PhysicalResourceId
        )
    elif action == "group":
        return delete_group(GroupProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "dbfs-file":
        return delete_dbfs_file(DbfsFileProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "secret-scope":
        return delete_secret_scope(SecretScopeProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "secret":
        return delete_secret(SecretProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "job":
        return delete_job(JobProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "instance-pool":
        return delete_instance_pool(InstancePoolProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "warehouse":
        return delete_warehouse(SQLWarehouseProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "warehouse-permissions":
        return delete_warehouse_permissions(event.PhysicalResourceId)
    elif action == "metastore" or action == "unity-metastore":
        return delete_metastore(MetastoreProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "metastore-assignment" or action == "unity-metastore-assignment":
        return delete_assignment(AssignmentProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "catalog" or action == "unity-catalog":
        return delete_catalog(CatalogProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "schema" or action == "unity-schema":
        return delete_schema(SchemaProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "catalog-permission" or action == "unity-catalog-permission":
        return delete_permissions(PermissionsProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "job-permissions":
        return delete_job_permissions(
            JobPermissionsProperties(**event.ResourceProperties),
            event.PhysicalResourceId,
        )
    elif action == "registered-model-permission":
        return delete_registered_model_permissions(
            RegisteredModelPermissionPermissionProperties(**event.ResourceProperties),
            event.PhysicalResourceId,
        )
    elif action == "volume-permissions":
        return delete_volume_permissions(
            VolumePermissionsProperties(**event.ResourceProperties),
            event.PhysicalResourceId,
        )
    elif action == "unity-storage-credentials":
        return delete_storage_credential(
            StorageCredentialsProperties(**event.ResourceProperties),
            event.PhysicalResourceId,
        )
    elif action == "unity-external-location":
        return delete_external_location(
            ExternalLocationProperties(**event.ResourceProperties),
            event.PhysicalResourceId,
        )
    elif action == "token":
        return delete_token(TokenProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "mlflow-experiment":
        return delete_experiment(ExperimentProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "mlflow-registered-model":
        return delete_registered_model(
            RegisteredModelProperties(**event.ResourceProperties),
            event.PhysicalResourceId,
        )
    elif action == "volume":
        return delete_volume(VolumeProperties(**event.ResourceProperties), event.PhysicalResourceId)
    elif action == "unity-registered-model":
        return delete_unity_catalog_registered_model(
            UnityCatalogRegisteredModelProperties(**event.ResourceProperties), event.PhysicalResourceId
        )
    elif action == "service-principal":
        return delete_service_principal(
            ServicePrincipalProperties(**event.ResourceProperties), event.PhysicalResourceId
        )
    elif action == "service-principal-secrets":
        return delete_service_principal_secrets(
            ServicePrincipalSecretsProperties(**event.ResourceProperties), event.PhysicalResourceId
        )
    else:
        raise RuntimeError(f"Unknown action: {action}")


def process_event(event: DatabricksEvent) -> CnfResponse:
    """Process a databricks deploy event"""
    try:
        if event.RequestType == "Create" or event.RequestType == "Update":
            return create_or_update_resource(event)
        elif event.RequestType == "Delete":
            return delete_resource(event)
        else:
            logger.error(f"unknown request_type: {event.RequestType}")
    except ValidationError:
        logger.error(f"{event}")
        raise


def handler(event, context):
    """Entrypoint for lambda"""
    logger.info(event)
    try:
        parsed_event = DatabricksEvent(**event)
        response_data = process_event(parsed_event)
        cfnresponse.send(
            event,
            context,
            cfnresponse.SUCCESS,
            response_data.dict(),
            physicalResourceId=response_data.physical_resource_id,
        )
    except Exception as e:
        logger.exception("Last-resort exception handler hit.")
        cfnresponse.send(event, context, cfnresponse.FAILED, None, reason=f"Uncaught exception: {e!s}")
