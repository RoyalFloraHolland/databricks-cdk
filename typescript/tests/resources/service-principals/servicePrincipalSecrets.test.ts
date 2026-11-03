import { Template } from "aws-cdk-lib/assertions";
import * as cdk from "aws-cdk-lib";
import { DatabricksDeployLambda, ServicePrincipalSecrets } from "../../../../typescript/src";


describe("ServicePrincipalSecrets", () => {
    test("RegisteredModel Custom Resource synthesizes the way we expect", () => {
        const app = new cdk.App();
        const databricksStack = new cdk.Stack(app, "DatabricksStack");
        const deployLambda = DatabricksDeployLambda.fromServiceToken(databricksStack, "DeployLambda", "some-arn");
        new ServicePrincipalSecrets(databricksStack, "ServicePrincipalSecrets", {
            service_principal_id: "1234",
            serviceToken: deployLambda.serviceToken.toString(),
        });

        const template = Template.fromStack(databricksStack);

        template.hasResourceProperties("AWS::CloudFormation::CustomResource",
            {

                "ServiceToken": "some-arn",
                "action": "service-principal-secrets",
                "service_principal_id": "1234",
            });
    });
});
