import { Duration } from "aws-cdk-lib";
import { aws_lambda, aws_logs, aws_iam } from "aws-cdk-lib";
import { AccountCredentials, AccountCredentialsProperties } from "./account/accountCredentials";
import { AccountStorageConfig, AccountStorageConfigProperties } from "./account/account-storage-config";
import { AccountNetwork, AccountNetworkProperties } from "./account/accountNetwork";
import { Workspace, WorkspaceProperties } from "./account/workspace";
import { InstanceProfile, InstanceProfileProperties } from "./instance-profiles/instance-profile";
import { Cluster, ClusterProperties } from "./clusters/cluster";
import { ClusterPermissions, ClusterPermissionsProperties } from "./permissions/cluster-permissions";
import { VolumePermissions, VolumePermissionsProperties } from "./permissions/volumePermissions";
import { DbfsFile, DbfsFileProperties } from "./dbfs/dbfs-file";
import { SecretScope, SecretScopeProperties } from "./secrets/secret-scope";
import { Job, JobProperties } from "./jobs/job";
import { Group, GroupProperties } from "./groups/group";
import { ScimUser, ScimUserProperties } from "./scim/scimUser";
import { InstancePool, InstancePoolProperties } from "./instance-pools/instance-pools";
import { Warehouse, WarehouseProperties } from "./sql-warehouses/sql-warehouses";
import { WarehousePermissions, WarehousePermissionsProperties } from "./permissions/sql-warehouse-permissions";
import { Construct } from "constructs";
import { DockerImage } from "../docker-image";
import {
    UnityCatalogVolume, UnityCatalogVolumeProperties,
    UnityCatalogCatalog,
    UnityCatalogCatalogProperties, UnityCatalogExternalLocation, UnityCatalogExternalLocationProperties,
    UnityCatalogMetastore,
    UnityCatalogMetastoreAssignment,
    UnityCatalogMetastoreAssignmentProperties,
    UnityCatalogMetastoreProperties,
    UnityCatalogPermission,
    UnityCatalogPermissionProperties,
    UnityCatalogSchema,
    UnityCatalogSchemaProperties, UnityCatalogStorageCredential, UnityCatalogStorageCredentialProperties
} from "./unity-catalog";
import { JobPermissions, JobPermissionsProperties, RegisteredModelPermissions, RegisteredModelPermissionsProperties, ExperimentPermissions, ExperimentPermissionsProperties } from "./permissions";
import { ClusterPolicy, ClusterPolicyProperties } from "./cluster-policies";
import { ClusterPolicyPermissions, ClusterPolicyPermissionsProperties } from "./permissions/cluster-policy-permissions";
import { Token, TokenProperties } from "./tokens";
import { Experiment, ExperimentProperties } from "./mlflow";
import { RegisteredModel, RegisteredModelProps } from "./mlflow/registeredModel";
import { ServicePrincipal, ServicePrincipalProperties, ServicePrincipalSecrets, ServicePrincipalSecretsProperties } from "./service-principals";


export interface CustomDeployLambdaProps {
    readonly accountId: string
    readonly region: string
    readonly lambdaVersion?: string
    readonly databricksAccountParam?: string
    readonly clientSecretParam?: string
    readonly lambdaCode?: aws_lambda.DockerImageCode
    readonly lambdaName?: string
    readonly lambdaId?: string
}

export abstract class IDatabricksDeployLambda extends Construct {
    serviceToken = "";

    public createCredential(scope: Construct, id: string, props: AccountCredentialsProperties): AccountCredentials {
        return new AccountCredentials(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createStorageConfig(scope: Construct, id: string, props: AccountStorageConfigProperties): AccountStorageConfig {
        return new AccountStorageConfig(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createNetwork(scope: Construct, id: string, props: AccountNetworkProperties): AccountNetwork {
        return new AccountNetwork(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createWorkspace(scope: Construct, id: string, props: WorkspaceProperties): Workspace {
        return new Workspace(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createInstanceProfile(scope: Construct, id: string, props: InstanceProfileProperties): InstanceProfile {
        return new InstanceProfile(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createCluster(scope: Construct, id: string, props: ClusterProperties): Cluster {
        return new Cluster(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createUser(scope: Construct, id: string, props: ScimUserProperties): ScimUser {
        return new ScimUser(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createClusterPermissions(scope: Construct, id: string, props: ClusterPermissionsProperties): ClusterPermissions {
        return new ClusterPermissions(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createClusterPolicy(scope: Construct, id: string, props: ClusterPolicyProperties): ClusterPolicy {
        return new ClusterPolicy(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createRegisteredModelPermissions(scope: Construct, id: string, props: RegisteredModelPermissionsProperties): RegisteredModelPermissions {
        return new RegisteredModelPermissions(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createClusterPolicyPermissions(scope: Construct, id: string, props: ClusterPolicyPermissionsProperties): ClusterPolicyPermissions {
        return new ClusterPolicyPermissions(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createExperimentPermissions(scope: Construct, id: string, props: ExperimentPermissionsProperties): ExperimentPermissions {
        return new ExperimentPermissions(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }


    public createGroup(scope: Construct, id: string, props: GroupProperties): Group {
        return new Group(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createDbfsFile(scope: Construct, id: string, props: DbfsFileProperties): DbfsFile {
        return new DbfsFile(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createToken(scope: Construct, id: string, props: TokenProperties): Token {
        return new Token(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createSecretScope(scope: Construct, id: string, props: SecretScopeProperties): SecretScope {
        return new SecretScope(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createJob(scope: Construct, id: string, props: JobProperties): Job {
        return new Job(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createJobPermissions(scope: Construct, id: string, props: JobPermissionsProperties): JobPermissions {
        return new JobPermissions(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createVolumePermissions(scope: Construct, id: string, props: VolumePermissionsProperties): VolumePermissions {
        return new VolumePermissions(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createInstancePool(scope: Construct, id: string, props: InstancePoolProperties): InstancePool {
        return new InstancePool(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createWarehouse(scope: Construct, id: string, props: WarehouseProperties): Warehouse {
        return new Warehouse(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createWarehousePermissions(scope: Construct, id: string, props: WarehousePermissionsProperties): WarehousePermissions {
        return new WarehousePermissions(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createUnityCatalogVolume(scope: Construct, id: string, props: UnityCatalogVolumeProperties): UnityCatalogVolume {
        return new UnityCatalogVolume(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createUnityCatalogMetastore(scope: Construct, id: string, props: UnityCatalogMetastoreProperties): UnityCatalogMetastore {
        return new UnityCatalogMetastore(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createUnityCatalogMetastoreAssignment(scope: Construct, id: string, props: UnityCatalogMetastoreAssignmentProperties): UnityCatalogMetastoreAssignment {
        return new UnityCatalogMetastoreAssignment(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createUnityCatalogCatalog(scope: Construct, id: string, props: UnityCatalogCatalogProperties): UnityCatalogCatalog {
        return new UnityCatalogCatalog(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createUnityCatalogSchema(scope: Construct, id: string, props: UnityCatalogSchemaProperties): UnityCatalogSchema {
        return new UnityCatalogSchema(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createUnityCatalogPermission(scope: Construct, id: string, props: UnityCatalogPermissionProperties): UnityCatalogPermission {
        return new UnityCatalogPermission(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createUnityCatalogStorageCredential(scope: Construct, id: string, props: UnityCatalogStorageCredentialProperties): UnityCatalogStorageCredential {
        return new UnityCatalogStorageCredential(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createUnityCatalogExternalLocation(scope: Construct, id: string, props: UnityCatalogExternalLocationProperties): UnityCatalogExternalLocation {
        return new UnityCatalogExternalLocation(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createMlflowExperiment(scope: Construct, id: string, props: ExperimentProperties): Experiment {
        return new Experiment(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createMlflowRegisteredModel(scope: Construct, id: string, props: RegisteredModelProps): RegisteredModel {
        return new RegisteredModel(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createServicePrincipal(scope: Construct, id: string, props: ServicePrincipalProperties): ServicePrincipal {
        return new ServicePrincipal(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

    public createServicePrincipalSecrets(scope: Construct, id: string, props: ServicePrincipalSecretsProperties): ServicePrincipalSecrets {
        return new ServicePrincipalSecrets(scope, id, {
            ...props,
            serviceToken: this.serviceToken
        });
    }

}

export class DatabricksDeployLambdaImport extends IDatabricksDeployLambda {
    constructor(scope: Construct, id: string, serviceToken: string) {
        super(scope, id);
        this.serviceToken = serviceToken;
    }
}

export class DatabricksDeployLambda extends IDatabricksDeployLambda {

    readonly props: CustomDeployLambdaProps;
    readonly lambda: aws_lambda.IFunction;
    readonly lambdaRole: aws_iam.IRole;

    constructor(scope: Construct, id: string, props: CustomDeployLambdaProps) {
        super(scope, id);
        this.props = props;

        const dockerImageCode = this.props.lambdaCode || DockerImage.generate(this.props.lambdaVersion);

        this.lambdaRole = new aws_iam.Role(this, "Role", {
            assumedBy: new aws_iam.ServicePrincipal("lambda.amazonaws.com"),
            managedPolicies: [
                aws_iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole"),
            ]
        });
        this.lambdaRole.addToPrincipalPolicy(new aws_iam.PolicyStatement({
            effect: aws_iam.Effect.ALLOW,
            actions: ["ssm:GetParameter"],
            resources: [
                `arn:aws:ssm:${this.props.region}:${this.props.accountId}:parameter/databricks/*`,
            ]
        }));

        this.lambdaRole.addToPrincipalPolicy(new aws_iam.PolicyStatement({
            effect: aws_iam.Effect.ALLOW,
            actions: ["secretsmanager:ListSecrets"],
            resources: ["*"] // AWS doesn't support providing specific resources for the ListSecrets action
        }));

        this.lambdaRole.addToPrincipalPolicy(new aws_iam.PolicyStatement({
            effect: aws_iam.Effect.ALLOW,
            actions: ["secretsmanager:CreateSecret", "secretsmanager:DeleteSecret", "secretsmanager:UpdateSecret"],
            resources: [
                `arn:aws:secretsmanager:${this.props.region}:${this.props.accountId}:secret:/databricks/*`,
            ]
        }));

        const lambdaId = this.props.lambdaId || `${id}Lambda`;
        this.lambda = new aws_lambda.DockerImageFunction(this, lambdaId, {
            functionName: this.props.lambdaName,
            code: dockerImageCode,
            timeout: Duration.minutes(15), // max timeout for lambda, waiting until resources are ready can take a while
            role: this.lambdaRole,
            memorySize: 512,
            environment: {
                LAMBDA_METHOD: "cfn-deploy",
                ACCOUNT_PARAM: props.databricksAccountParam || "/databricks/account-id",
                CLIENT_SECRET_PARAM: props.clientSecretParam || "/databricks/deploy/client-secret"
            },
            logRetention: aws_logs.RetentionDays.THREE_MONTHS,
        });
        this.serviceToken = this.lambda.functionArn;
    }

    public static fromServiceToken(scope: Construct, id: string, serviceToken: string): IDatabricksDeployLambda {
        return new DatabricksDeployLambdaImport(scope, id, serviceToken);
    }
}
