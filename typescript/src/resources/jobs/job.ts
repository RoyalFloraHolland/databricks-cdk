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

export interface JobTaskSettings {
    task_key: string
    description?: string
    depends_on?: Array<string>
    existing_cluster_id?: string
    new_cluster?: JobNewCluster
    job_cluster_key?: string
    notebook_task?: JobNotebookTask
    spark_jar_task?: JobSparkJarTask
    spark_python_task?: JobSparkPythonTask
    spark_submit_task?: JobSparkSubmitTask
    pipeline_task?: JobPipelineTask
    python_wheel_task?: JobPythonWheelTask
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

export interface JobFileArrivalTrigger {
    url: string
    min_time_between_triggers_seconds?: number
    wait_after_last_change_seconds?: number
}

export interface JobTableUpdateTrigger {
    table_names: Array<string>
    condition?: "ANY_UPDATED" | "ALL_UPDATED"
    min_time_between_triggers_seconds?: number
    wait_after_last_change_seconds?: number
}

/**
 * Set exactly one of file_arrival or table_update. A job with a trigger should not also have a schedule.
 */
export interface JobTriggerSettings {
    pause_status?: "PAUSED" | "UNPAUSED"
    file_arrival?: JobFileArrivalTrigger
    table_update?: JobTableUpdateTrigger
}

export interface JobAccessControlRequestForUser {
    user_name: string
    permission_level: string
}

export interface JobAccessControlRequestForGroup {
    group_name: string
    permission_level: string
}

export interface JobSettings {
    name: string
    tasks: Array<JobTaskSettings>
    job_clusters?: Array<JobCluster>
    email_notifications?: JobEmailNotifications
    timeout_seconds?: number
    schedule?: JobCronSchedule
    trigger?: JobTriggerSettings
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
