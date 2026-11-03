import {Template} from "aws-cdk-lib/assertions";
import * as cdk from "aws-cdk-lib";
import {DatabricksDeployLambda, UnityCatalogVolume, VolumeType} from "../../../../typescript/src";


describe("UnityCatalogVolume", () => {
    test("RegisteredModel Custom Resource synthesizes the way we expect", () => {
        const app = new cdk.App();
        const databricksStack = new cdk.Stack(app, "DatabricksStack");
        const deployLambda = DatabricksDeployLambda.fromServiceToken(databricksStack, "DeployLambda", "some-arn");
        const workspaceUrl = cdk.Fn.importValue("databricks-workspace-url");
        new UnityCatalogVolume(databricksStack, "UnityCatalogVolume", {
            volume: {
                name: "some-name",
                schema_name: "some-schema-name",
                catalog_name: "some-catalog-name",
                comment: "some-comment",
                storage_location: "some-storage-location",
                volume_type: VolumeType.EXTERNAL,
            },
            workspace_url: workspaceUrl.toString(),
            serviceToken: deployLambda.serviceToken.toString(),
        });

        const template = Template.fromStack(databricksStack);

        template.hasResourceProperties("AWS::CloudFormation::CustomResource",
            {

                "ServiceToken": "some-arn",
                "action": "volume",
                "workspace_url": {
                    "Fn::ImportValue": "databricks-workspace-url"
                },
                "volume": {
                    "name": "some-name",
                    "catalog_name": "some-catalog-name",
                    "schema_name": "some-schema-name",
                    "comment": "some-comment",
                    "storage_location": "some-storage-location",
                    "volume_type": "EXTERNAL"
                },
            });
    });
});
