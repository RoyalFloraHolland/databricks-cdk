from databricks.sdk.service.catalog import PermissionsChange, PermissionsList, Privilege, PrivilegeAssignment


def get_assignment_dict_from_permissions_list(permissions_list: PermissionsList) -> dict[str, list[Privilege]]:
    """Converts PermissionsList to dict with key of principal and list of associated privileges as value"""
    privilige_assignments = permissions_list.privilege_assignments

    if privilige_assignments is None:
        return {}

    return {
        x.principal: [Privilege(y) for y in x.privileges]
        for x in privilige_assignments
        if x.principal is not None and x.privileges is not None
    }


def get_assignment_dict_from_privilege_assignments(
    privilege_assignments: list[PrivilegeAssignment],
) -> dict[str, list[Privilege]]:
    """Converts list of PrivilegeAssignment to dict with key of principal and list of associated privileges as value"""
    return {
        x.principal: x.privileges for x in privilege_assignments if x.principal is not None and x.privileges is not None
    }


def get_permission_changes_principals(
    assignments_on_databricks_dict: dict[str, list[Privilege]],
    assignments_from_properties_dict: dict[str, list[Privilege]],
) -> list[PermissionsChange]:
    """See if there are new principals that need to be added"""
    permission_changes = []

    principals_on_databricks = set(assignments_on_databricks_dict.keys())
    principals_from_properties = set(assignments_from_properties_dict.keys())

    principals_to_add = principals_from_properties.difference(principals_on_databricks)
    principals_to_remove = principals_on_databricks.difference(principals_from_properties)

    for principal in principals_to_add:
        permission_changes.append(
            PermissionsChange(principal=principal, add=assignments_from_properties_dict[principal])
        )

    for principal in principals_to_remove:
        permission_changes.append(
            PermissionsChange(principal=principal, remove=assignments_on_databricks_dict[principal])
        )

    return permission_changes


def get_permission_changes_assignments_changed(
    assignments_on_databricks_dict: dict[str, list[Privilege]],
    assignments_from_properties_dict: dict[str, list[Privilege]],
) -> list[PermissionsChange]:
    """See if there are principal assignemnts that need to be updated"""
    permission_changes = []
    for principal, privileges in assignments_from_properties_dict.items():
        privileges_databricks = set(assignments_on_databricks_dict.get(principal, []))
        privileges_properties = set(privileges)

        if privileges_databricks != privileges_properties and len(privileges_databricks) > 0:
            to_remove = privileges_databricks.difference(privileges_properties)
            to_add = privileges_properties.difference(privileges_databricks)
            permission_changes.append(PermissionsChange(principal=principal, add=list(to_add), remove=list(to_remove)))

    return permission_changes


def get_permission_changes(
    assignments_on_databricks: PermissionsList, assignments_from_properties: list[PrivilegeAssignment]
) -> list[PermissionsChange]:
    """Get the changes between the existing grants and the new grants and create PermissionsChange object"""
    # Convert to dict for easier lookup
    assignments_on_databricks_dict = get_assignment_dict_from_permissions_list(assignments_on_databricks)
    assignments_from_properties_dict = get_assignment_dict_from_privilege_assignments(assignments_from_properties)

    permission_changes: list[PermissionsChange] = []
    permission_changes += get_permission_changes_principals(
        assignments_on_databricks_dict, assignments_from_properties_dict
    )
    permission_changes += get_permission_changes_assignments_changed(
        assignments_on_databricks_dict, assignments_from_properties_dict
    )

    return permission_changes
