import { Template } from "aws-cdk-lib/assertions";
import * as cdk from "aws-cdk-lib";
import { DatabricksDeployLambda, ServicePrincipal } from "../../../../typescript/src";


describe("ServicePrincipal", () => {
    test("RegisteredModel Custom Resource synthesizes the way we expect", () => {
        const app = new cdk.App();
        const databricksStack = new cdk.Stack(app, "DatabricksStack");
        const deployLambda = DatabricksDeployLambda.fromServiceToken(databricksStack, "DeployLambda", "some-arn");
        const workspaceUrl = cdk.Fn.importValue("databricks-workspace-url");
        new ServicePrincipal(databricksStack, "ServicePrincipal", {
            service_principal_settings: {
                active: true,
                application_id: "some_id",
                display_name: "some_name",
                roles: [{ value: "some_role" }],
            },
            workspace_url: workspaceUrl.toString(),
            serviceToken: deployLambda.serviceToken.toString(),
        });

        const template = Template.fromStack(databricksStack);

        template.hasResourceProperties("AWS::CloudFormation::CustomResource",
            {

                "ServiceToken": "some-arn",
                "action": "service-principal",
                "workspace_url": {
                    "Fn::ImportValue": "databricks-workspace-url"
                },
                "service_principal": {
                    "active": true,
                    "application_id": "some_id",
                    "display_name": "some_name",
                    "roles": [{ "value": "some_role" }]
                }
            });
    });
});
