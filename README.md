[![npm version](https://badge.fury.io/js/databricks-cdk.svg)](https://badge.fury.io/js/databricks-cdk)

# databricks-cdk

## Overview

databricks-cdk is an open source library that allows you to deploy Databricks workspace and resources on AWS using the AWS Cloud Development Kit (CDK) version 2 and TypeScript.

## Prerequisites

- AWS CLI
- Node.js
- AWS CDK v2
- Databricks account
- AWS Systems Manager (SSM) parameters:
  - `/databricks/deploy/client-id`
  - `/databricks/deploy/client-secret` (secure parameter)
  - `/databricks/account-id` (not AWS account ID)

## Installation

To install databricks-cdk, you can use npm:

    npm install databricks-cdk

## Usage

Here's an example of how you can use databricks-cdk to deploy a Databricks workspace:

Initialize your AWS CDK project:

```shell
cdk init
```

Import the DatabricksDeployLambda class into your AWS CDK app:
```typescript
import {Construct} from "constructs";
import {Stack, StackProps} from "aws-cdk-lib";
import {DatabricksDeployLambda} from "databricks-cdk";

```

Create a Simple stack containing the DatabricksDeployLambda, and a Databricks Workspace and User.
```typescript
export class SimpleStack extends Stack {

    constructor(scope: Construct, id: string, props: StackProps) {
        super(scope, id, props);

        const deployLambda = new DatabricksDeployLambda(this, "DeployLambda", {
            region: this.region,
            accountId: this.account
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

        deployLambda.createUser(this, "UserTest", {
            workspaceUrl: workspace.workspaceUrl(),
            userName: "test@test.com",
        });


    }
}
```

Create an instance of the SimpleStack class:
```typescript
const app = new SimpleStack(app, "databricks-cdk");
```
Deploy the stack to your AWS account:
```shell
cdk deploy
```
Note: The AWS SSM parameters `/databricks/deploy/client-id`, `/databricks/deploy/client-secret`, and `/databricks/account-id` are required for the deployment to succeed.

- `/databricks/deploy/client-id` is the client-id of service principal that is account admin and workspace admin
- `/databricks/deploy/client-secret` is the client-secret of service principal that is account admin and workspace admin
- `/databricks/account-id` is the id of your databricks account

See also the simple-workspace and multi-stack examples in [examples](examples)

## Contributing

We welcome contributions to databricks-cdk! If you'd like to contribute, please follow these steps:

1. Fork the repository.
2. Install [prek](https://prek.j178.dev/) hooks
2. Create a branch for your feature or bug fix.
3. Make your changes.
4. Test your changes thoroughly.
5. Submit a pull request.


## License

* databricks-cdk is licensed under the MIT License. See [LICENSE](LICENSE) for more information
