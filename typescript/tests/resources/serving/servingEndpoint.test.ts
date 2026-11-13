import {Template} from "aws-cdk-lib/assertions";
import * as cdk from "aws-cdk-lib";
import {DatabricksDeployLambda, ServingEndpoint, ServingEndpointWorkloadSize, ServingEndpointWorkloadType} from "../../../../typescript/src";


function createStack() {
    const app = new cdk.App();
    const stack = new cdk.Stack(app, "DatabricksStack");
    const deployLambda = DatabricksDeployLambda.fromServiceToken(stack, "DeployLambda", "some-arn");
    const workspaceUrl = cdk.Fn.importValue("databricks-workspace-url");
    return {stack, deployLambda, workspaceUrl: workspaceUrl.toString()};
}


describe("ServingEndpoint", () => {
    test("Custom Resource synthesizes the way we expect", () => {
        const {stack, deployLambda, workspaceUrl} = createStack();
        new ServingEndpoint(stack, "ServingEndpoint", {
            serviceToken: deployLambda.serviceToken.toString(),
            workspace_url: workspaceUrl,
            name: "some-endpoint",
            served_entity: {
                entity_name: "catalog.schema.model",
                alias: "champion",
                workload_size: ServingEndpointWorkloadSize.MEDIUM,
                workload_type: ServingEndpointWorkloadType.GPU_SMALL,
                scale_to_zero_enabled: true,
            },
            tags: [{key: "team", value: "datascience"}],
        });

        Template.fromStack(stack).hasResourceProperties("AWS::CloudFormation::CustomResource", {
            "ServiceToken": "some-arn",
            "action": "serving-endpoint",
            "workspace_url": {"Fn::ImportValue": "databricks-workspace-url"},
            "name": "some-endpoint",
            "served_entity": {
                "entity_name": "catalog.schema.model",
                "alias": "champion",
                "workload_size": "Medium",
                "workload_type": "GPU_SMALL",
                "scale_to_zero_enabled": true,
            },
            "tags": [{"key": "team", "value": "datascience"}],
            "adopt_existing": false,
        });
    });

    test("Retains the endpoint by default", () => {
        const {stack, deployLambda, workspaceUrl} = createStack();
        deployLambda.createServingEndpoint(stack, "ServingEndpoint", {
            workspace_url: workspaceUrl,
            name: "some-endpoint",
            served_entity: {entity_name: "catalog.schema.model", entity_version: "1"},
        });

        Template.fromStack(stack).hasResource("AWS::CloudFormation::CustomResource", {
            DeletionPolicy: "Retain",
            UpdateReplacePolicy: "Retain",
        });
    });

    test("Requires exactly one of entity_version or alias", () => {
        const {stack, deployLambda, workspaceUrl} = createStack();
        const create = (id: string, served_entity: {entity_name: string, entity_version?: string, alias?: string}) =>
            deployLambda.createServingEndpoint(stack, id, {workspace_url: workspaceUrl, name: id, served_entity});

        expect(() => create("Neither", {entity_name: "catalog.schema.model"})).toThrow("exactly one of");
        expect(() => create("Both", {entity_name: "catalog.schema.model", entity_version: "1", alias: "champion"}))
            .toThrow("exactly one of");
    });

    test("Exposes the served version", () => {
        const {stack, deployLambda, workspaceUrl} = createStack();
        const endpoint = deployLambda.createServingEndpoint(stack, "ServingEndpoint", {
            workspace_url: workspaceUrl,
            name: "some-endpoint",
            served_entity: {entity_name: "catalog.schema.model", alias: "champion"},
        });
        new cdk.CfnOutput(stack, "Version", {value: endpoint.entityVersion});

        Template.fromStack(stack).hasOutput("Version", {
            Value: {"Fn::GetAtt": ["ServingEndpoint", "entity_version"]},
        });
    });
});
