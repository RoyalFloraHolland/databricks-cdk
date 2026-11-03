import {CustomResource} from "aws-cdk-lib";
import {Construct} from "constructs";

interface FixedPolicy {
    type: "fixed";
    value: string | number | boolean;
    hidden?: boolean;
}

interface ForbiddenPolicy {
    type: "forbidden";
}

interface LimitingPolicyBase {
    defaultValue?: string | number | boolean;
    isOptional?: boolean;
}

interface AllowlistPolicy {
    type: "allowlist";
    values: (string | number | boolean)[];
}

interface BlocklistPolicy {
    type: "blocklist";
    values: (string | number | boolean)[];
}

interface RegexPolicy {
    type: "regex";
    pattern: string;
}

interface RangePolicy {
    type: "range";
    minValue?: number;
    maxValue?: number;
}

interface UnlimitedPolicy {
    type: "unlimited";
}

export type LimitingPolicy = AllowlistPolicy | BlocklistPolicy | RegexPolicy | RangePolicy | UnlimitedPolicy;
export type PolicyElement = FixedPolicy | ForbiddenPolicy | (LimitingPolicy & LimitingPolicyBase);

export interface ClusterPolicyPolicy {
    [path: string]: PolicyElement
}

export interface ClusterPolicySettings {
    name: string
    description?: string
    definition: ClusterPolicyPolicy
}

export interface ClusterPolicyProperties {
    workspaceUrl: string
    clusterPolicy: ClusterPolicySettings
}

export interface ClusterPolicyProps extends ClusterPolicyProperties {
    serviceToken: string
}

export class ClusterPolicy extends CustomResource {
    constructor(scope: Construct, id: string, props: ClusterPolicyProps) {
        super(scope, id, {
            serviceToken: props.serviceToken,
            properties: {
                action: "cluster-policy",
                workspace_url: props.workspaceUrl,
                cluster_policy: props.clusterPolicy
            }
        });
    }

    public policyId(): string {
        return this.getAttString("physical_resource_id");
    }
}
