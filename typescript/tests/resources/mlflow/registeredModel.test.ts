import {Template} from "aws-cdk-lib/assertions";
import * as cdk from "aws-cdk-lib";
import {DatabricksDeployLambda, RegisteredModel} from "../../../../typescript/src";

describe("RegisteredModel", () => {
    test("RegisteredModel Custom Resource synthesizes the way we expect", () => {
        const app = new cdk.App();
        const databricksStack = new cdk.Stack(app, "DatabricksStack");
        const deployLambda = DatabricksDeployLambda.fromServiceToken(databricksStack, "DeployLambda", "some-arn");
        const workspaceUrl = cdk.Fn.importValue("databricks-workspace-url");
        new RegisteredModel(databricksStack, "RegisteredModel", {
            name: "ml-model",
            description: "some description",
            tags: [{key: "hello", value: "world"}] ,
            serviceToken: deployLambda.serviceToken.toString(),
            workspaceUrl: workspaceUrl.toString(),
        });

        const template = Template.fromStack(databricksStack);

        template.hasResourceProperties("AWS::CloudFormation::CustomResource",
            {

                "ServiceToken": "some-arn",
                "action": "mlflow-registered-model",
                "workspace_url": {
                    "Fn::ImportValue": "databricks-workspace-url"
                },
                "name": "ml-model",
                "description": "some description",
                "tags": [{"key": "hello", "value":"world"}]
            });
    });
});
