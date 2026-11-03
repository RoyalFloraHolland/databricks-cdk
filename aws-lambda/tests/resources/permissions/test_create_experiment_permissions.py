from unittest.mock import patch

from databricks_cdk.resources.permissions.experiment_permissions import (
    ExperimentPermission,
    ExperimentPermissionProperties,
    GroupPermission,
    ServicePrincipalPermission,
    UserPermission,
    create_or_update_experiment_permissions,
    delete_experiment_permissions,
    get_experiment_permissions_url,
)
from databricks_cdk.utils import CnfResponse


def test_get_experiment_permissions_url():
    assert (
        get_experiment_permissions_url(workspace_url="https://test.cloud.databricks.com", experiment_id="1234")
        == "https://test.cloud.databricks.com/api/2.0/permissions/experiments/1234"
    )


@patch("databricks_cdk.resources.permissions.experiment_permissions.put_request")
def test_create_or_update_experiment_permissions(patched_put_request):
    props = ExperimentPermissionProperties(
        experiment_id=1234,
        workspace_url="https://test.cloud.databricks.com",
        access_control_list=[
            UserPermission(user_name="test@test.com", permission_level=ExperimentPermission.CAN_EDIT),
            ServicePrincipalPermission(
                service_principal_name="test_principal", permission_level=ExperimentPermission.CAN_MANAGE
            ),
            GroupPermission(group_name="test_group", permission_level=ExperimentPermission.CAN_READ),
        ],
    )

    response = create_or_update_experiment_permissions(props)

    assert isinstance(response, CnfResponse)
    assert response.physical_resource_id == "1234/permissions"

    assert patched_put_request.call_args.args == (
        "https://test.cloud.databricks.com/api/2.0/permissions/experiments/1234",
        {
            "access_control_list": [
                {"user_name": "test@test.com", "permission_level": ExperimentPermission.CAN_EDIT},
                {"service_principal_name": "test_principal", "permission_level": ExperimentPermission.CAN_MANAGE},
                {"group_name": "test_group", "permission_level": ExperimentPermission.CAN_READ},
            ]
        },
    )


@patch("databricks_cdk.resources.permissions.experiment_permissions.put_request")
def test_delete_experiment_permissions(patched_put_request):
    props = ExperimentPermissionProperties(
        experiment_id=1234,
        workspace_url="https://test.cloud.databricks.com",
        access_control_list=[
            UserPermission(user_name="test@test.com", permission_level=ExperimentPermission.CAN_EDIT),
            ServicePrincipalPermission(
                service_principal_name="test_principal", permission_level=ExperimentPermission.CAN_MANAGE
            ),
            GroupPermission(group_name="test_group", permission_level=ExperimentPermission.CAN_READ),
        ],
    )

    response = delete_experiment_permissions(props, 1234)

    assert isinstance(response, CnfResponse)
    assert response.physical_resource_id == "1234/permissions"
    assert patched_put_request.call_args.args == (
        "https://test.cloud.databricks.com/api/2.0/permissions/experiments/1234",
        {"access_control_list": []},
    )
