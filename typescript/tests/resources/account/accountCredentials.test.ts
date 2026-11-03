import {Template} from "aws-cdk-lib/assertions";
import * as cdk from "aws-cdk-lib";

import {DatabricksDeployLambda, AccountCredentials} from "../../../src";

describe("Credentials", () => {
    test("Credentials Custom Resource synthesizes the way we expect", () => {
        const app = new cdk.App();
        const databricksStack = new cdk.Stack(app, "DatabricksStack");
        const deployLambda = DatabricksDeployLambda.fromServiceToken(databricksStack, "DeployLambda", "some-arn");

        new AccountCredentials(databricksStack, "Credentials", {
            serviceToken: deployLambda.serviceToken.toString(),
            roleArn: "some-role-arn",
            credentialsName: "some-credentials-name",
        });

        const template = Template.fromStack(databricksStack);
        template.hasResourceProperties("AWS::CloudFormation::CustomResource",
            {
                "ServiceToken": "some-arn",
                "action": "credentials",
                "credentials_name": "some-credentials-name",
                "role_arn": "some-role-arn",
            }
        );

    });

});
