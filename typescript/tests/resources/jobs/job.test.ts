import {Template} from "aws-cdk-lib/assertions";
import * as cdk from "aws-cdk-lib";

import {DatabricksDeployLambda, Job, JobTriggerSettings} from "../../../src";

function createJob(trigger: JobTriggerSettings): void {
    const app = new cdk.App();
    const databricksStack = new cdk.Stack(app, "DatabricksStack");
    new Job(databricksStack, "Job", {
        serviceToken: "some-arn",
        workspaceUrl: "https://test.cloud.databricks.com",
        job: {name: "some-job", tasks: [{task_key: "some-task"}], trigger},
    });
}

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

    test("Job Custom Resource synthesizes a chain of run job tasks", () => {
        const app = new cdk.App();
        const databricksStack = new cdk.Stack(app, "DatabricksStack");

        new Job(databricksStack, "Job", {
            serviceToken: "some-arn",
            workspaceUrl: "https://test.cloud.databricks.com",
            job: {
                name: "some-chain",
                tasks: [
                    {task_key: "first", run_job_task: {job_id: 1}},
                    {
                        task_key: "gate",
                        depends_on: [{task_key: "first"}],
                        condition_task: {left: "{{tasks.first.values.ok}}", op: "EQUAL_TO", right: "true"},
                    },
                    {
                        task_key: "second",
                        depends_on: [{task_key: "gate", outcome: "true"}],
                        run_if: "ALL_SUCCESS",
                        run_job_task: {job_id: 2, python_params: ["data", "--date", "2026-10-26"]},
                    },
                ],
                queue: {enabled: true},
                tags: {Application: "some-app"},
            },
        });

        const template = Template.fromStack(databricksStack);
        template.hasResourceProperties("AWS::CloudFormation::CustomResource",
            {
                "job": {
                    "name": "some-chain",
                    "tasks": [
                        {"task_key": "first", "run_job_task": {"job_id": 1}},
                        {"task_key": "gate", "depends_on": [{"task_key": "first"}]},
                        {
                            "task_key": "second",
                            "depends_on": [{"task_key": "gate", "outcome": "true"}],
                            "run_job_task": {"job_id": 2, "python_params": ["data", "--date", "2026-10-26"]},
                        },
                    ],
                    "queue": {"enabled": true},
                    "tags": {"Application": "some-app"},
                },
            }
        );
    });

    test("Job accepts a table update trigger", () => {
        expect(() => createJob({table_update: {table_names: ["catalog.schema.table"]}})).not.toThrow();
    });

    test("Job rejects a trigger with both file_arrival and table_update", () => {
        const trigger = {
            file_arrival: {url: "/Volumes/catalog/schema/volume/"},
            table_update: {table_names: ["catalog.schema.table"]},
        };

        // @ts-expect-error the type only allows one trigger type
        const typed: JobTriggerSettings = trigger;

        expect(() => createJob(typed)).toThrow("got: file_arrival, table_update");
    });

    test("Job rejects a trigger without a trigger type", () => {
        // @ts-expect-error the type requires one trigger type
        const trigger: JobTriggerSettings = {pause_status: "UNPAUSED"};

        expect(() => createJob(trigger)).toThrow("got: none");
    });
});
