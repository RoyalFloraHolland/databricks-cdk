import { CustomResource } from "aws-cdk-lib";
import { Construct } from "constructs";

export interface ComplexValue {
    // TODO: Add more fields according to the actual schema, refert to https://databricks-sdk-py.readthedocs.io/en/latest/dbdataclasses/iam.html#databricks.sdk.service.iam.ComplexValue
    value?: string,
}

export interface ServicePrincipalSettings {
    active?: boolean
    application_id?: string
    display_name?: string
    entitlements?: ComplexValue[]
    external_id?: string
    groups?: ComplexValue[]
    id?: string
    roles?: ComplexValue[]
    // TODO: Add support for a "schemas" field, refer to https://databricks-sdk-py.readthedocs.io/en/latest/dbdataclasses/iam.html#databricks.sdk.service.iam.ServicePrincipalSchema
}

export interface ServicePrincipalProperties {
    workspace_url: string
    service_principal_settings: ServicePrincipalSettings
}

export interface ServicePrincipalProps extends ServicePrincipalProperties {
    readonly serviceToken: string
}

export class ServicePrincipal extends CustomResource {
    constructor(scope: Construct, id: string, props: ServicePrincipalProps) {
        super(scope, id, {
            serviceToken: props.serviceToken,
            properties: {
                action: "service-principal",
                workspace_url: props.workspace_url,
                service_principal: props.service_principal_settings,
            }
        });
    }

    public servicePrincipalId(): string {
        return this.getAttString("physical_resource_id");
    }

    public servicePrincipalName(): string {
        return this.getAttString("name");
    }

    public servicePrincipalApplicationId(): string {
        return this.getAttString("application_id");
    }
}
