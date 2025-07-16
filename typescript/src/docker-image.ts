import fs from "fs";
import path from "path";
import os from "os";
import {randomUUID} from "crypto";
import {aws_lambda} from "aws-cdk-lib";

export class DockerImage {
    public static generate(version?: string): aws_lambda.DockerImageCode {
        const dockerTempDir = fs.mkdtempSync(path.join(os.tmpdir(), "databricks-cdk-lambda-"));
        const dockerFile = path.join(dockerTempDir, "Dockerfile");

        const lambdaVersion = version || DockerImage.version();
        fs.writeFileSync(dockerFile, `FROM floriday/databricks-cdk-lambda:${lambdaVersion}`);

        // Random hash will trigger a rebuild always, only need if dev is used
        const randomHash = (lambdaVersion == "dev") ? randomUUID() : "";

        return aws_lambda.DockerImageCode.fromImageAsset(
            dockerTempDir, {
                file: "Dockerfile",
                buildArgs: {
                    version: lambdaVersion,
                    randomHash: randomHash,
                }
            }
        );
    }

    public static version() {
        const pj = require("../package.json"); // eslint-disable-line @typescript-eslint/no-var-requires
        return pj.version;
    }
}
