import {CustomResource, RemovalPolicy} from "aws-cdk-lib";
import {Construct} from "constructs";


export interface UnityCatalogRegisteredModelTag {
    key: string
    value: string
}

export interface UnityCatalogRegisteredModelSettings {
    name: string
    schema_name: string
    catalog_name: string
    comment?: string
    storage_location?: string
    /**
     * Tags on the model. When set, the model gets exactly these tags: tags added outside CDK are removed on deploy.
     * Leave it out to not manage tags at all.
     */
    tags?: Array<UnityCatalogRegisteredModelTag>
}

export interface UnityCatalogRegisteredModelProperties {
    workspace_url: string
    registered_model: UnityCatalogRegisteredModelSettings
    /**
     * Take over the model if it already exists, instead of failing the deploy.
     * Useful when migrating a model that was created outside CDK. Defaults to false.
     */
    adopt_existing?: boolean
    /**
     * What happens to the model when it is removed from the stack or replaced.
     * Defaults to RETAIN. With DESTROY, deleting fails while the model still has versions, because Unity Catalog
     * only deletes empty models.
     */
    removalPolicy?: RemovalPolicy
}

export interface UnityCatalogRegisteredModelProps extends UnityCatalogRegisteredModelProperties {
    readonly serviceToken: string
}

/**
 * A registered model in Unity Catalog. Only the model itself is managed here:
 * versions and aliases are created by ML pipelines (for example with mlflow.register_model).
 */
export class UnityCatalogRegisteredModel extends CustomResource {
    /** The three-level name of the model, e.g. catalog.schema.model */
    readonly fullName: string;

    constructor(scope: Construct, id: string, props: UnityCatalogRegisteredModelProps) {
        super(scope, id, {
            serviceToken: props.serviceToken,
            removalPolicy: props.removalPolicy ?? RemovalPolicy.RETAIN,
            properties: {
                action: "unity-registered-model",
                workspace_url: props.workspace_url,
                registered_model: props.registered_model,
                adopt_existing: props.adopt_existing ?? false,
            }
        });
        this.fullName = this.ref;
    }
}
