from databricks.sdk.service.catalog import PermissionsChange, PermissionsList, Privilege, PrivilegeAssignment

from databricks_cdk.resources.permissions.changes import (
    get_assignment_dict_from_permissions_list,
    get_assignment_dict_from_privilege_assignments,
    get_permission_changes,
    get_permission_changes_assignments_changed,
    get_permission_changes_principals,
)


def test_get_assignment_dict_from_permissions_list():
    permissions_list = PermissionsList(
        privilege_assignments=[
            PrivilegeAssignment(principal="principal1", privileges=["APPLY_TAG", "WRITE_FILES"]),
            PrivilegeAssignment(principal="principal2", privileges=["READ_FILES"]),
        ]
    )

    result = get_assignment_dict_from_permissions_list(permissions_list)

    assert result == {
        "principal1": [Privilege.APPLY_TAG, Privilege.WRITE_FILES],
        "principal2": [Privilege.READ_FILES],
    }


def test_get_assignment_dict_from_permissions_list_empty():
    permissions_list = PermissionsList(privilege_assignments=None)

    result = get_assignment_dict_from_permissions_list(permissions_list)

    assert result == {}


def test_get_assignment_dict_from_privilege_assignments():
    privilege_assignments = [
        PrivilegeAssignment(principal="principal1", privileges=[Privilege.APPLY_TAG, Privilege.WRITE_FILES]),
        PrivilegeAssignment(principal="principal2", privileges=[Privilege.READ_FILES]),
    ]

    result = get_assignment_dict_from_privilege_assignments(privilege_assignments)

    assert result == {
        "principal1": [Privilege.APPLY_TAG, Privilege.WRITE_FILES],
        "principal2": [Privilege.READ_FILES],
    }


def test_get_assignment_dict_from_privilege_assignments_empty():
    privilege_assignments = [
        PrivilegeAssignment(principal="principal1", privileges=None),
        PrivilegeAssignment(principal=None, privileges=[Privilege.READ_FILES]),
    ]
    result = get_assignment_dict_from_privilege_assignments(privilege_assignments)

    assert result == {}


def test_get_permission_changes_assignments_changed():
    assignments_on_databricks_dict = {"principal": [Privilege.APPLY_TAG, Privilege.WRITE_FILES]}
    assignments_from_properties_dict = {"principal": [Privilege.APPLY_TAG, Privilege.READ_FILES]}

    result = get_permission_changes_assignments_changed(
        assignments_on_databricks_dict, assignments_from_properties_dict
    )

    # READ_FILES should be added WRITE_FILES should be removed
    assert result == [
        PermissionsChange(add=[Privilege.READ_FILES], principal="principal", remove=[Privilege.WRITE_FILES])
    ]


def test_get_permission_changes_assignments_changed_no_changes():
    assignments_on_databricks_dict = {"principal": [Privilege.APPLY_TAG, Privilege.WRITE_FILES]}
    assignments_from_properties_dict = {"principal": [Privilege.APPLY_TAG, Privilege.WRITE_FILES]}

    result = get_permission_changes_assignments_changed(
        assignments_on_databricks_dict, assignments_from_properties_dict
    )

    # No changes
    assert result == []


def test_get_permission_changes_new_principals():
    assignments_on_databricks_dict = {
        "principal_to_remove": [Privilege.APPLY_TAG],
        "principal_to_stay": [Privilege.APPLY_TAG],
    }
    assignments_from_properties_dict = {
        "principal_to_add": [Privilege.APPLY_TAG],
        "principal_to_stay": [Privilege.APPLY_TAG],
    }

    result = get_permission_changes_principals(assignments_on_databricks_dict, assignments_from_properties_dict)

    # No new principals
    assert result == [
        PermissionsChange(add=[Privilege.APPLY_TAG], principal="principal_to_add", remove=None),
        PermissionsChange(add=None, principal="principal_to_remove", remove=[Privilege.APPLY_TAG]),
    ]


def test_get_permission_changes_no_principals():
    assignments_on_databricks_dict = {}
    assignments_from_properties_dict = {}

    result = get_permission_changes_principals(assignments_on_databricks_dict, assignments_from_properties_dict)

    # No new principals
    assert result == []


def test_get_permission_changes():
    sample_permissions_list = PermissionsList(
        privilege_assignments=[
            PrivilegeAssignment(principal="user1", privileges=[Privilege.APPLY_TAG]),
            PrivilegeAssignment(principal="user2", privileges=[Privilege.CREATE]),
            PrivilegeAssignment(principal="userToRemove", privileges=[Privilege.CREATE]),
        ]
    )
    sample_privilege_assignments = [
        PrivilegeAssignment(principal="user1", privileges=[Privilege.APPLY_TAG]),
        PrivilegeAssignment(principal="user2", privileges=[Privilege.APPLY_TAG]),
        PrivilegeAssignment(principal="userToAdd", privileges=[Privilege.CREATE]),
    ]

    result = get_permission_changes(
        assignments_on_databricks=sample_permissions_list, assignments_from_properties=sample_privilege_assignments
    )

    assert result == [
        PermissionsChange(add=[Privilege.CREATE], principal="userToAdd", remove=None),
        PermissionsChange(add=None, principal="userToRemove", remove=[Privilege.CREATE]),
        PermissionsChange(add=[Privilege.APPLY_TAG], principal="user2", remove=[Privilege.CREATE]),
    ]
