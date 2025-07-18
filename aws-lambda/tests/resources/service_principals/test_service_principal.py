from unittest.mock import patch

import pytest
from databricks.sdk.errors import NotFound
from databricks.sdk.service.iam import ComplexValue, ServicePrincipal

from databricks_cdk.resources.service_principals.service_principal import (
    ServicePrincipalCreationError,
    ServicePrincipalNotFoundError,
    ServicePrincipalProperties,
    ServicePrincipalResponse,
    create_or_update_service_principal,
    create_service_principal,
    delete_service_principal,
    get_service_principal,
    update_service_principal,
)
from databricks_cdk.utils import CnfResponse


@patch("databricks_cdk.resources.service_principals.service_principal.get_workspace_client")
@patch("databricks_cdk.resources.service_principals.service_principal.update_service_principal")
@patch("databricks_cdk.resources.service_principals.service_principal.create_service_principal")
@patch("databricks_cdk.resources.service_principals.service_principal.get_service_principal")
def test_create_or_update_service_principal_create(
    patched_get_service_principal,
    patched_create_service_principal,
    patched_update_service_principal,
    patched_get_workspace_client,
    workspace_client,
):
    patched_get_workspace_client.return_value = workspace_client
    mock_properties = ServicePrincipalProperties(
        workspace_url="https://test.cloud.databricks.com",
        service_principal=ServicePrincipal(
            active=True,
            display_name="mock_name",
        ),
    )

    create_or_update_service_principal(properties=mock_properties)

    patched_create_service_principal.assert_called_once_with(
        ServicePrincipal(
            active=True,
            display_name="mock_name",
            id=None,
            application_id=None,
            entitlements=None,
            external_id=None,
            groups=None,
            roles=None,
            schemas=None,
        ),
        workspace_client,
    )
    patched_get_service_principal.assert_not_called()
    patched_update_service_principal.assert_not_called()


@patch("databricks_cdk.resources.service_principals.service_principal.get_workspace_client")
@patch("databricks_cdk.resources.service_principals.service_principal.update_service_principal")
@patch("databricks_cdk.resources.service_principals.service_principal.create_service_principal")
@patch("databricks_cdk.resources.service_principals.service_principal.get_service_principal")
def test_create_or_update_service_principal_update(
    patched_get_service_principal,
    patched_create_service_principal,
    patched_update_service_principal,
    patched_get_workspace_client,
    workspace_client,
):
    patched_get_workspace_client.return_value = workspace_client
    mock_physical_resource_id = "some_id"
    existing_service_principal = ServicePrincipal(
        active=True,
        display_name="mock_name",
        id=mock_physical_resource_id,
        roles=[ComplexValue(value="role")],
    )
    patched_get_service_principal.return_value = existing_service_principal
    mock_properties = ServicePrincipalProperties(
        workspace_url="https://test.cloud.databricks.com",
        service_principal=ServicePrincipal(
            active=True,
            display_name="mock_name",
            id=mock_physical_resource_id,
        ),
    )

    create_or_update_service_principal(properties=mock_properties)

    patched_get_service_principal.assert_called_once_with(mock_physical_resource_id, workspace_client)
    patched_update_service_principal.assert_called_once_with(
        ServicePrincipal(
            active=True,
            display_name="mock_name",
            id=mock_physical_resource_id,
            roles=None,
            application_id=None,
            entitlements=None,
            external_id=None,
            groups=None,
            schemas=None,
        ),
        workspace_client,
    )
    patched_create_service_principal.assert_not_called()


def test_get_service_principal(workspace_client):
    service_principal = ServicePrincipal(
        active=True,
        display_name="mock_name",
        id="some_id",
    )
    workspace_client.service_principals.get.return_value = service_principal

    response = get_service_principal("some_id", workspace_client)
    assert response == service_principal
    workspace_client.service_principals.get.assert_called_once_with(id="some_id")


def test_get_service_principal_error(workspace_client):
    workspace_client.service_principals.get.side_effect = NotFound("Not found")

    with pytest.raises(ServicePrincipalNotFoundError):
        get_service_principal("some_id", workspace_client)


def test_create_service_principal(workspace_client):
    mock_properties = ServicePrincipalProperties(
        workspace_url="https://test.cloud.databricks.com",
        service_principal=ServicePrincipal(
            active=True,
            application_id="mock_application_id",
            display_name="mock_name",
        ),
    )
    workspace_client.service_principals.create.return_value = ServicePrincipal(
        active=True,
        application_id="mock_application_id",
        display_name="mock_name",
        id="some_id",
    )

    response = create_service_principal(mock_properties.service_principal, workspace_client)

    assert response == ServicePrincipalResponse(
        name="mock_name", physical_resource_id="some_id", application_id="mock_application_id"
    )

    workspace_client.service_principals.create.assert_called_once_with(
        display_name="mock_name",
        active=True,
        id=None,
        application_id="mock_application_id",
        entitlements=None,
        external_id=None,
        groups=None,
        roles=None,
        schemas=None,
    )


def test_create_service_principal_error(workspace_client):
    mock_properties = ServicePrincipalProperties(
        workspace_url="https://test.cloud.databricks.com",
        service_principal=ServicePrincipal(
            active=True,
            display_name="mock_name",
        ),
    )
    workspace_client.service_principals.create.return_value = ServicePrincipal(
        active=True,
        display_name="mock_name",
        id=None,
    )

    with pytest.raises(ServicePrincipalCreationError):
        create_service_principal(mock_properties.service_principal, workspace_client)


def test_update_service_principal(workspace_client):
    mock_properties = ServicePrincipalProperties(
        workspace_url="https://test.cloud.databricks.com",
        service_principal=ServicePrincipal(
            active=True,
            application_id="mock_application_id",
            display_name="mock_name",
            id="some_id",
            roles=[ComplexValue(value="role")],
        ),
    )
    workspace_client.service_principals.update.return_value = ServicePrincipal(
        active=True,
        application_id="mock_application_id",
        display_name="mock_name",
        id="some_id",
        roles=[ComplexValue(value="role")],
    )

    response = update_service_principal(mock_properties.service_principal, workspace_client)

    assert response == ServicePrincipalResponse(
        name="mock_name", physical_resource_id="some_id", application_id="mock_application_id"
    )

    workspace_client.service_principals.update.assert_called_once_with(
        active=True,
        display_name="mock_name",
        id="some_id",
        roles=[ComplexValue(value="role")],
        application_id="mock_application_id",
        entitlements=None,
        external_id=None,
        groups=None,
        schemas=None,
    )


@patch("databricks_cdk.resources.service_principals.service_principal.get_workspace_client")
@patch("databricks_cdk.resources.service_principals.service_principal.get_account_client")
def test_delete_service_principal(
    patched_get_account_client,
    patched_get_workspace_client,
    workspace_client,
    account_client,
):
    patched_get_workspace_client.return_value = workspace_client
    patched_get_account_client.return_value = account_client
    mock_properties = ServicePrincipalProperties(
        workspace_url="https://test.cloud.databricks.com",
        service_principal=ServicePrincipal(
            active=True,
            display_name="mock_name",
            id="some_id",
        ),
    )
    response = delete_service_principal(mock_properties, "some_id")

    assert response == CnfResponse(physical_resource_id="some_id")
    workspace_client.service_principals.delete.assert_called_once_with(id="some_id")
    account_client.service_principals.delete.assert_called_once_with(id="some_id")
