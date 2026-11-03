import {Construct} from "constructs";
import {Stack, StackProps, Fn} from "aws-cdk-lib";
import {DatabricksDeployLambda} from "databricks-cdk";

export class ApplicationStack extends Stack {

    constructor(scope: Construct, id: string, props: StackProps) {
        super(scope, id, props);

        // Reusing deploy lambda of root stack
        const deployLambda = DatabricksDeployLambda.fromServiceToken(this, "DeployLambda", Fn.importValue("databricks-deploy-lambda-arn"));
        const workspaceUrl = Fn.importValue("databricks-workspace-url");

        deployLambda.createJob(this, "TestJob", {
            workspaceUrl: workspaceUrl,
            job: {
                name: "TestJob",
                tasks: [{
                    task_key: "task_1",
                    spark_submit_task: {
                        parameters: ["dbfs://sripts/test.py"]
                    }
                }],
                job_clusters: [],
            }
        });

    }
}
