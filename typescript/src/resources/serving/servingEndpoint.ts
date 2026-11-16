import {CustomResource, RemovalPolicy} from "aws-cdk-lib";
import {Construct} from "constructs";


export enum ServingEndpointWorkloadSize {
    SMALL = "Small",
    MEDIUM = "Medium",
    LARGE = "Large",
}

export enum ServingEndpointWorkloadType {
    CPU = "CPU",
    GPU_SMALL = "GPU_SMALL",
    GPU_MEDIUM = "GPU_MEDIUM",
    GPU_LARGE = "GPU_LARGE",
    MULTIGPU_MEDIUM = "MULTIGPU_MEDIUM",
}

export interface ServingEndpointServedEntity {
    /** Three-level name of a Unity Catalog model, e.g. catalog.schema.model */
    entity_name: string
    /** Pin a version: CDK always serves this version. Set this or `alias`. */
    entity_version?: string
    /**
     * Serve the version behind this alias (e.g. "champion"). The alias is only resolved when the endpoint is created
     * or starts serving another model; after that CDK keeps the served version, so a pipeline can move it.
     * Set this or `entity_version`.
     */
    alias?: string
    /** Defaults to Small */
    workload_size?: ServingEndpointWorkloadSize
    /** Defaults to CPU */
    workload_type?: ServingEndpointWorkloadType
    /** Defaults to false */
    scale_to_zero_enabled?: boolean
    environment_vars?: Record<string, string>
}

export interface ServingEndpointTag {
    key: string
    value: string
}

export interface ServingEndpointProperties {
    workspace_url: string
    name: string
    served_entity: ServingEndpointServedEntity
    /**
     * Tags on the endpoint. When set, the endpoint gets exactly these tags: tags added outside CDK are removed on deploy.
     * Leave it out to not manage tags at all.
     */
    tags?: Array<ServingEndpointTag>
    /** Take over the endpoint if it already exists, instead of failing the deploy. Defaults to false. */
    adopt_existing?: boolean
    /**
     * What happens to the endpoint when it is removed from the stack or replaced (renamed). Defaults to RETAIN,
     * so a renamed endpoint keeps running (and costing) until it is deleted by hand.
     */
    removalPolicy?: RemovalPolicy
}

export interface ServingEndpointProps extends ServingEndpointProperties {
    readonly serviceToken: string
}

/**
 * A model serving endpoint that serves one Unity Catalog model.
 *
 * The deploy does not wait for the endpoint to be ready: it finishes once Databricks accepted the change.
 * Databricks keeps serving the previous config until the new one is up, and keeps it if the new one fails.
 */
export class ServingEndpoint extends CustomResource {
    readonly endpointName: string;
    /** The model version the endpoint was set to serve on the last deploy */
    readonly entityVersion: string;

    constructor(scope: Construct, id: string, props: ServingEndpointProps) {
        const {entity_version, alias} = props.served_entity;
        if ((entity_version === undefined) === (alias === undefined)) {
            throw new Error(`ServingEndpoint ${props.name}: set exactly one of served_entity.entity_version or served_entity.alias`);
        }

        super(scope, id, {
            serviceToken: props.serviceToken,
            removalPolicy: props.removalPolicy ?? RemovalPolicy.RETAIN,
            properties: {
                action: "serving-endpoint",
                workspace_url: props.workspace_url,
                name: props.name,
                served_entity: props.served_entity,
                tags: props.tags,
                adopt_existing: props.adopt_existing ?? false,
            }
        });
        this.endpointName = this.ref;
        this.entityVersion = this.getAttString("entity_version");
    }
}
