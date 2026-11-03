import {CustomResource} from "aws-cdk-lib";
import {Construct} from "constructs";
import {User, Group, ServicePrincipal} from "./models";


export enum RegisteredModelPermissionLevel {
    "CAN_READ",
    "CAN_EDIT",
    "CAN_MANAGE_STAGING_VERSIONS",
    "CAN_MANAGE_PRODUCTION_VERSIONS",
    "CAN_MANAGE"
}

export interface UserRegisteredModelPermission extends User {
    permission_level: RegisteredModelPermissionLevel
}

export interface GroupRegisteredModelPermission extends Group {
    permission_level: RegisteredModelPermissionLevel
}

export interface ServicePrinicpalRegisteredModelPermission extends ServicePrincipal {
    permission_level: RegisteredModelPermissionLevel
}


export interface RegisteredModelPermissionsProperties {
    workspaceUrl: string
    registeredModelId: string
    accessControlList: Array<UserRegisteredModelPermission | GroupRegisteredModelPermission | ServicePrinicpalRegisteredModelPermission>
}

export interface RegisteredModelPermissionsProps extends RegisteredModelPermissionsProperties {
    readonly serviceToken: string
}

export class RegisteredModelPermissions extends CustomResource {
    constructor(scope: Construct, id: string, props: RegisteredModelPermissionsProps) {
        super(scope, id, {
            serviceToken: props.serviceToken,
            properties: {
                action: "registered-model-permission",
                workspace_url: props.workspaceUrl,
                registered_model_id: props.registeredModelId,
                access_control_list: props.accessControlList,
            }
        });
    }
}
