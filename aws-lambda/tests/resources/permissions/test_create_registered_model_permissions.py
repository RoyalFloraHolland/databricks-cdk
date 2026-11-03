from unittest.mock import patch

from databricks_cdk.resources.permissions.registered_model_permissions import (
    GroupPermission,
    RegisteredModelPermission,
    RegisteredModelPermissionPermissionProperties,
    ServicePrincipalPermission,
    UserPermission,
    create_or_update_registered_model_permissions,
    delete_registered_model_permissions,
    get_registered_model_permissions_url,
)
from databricks_cdk.utils import CnfResponse


def test_get_experiment_permissions_url():
    assert (
        get_registered_model_permissions_url(
            workspace_url="https://test.cloud.databricks.com", registered_model_id="1234"
        )
        == "https://test.cloud.databricks.com/api/2.0/permissions/registered-models/1234"
    )


@patch("databricks_cdk.resources.permissions.registered_model_permissions.put_request")
def test_create_or_update_experiment_permissions(patched_put_request):
    props = RegisteredModelPermissionPermissionProperties(
        registered_model_id=1234,
        workspace_url="https://test.cloud.databricks.com",
        access_control_list=[
            UserPermission(user_name="test@test.com", permission_level=RegisteredModelPermission.CAN_EDIT),
            ServicePrincipalPermission(
                service_principal_name="test_principal", permission_level=RegisteredModelPermission.CAN_MANAGE
            ),
            GroupPermission(group_name="test_group_1", permission_level=RegisteredModelPermission.CAN_READ),
            GroupPermission(
                group_name="test_group_2", permission_level=RegisteredModelPermission.CAN_MANAGE_PRODUCTION_VERSIONS
            ),
            GroupPermission(
                group_name="test_group_3", permission_level=RegisteredModelPermission.CAN_MANAGE_STAGING_VERSIONS
            ),
        ],
    )

    response = create_or_update_registered_model_permissions(props)

    assert isinstance(response, CnfResponse)
    assert response.physical_resource_id == "1234/permissions"

    assert patched_put_request.call_args.args == (
        "https://test.cloud.databricks.com/api/2.0/permissions/registered-models/1234",
        {
            "access_control_list": [
                {"user_name": "test@test.com", "permission_level": RegisteredModelPermission.CAN_EDIT},
                {"service_principal_name": "test_principal", "permission_level": RegisteredModelPermission.CAN_MANAGE},
                {"group_name": "test_group_1", "permission_level": RegisteredModelPermission.CAN_READ},
                {
                    "group_name": "test_group_2",
                    "permission_level": RegisteredModelPermission.CAN_MANAGE_PRODUCTION_VERSIONS,
                },
                {
                    "group_name": "test_group_3",
                    "permission_level": RegisteredModelPermission.CAN_MANAGE_STAGING_VERSIONS,
                },
            ]
        },
    )


@patch("databricks_cdk.resources.permissions.registered_model_permissions.put_request")
def test_delete_experiment_permissions(patched_put_request):
    props = RegisteredModelPermissionPermissionProperties(
        registered_model_id=1234,
        workspace_url="https://test.cloud.databricks.com",
        access_control_list=[
            UserPermission(user_name="test@test.com", permission_level=RegisteredModelPermission.CAN_EDIT),
            ServicePrincipalPermission(
                service_principal_name="test_principal", permission_level=RegisteredModelPermission.CAN_MANAGE
            ),
            GroupPermission(group_name="test_group", permission_level=RegisteredModelPermission.CAN_READ),
        ],
    )

    response = delete_registered_model_permissions(props, 1234)

    assert isinstance(response, CnfResponse)
    assert response.physical_resource_id == "1234/permissions"
    assert patched_put_request.call_args.args == (
        "https://test.cloud.databricks.com/api/2.0/permissions/registered-models/1234",
        {"access_control_list": []},
    )
