import {Construct} from "constructs";
import {Stack, StackProps, CfnOutput} from "aws-cdk-lib";
import {DatabricksDeployLambda} from "databricks-cdk";

export class RootStack extends Stack {

    constructor(scope: Construct, id: string, props: StackProps) {
        super(scope, id, props);

        const deployLambda = new DatabricksDeployLambda(this, "DeployLambda", {
            region: this.region,
            accountId: this.account
        });

        new CfnOutput(this, "DeployLambdaArn", {
            value: deployLambda.lambda.functionArn,
            exportName: "databricks-deploy-lambda-arn",
        });

        const credentials = deployLambda.createCredential(this, "Credentials", {
            credentialsName: "credentials-name",
            roleArn: "role-arn",
        });
        const storageConfig = deployLambda.createStorageConfig(this, "StorageConfig", {
            storageConfigName: "storage-config-name",
            bucketName: "bucket-name",
        });

        const workspace = deployLambda.createWorkspace(this, "Workspace", {
            workspaceName: "databricks-workspace",
            awsRegion: this.region,
            credentialsId: credentials.credentialsId(),
            storageConfigurationId: storageConfig.storageConfigId(),
        });

        new CfnOutput(this, "DatabricksWorkspaceUrl", {
            value: workspace.workspaceUrl(),
            exportName: "databricks-workspace-url",
        });

        deployLambda.createUser(this, "UserTest", {
            workspaceUrl: workspace.workspaceUrl(),
            userName: "test@test.com",
        });

    }
}
