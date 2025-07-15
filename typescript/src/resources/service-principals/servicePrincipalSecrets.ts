import { CustomResource } from "aws-cdk-lib";
import { Construct } from "constructs";


export interface ServicePrincipalSecretsProperties {
    service_principal_id: string
}

export interface ServicePrincipalSecretsProps extends ServicePrincipalSecretsProperties {
    readonly serviceToken: string
}

export class ServicePrincipalSecrets extends CustomResource {
    constructor(scope: Construct, id: string, props: ServicePrincipalSecretsProps) {
        super(scope, id, {
            serviceToken: props.serviceToken,
            properties: {
                action: "service-principal-secrets",
                service_principal_id: props.service_principal_id,
            }
        });
    }

    public secretsManagerArn(): string {
        return this.getAttString("secrets_manager_arn");
    }

    public secretsManagerName(): string {
        return this.getAttString("secrets_manager_name");
    }
}
