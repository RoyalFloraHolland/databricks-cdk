import {Template} from "aws-cdk-lib/assertions";
import * as cdk from "aws-cdk-lib";

import {DatabricksDeployLambda, Job} from "../../../src";

describe("Job", () => {
    test("Job Custom Resource synthesizes a file arrival trigger", () => {
        const app = new cdk.App();
        const databricksStack = new cdk.Stack(app, "DatabricksStack");
        const deployLambda = DatabricksDeployLambda.fromServiceToken(databricksStack, "DeployLambda", "some-arn");

        new Job(databricksStack, "Job", {
            serviceToken: deployLambda.serviceToken.toString(),
            workspaceUrl: "https://test.cloud.databricks.com",
            job: {
                name: "some-job",
                tasks: [{task_key: "some-task"}],
                trigger: {
                    pause_status: "UNPAUSED",
                    file_arrival: {url: "/Volumes/catalog/schema/volume/"},
                },
            },
        });

        const template = Template.fromStack(databricksStack);
        template.hasResourceProperties("AWS::CloudFormation::CustomResource",
            {
                "ServiceToken": "some-arn",
                "action": "job",
                "job": {
                    "name": "some-job",
                    "trigger": {
                        "pause_status": "UNPAUSED",
                        "file_arrival": {"url": "/Volumes/catalog/schema/volume/"},
                    },
                },
            }
        );
    });
});
