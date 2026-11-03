export interface User {
    user_name: string
}

export interface Group {
    group_name: string
}

export interface ServicePrincipal {
    service_principal_name: string
}

export interface UserPermission extends User {
    permission_level: string
}

export interface GroupPermission extends Group {
    permission_level: string
}

export interface ServicePrincipalPermission extends ServicePrincipal {
    permission_level: string
}
