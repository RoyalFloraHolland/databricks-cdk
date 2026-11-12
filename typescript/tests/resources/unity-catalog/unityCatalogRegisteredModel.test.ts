import {Template} from "aws-cdk-lib/assertions";
import * as cdk from "aws-cdk-lib";
import {DatabricksDeployLambda, UnityCatalogRegisteredModel} from "../../../../typescript/src";


function createStack() {
    const app = new cdk.App();
    const stack = new cdk.Stack(app, "DatabricksStack");
    const deployLambda = DatabricksDeployLambda.fromServiceToken(stack, "DeployLambda", "some-arn");
    const workspaceUrl = cdk.Fn.importValue("databricks-workspace-url");
    return {stack, deployLambda, workspaceUrl: workspaceUrl.toString()};
}

const registeredModel = {
    name: "some-model",
    schema_name: "some-schema-name",
    catalog_name: "some-catalog-name",
    comment: "some-comment",
};


describe("UnityCatalogRegisteredModel", () => {
    test("Custom Resource synthesizes the way we expect", () => {
        const {stack, deployLambda, workspaceUrl} = createStack();
        new UnityCatalogRegisteredModel(stack, "UnityCatalogRegisteredModel", {
            registered_model: registeredModel,
            workspace_url: workspaceUrl,
            serviceToken: deployLambda.serviceToken.toString(),
        });

        const template = Template.fromStack(stack);

        template.hasResourceProperties("AWS::CloudFormation::CustomResource", {
            "ServiceToken": "some-arn",
            "action": "unity-registered-model",
            "workspace_url": {
                "Fn::ImportValue": "databricks-workspace-url"
            },
            "registered_model": {
                "name": "some-model",
                "catalog_name": "some-catalog-name",
                "schema_name": "some-schema-name",
                "comment": "some-comment",
            },
            "adopt_existing": false,
        });
    });

    test("Can adopt an existing model", () => {
        const {stack, deployLambda, workspaceUrl} = createStack();
        deployLambda.createUnityCatalogRegisteredModel(stack, "UnityCatalogRegisteredModel", {
            registered_model: registeredModel,
            workspace_url: workspaceUrl,
            adopt_existing: true,
        });

        Template.fromStack(stack).hasResourceProperties("AWS::CloudFormation::CustomResource", {
            "action": "unity-registered-model",
            "adopt_existing": true,
        });
    });

    test("Passes tags to the custom resource", () => {
        const {stack, deployLambda, workspaceUrl} = createStack();
        deployLambda.createUnityCatalogRegisteredModel(stack, "UnityCatalogRegisteredModel", {
            registered_model: {...registeredModel, tags: [{key: "team", value: "datascience"}]},
            workspace_url: workspaceUrl,
        });

        Template.fromStack(stack).hasResourceProperties("AWS::CloudFormation::CustomResource", {
            "registered_model": {
                "name": "some-model",
                "tags": [{"key": "team", "value": "datascience"}],
            },
        });
    });

    test("Retains the model by default", () => {
        const {stack, deployLambda, workspaceUrl} = createStack();
        deployLambda.createUnityCatalogRegisteredModel(stack, "UnityCatalogRegisteredModel", {
            registered_model: registeredModel,
            workspace_url: workspaceUrl,
        });

        Template.fromStack(stack).hasResource("AWS::CloudFormation::CustomResource", {
            DeletionPolicy: "Retain",
            UpdateReplacePolicy: "Retain",
        });
    });

    test("Can be set to destroy the model", () => {
        const {stack, deployLambda, workspaceUrl} = createStack();
        deployLambda.createUnityCatalogRegisteredModel(stack, "UnityCatalogRegisteredModel", {
            registered_model: registeredModel,
            workspace_url: workspaceUrl,
            removalPolicy: cdk.RemovalPolicy.DESTROY,
        });

        Template.fromStack(stack).hasResource("AWS::CloudFormation::CustomResource", {
            DeletionPolicy: "Delete",
            UpdateReplacePolicy: "Delete",
        });
    });
});
