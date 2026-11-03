import {Template} from "aws-cdk-lib/assertions";
import * as cdk from "aws-cdk-lib";

import {DatabricksDeployLambda, VolumePermissions, PrivilegeVolume} from "../../../../typescript/src";

describe("VolumePermissions", () => {
    test("VolumePermissions Custom Resource synthesizes the way we expect", () => {
        const app = new cdk.App();
        const databricksStack = new cdk.Stack(app, "DatabricksStack");
        const deployLambda = DatabricksDeployLambda.fromServiceToken(databricksStack, "DeployLambda", "some-arn");
        const workspaceUrl = cdk.Fn.importValue("databricks-workspace-url");
        new VolumePermissions(databricksStack, "VolumePermissions", {
            privilege_assignments: [
                {
                    principal: "some-principal",
                    privileges: [
                        PrivilegeVolume.APPLY_TAG,
                        PrivilegeVolume.READ_VOLUME,
                        PrivilegeVolume.WRITE_VOLUME,
                        PrivilegeVolume.ALL_PRIVILEGES,
                    ]
                },
                {
                    principal: "some-other-principal",
                    privileges: [
                        PrivilegeVolume.APPLY_TAG,
                        PrivilegeVolume.READ_VOLUME,
                    ]
                }
            ],
            workspaceUrl: workspaceUrl.toString(),
            serviceToken: deployLambda.serviceToken.toString(),
            volume_name: "some-volume"
        });

        const template = Template.fromStack(databricksStack);

        template.hasResourceProperties("AWS::CloudFormation::CustomResource",
            {

                "ServiceToken": "some-arn",
                "action": "volume-permissions",
                "workspace_url": {
                    "Fn::ImportValue": "databricks-workspace-url"
                },
                "privilege_assignments": [
                    {
                        "principal": "some-principal",
                        "privileges": [
                            "APPLY_TAG",
                            "READ_VOLUME",
                            "WRITE_VOLUME",
                            "ALL_PRIVILEGES"
                        ]
                    },
                    {
                        "principal": "some-other-principal",
                        "privileges": [
                            "APPLY_TAG",
                            "READ_VOLUME"
                        ]
                    }
                ],
                "volume_name": "some-volume"
            });
    });
});
