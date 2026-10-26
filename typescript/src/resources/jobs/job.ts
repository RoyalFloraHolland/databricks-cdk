import {CustomResource} from "aws-cdk-lib";
import {Construct} from "constructs";

export interface JobClusterAutoScale {
    min_workers: number
    max_workers: number
}

export interface JobClusterAwsAttributes {
    first_on_demand?: number
    availability?: string
    zone_id?: string
    instance_profile_arn?: string
    spot_bid_price_percent?: number
    ebs_volume_type?: string
    ebs_volume_count?: number
    ebs_volume_size?: number
    ebs_volume_iops?: number
    ebs_volume_throughput?: number
}

export interface JobClusterStorageInfo {
    destination: string
}

export interface JobClusterStorageInfoS3 extends JobClusterStorageInfo {
    region: string
    endpoint?: string
    enable_encryption?: boolean
    encryption_type?: string
    kms_key?: string
    canned_acl?: string
}

export interface JobClusterInitScriptInfoDbfs {
    dbfs: JobClusterStorageInfo
}

export interface JobClusterInitScriptInfoFile {
    file: JobClusterStorageInfo
}

export interface JobClusterInitScriptInfoS3 {
    s3: JobClusterStorageInfoS3
}

export interface JobClusterDockerBasicAuth {
    username: string
    password: string
}

export interface JobClusterDockerImage {
    url: string
    basic_auth?: JobClusterDockerBasicAuth
}

export interface JobClusterStorageInfo {
    destination: string
}

export interface JobClusterLogConfDbfs {
    dbfs: JobClusterStorageInfo;
}
export interface JobClusterLogConfS3 {
    s3: JobClusterStorageInfoS3;
}

export interface JobNewCluster {
    num_workers?: number
    autoscale?: JobClusterAutoScale
    spark_version: string
    spark_conf?: Record<string, string>
    aws_attributes: JobClusterAwsAttributes
    node_type_id?: string
    driver_node_type_id?: string
    ssh_public_keys?: Array<string>
    custom_tags?: Record<string, unknown>
    cluster_log_conf?: JobClusterLogConfDbfs | JobClusterLogConfS3
    init_scripts?: Array<JobClusterInitScriptInfoDbfs | JobClusterInitScriptInfoFile | JobClusterInitScriptInfoS3>
    docker_image?: JobClusterDockerImage
    spark_env_vars?: Record<string, unknown>
    autotermination_minutes?: number
    enable_elastic_disk?: boolean
    driver_instance_pool_id?: string
    instance_pool_id?: string
    data_security_mode?: string
    runtime_engine?: string
}

export interface JobCluster {
    job_cluster_key: string
    new_cluster: JobNewCluster
}

export interface JobNotebookTask {
    notebook_path: string
    base_parameters?: Record<string, unknown>
}

export interface JobSparkJarTask {
    main_class_name: string
    parameters?: Array<string>
}

export interface JobSparkPythonTask {
    python_file: string
    parameters?: Array<string>
}

export interface JobSparkSubmitTask {
    parameters: Array<string>
}

export interface JobPipelineTask {
    pipeline_id: string
}

export interface JobPythonWheelTask {
    package_name: string
    entry_point?: string
    parameters?: Array<string>
}

export interface JobTaskLibrary {
    jar?: string
    egg?: string
    whl?: string
    pypi?: string
    maven?: string
    cran?: string
}

export interface JobEmailNotifications {
    on_start?: Array<string>
    on_success?: Array<string>
    on_failure?: Array<string>
    no_alert_for_skipped_runs?: boolean
}

/**
 * Runs another job as a task.
 * Sent as `tasks[].run_job_task` in the Jobs API create and reset requests.
 * @see https://docs.databricks.com/aws/en/jobs/run-job
 * @see https://docs.databricks.com/api/workspace/jobs/create
 */
export interface JobRunJobTask {
    /** ID of the job to run, e.g. `otherJob.getAttString("job_id")`. */
    job_id: number | string
    /** Job-level parameters of the job to run. */
    job_parameters?: Record<string, string>
    /** Parameters for the job's Python tasks, replacing the ones in its definition. */
    python_params?: Array<string>
}

/**
 * An if/else branch. Tasks that depend on it pick a branch with `outcome`.
 * Sent as `tasks[].condition_task` in the Jobs API create and reset requests.
 * @see https://docs.databricks.com/aws/en/jobs/if-else
 * @see https://docs.databricks.com/api/workspace/jobs/create
 */
export interface JobConditionTask {
    /** Left operand, e.g. a task value `{{tasks.check.values.is_auction_day}}`. */
    left: string
    op: "EQUAL_TO" | "NOT_EQUAL" | "GREATER_THAN" | "GREATER_THAN_OR_EQUAL" | "LESS_THAN" | "LESS_THAN_OR_EQUAL"
    right: string
}

export interface JobTaskDependency {
    task_key: string
    /** For a dependency on a condition task: the branch this task runs on. */
    outcome?: "true" | "false"
}

/**
 * When a task runs, based on the state of its dependencies. Defaults to `ALL_SUCCESS`.
 * @see https://docs.databricks.com/aws/en/jobs/run-if
 */
export type JobRunIf =
    | "ALL_SUCCESS"
    | "AT_LEAST_ONE_SUCCESS"
    | "NONE_FAILED"
    | "ALL_DONE"
    | "AT_LEAST_ONE_FAILED"
    | "ALL_FAILED"

export interface JobTaskSettings {
    task_key: string
    description?: string
    /** Tasks that must finish first. A plain string is a task key, kept for compatibility. */
    depends_on?: Array<JobTaskDependency | string>
    run_if?: JobRunIf
    existing_cluster_id?: string
    new_cluster?: JobNewCluster
    job_cluster_key?: string
    notebook_task?: JobNotebookTask
    spark_jar_task?: JobSparkJarTask
    spark_python_task?: JobSparkPythonTask
    spark_submit_task?: JobSparkSubmitTask
    pipeline_task?: JobPipelineTask
    python_wheel_task?: JobPythonWheelTask
    run_job_task?: JobRunJobTask
    condition_task?: JobConditionTask
    libraries?: Array<JobTaskLibrary>
    email_notifications?: JobEmailNotifications
    timeout_seconds?: number
    max_retries?: number
    min_retry_interval_millis?: number
    retry_on_timeout?: boolean
}

export interface JobCronSchedule {
    quartz_cron_expression?: string
    timezone_id?: string
    pause_status?: string
}

/**
 * Starts a run when new files arrive in a Unity Catalog external location or volume.
 * Sent as `trigger.file_arrival` in the Jobs API create and reset requests.
 * @see https://docs.databricks.com/aws/en/jobs/file-arrival-triggers
 * @see https://docs.databricks.com/api/workspace/jobs/create
 */
export interface JobFileArrivalTrigger {
    /**
     * Root or subpath of a Unity Catalog external location or volume, e.g. `/Volumes/catalog/schema/volume/`.
     * Subdirectories are checked too.
     */
    url: string
    /** Minimum time to wait after a run completes before triggering the next one. */
    min_time_between_triggers_seconds?: number
    /** Time to wait after the last file arrives before triggering. Each new file resets the timer. */
    wait_after_last_change_seconds?: number
}

/**
 * Starts a run when Unity Catalog tables are updated.
 * Sent as `trigger.table_update` in the Jobs API create and reset requests.
 * @see https://docs.databricks.com/aws/en/jobs/trigger-table-update
 * @see https://docs.databricks.com/api/workspace/jobs/create
 */
export interface JobTableUpdateTrigger {
    /** Full names of the tables to monitor, e.g. `catalog.schema.table`. At most 10. */
    table_names: Array<string>
    /** With several tables, whether any table or all of them must be updated. */
    condition?: "ANY_UPDATED" | "ALL_UPDATED"
    /** Minimum time to wait after a run completes before triggering the next one. */
    min_time_between_triggers_seconds?: number
    /** Time to wait after the last table update before triggering. Each new update resets the timer. */
    wait_after_last_change_seconds?: number
}

interface JobTriggerSettingsBase {
    /** Whether the trigger is active. */
    pause_status?: "PAUSED" | "UNPAUSED"
}

/**
 * Starts job runs on an event instead of a schedule. Set exactly one of `file_arrival` or `table_update`.
 * A job with a trigger should not also have a schedule.
 * Sent as `trigger` in the Jobs API create and reset requests (`POST /api/2.1/jobs/create`, `/jobs/reset`).
 * @see https://docs.databricks.com/aws/en/jobs/triggers
 * @see https://docs.databricks.com/api/workspace/jobs/create
 */
export type JobTriggerSettings =
    | (JobTriggerSettingsBase & { file_arrival: JobFileArrivalTrigger, table_update?: never })
    | (JobTriggerSettingsBase & { table_update: JobTableUpdateTrigger, file_arrival?: never })

export function validateJobTrigger(trigger: JobTriggerSettings): void {
    const types = (["file_arrival", "table_update"] as const).filter((type) => trigger[type] !== undefined);
    if (types.length !== 1) {
        throw new Error(
            `A job trigger must set exactly one of file_arrival or table_update, got: ${types.join(", ") || "none"}`,
        );
    }
}

export interface JobAccessControlRequestForUser {
    user_name: string
    permission_level: string
}

export interface JobAccessControlRequestForGroup {
    group_name: string
    permission_level: string
}

/** @see https://docs.databricks.com/aws/en/jobs/advanced#queue-settings */
export interface JobQueueSettings {
    /** Queue runs that would exceed `max_concurrent_runs`, instead of skipping them. */
    enabled: boolean
}

/** @see https://docs.databricks.com/aws/en/jobs/job-parameters */
export interface JobParameterDefinition {
    name: string
    default: string
}

export interface JobSettings {
    name: string
    description?: string
    tasks: Array<JobTaskSettings>
    job_clusters?: Array<JobCluster>
    email_notifications?: JobEmailNotifications
    timeout_seconds?: number
    schedule?: JobCronSchedule
    trigger?: JobTriggerSettings
    queue?: JobQueueSettings
    parameters?: Array<JobParameterDefinition>
    tags?: Record<string, string>
    max_concurrent_runs?: number
    format?: string
    access_control_list?: Array<JobAccessControlRequestForUser | JobAccessControlRequestForGroup>
}

export interface JobProperties {
    workspaceUrl: string
    job: JobSettings
}

export interface JobProps extends JobProperties {
    readonly serviceToken: string
}

export class Job extends CustomResource {
    constructor(scope: Construct, id: string, props: JobProps) {
        if (props.job.trigger !== undefined) {
            validateJobTrigger(props.job.trigger);
        }
        super(scope, id, {
            serviceToken: props.serviceToken,
            properties: {
                action: "job",
                workspace_url: props.workspaceUrl,
                job: props.job,
            }
        });
    }
}
