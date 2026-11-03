import json
import logging

import requests
from pydantic import BaseModel, root_validator, validator

from databricks_cdk.utils import CnfResponse, get_authorization_headers, post_request

logger = logging.getLogger(__name__)


class JobEmailNotifications(BaseModel):
    on_start: list[str] = []
    on_success: list[str] = []
    on_failure: list[str] = []
    no_alert_for_skipped_runs: bool = False


class AutoScale(BaseModel):
    min_workers: int
    max_workers: int


class AwsAttributes(BaseModel):
    first_on_demand: int | None = None
    availability: str | None = None
    zone_id: str | None = None
    instance_profile_arn: str | None = None
    spot_bid_price_percent: int | None = None
    ebs_volume_type: str | None = None
    ebs_volume_count: int | None = None
    ebs_volume_size: int | None = None
    ebs_volume_iops: int | None = None
    ebs_volume_throughput: int | None = None


class DockerBasicAuth(BaseModel):
    username: str
    password: str


class DockerImage(BaseModel):
    url: str
    basic_auth: DockerBasicAuth | None


class NewCluster(BaseModel):
    num_workers: int | None = None
    autoscale: AutoScale | None = None
    spark_version: str
    docker_image: DockerImage | None = None
    spark_conf: dict[str, str] = {}
    aws_attributes: AwsAttributes
    node_type_id: str | None = None
    driver_node_type_id: str | None = None
    ssh_public_keys: list[str] = []
    custom_tags: dict | None = None
    cluster_log_conf: dict | None = None
    init_scripts: list[dict] = []
    spark_env_vars: dict[str, str] = {}
    enable_elastic_disk: bool | None = None
    driver_instance_pool_id: str | None = None
    instance_pool_id: str | None = None
    data_security_mode: str | None = None
    runtime_engine: str | None = None


class JobCluster(BaseModel):
    job_cluster_key: str
    new_cluster: NewCluster


class NotebookTask(BaseModel):
    notebook_path: str
    base_parameters: dict = {}


class SparkJarTask(BaseModel):
    main_class_name: str
    parameters: list[str] = []


class SparkPythonTask(BaseModel):
    python_file: str
    parameters: list[str] = []


class SparkSubmitTask(BaseModel):
    parameters: list[str] = []


class PipelineTask(BaseModel):
    pipeline_id: str


class PythonWheelTask(BaseModel):
    package_name: str
    entry_point: str | None = None
    parameters: list[str] = []


class Library(BaseModel):
    jar: str | None = None
    egg: str | None = None
    whl: str | None = None
    pypi: str | None = None
    maven: str | None = None
    cran: str | None = None


class RunJobTask(BaseModel):
    """Runs another job, see https://docs.databricks.com/aws/en/jobs/run-job

    API: `tasks[].run_job_task` in https://docs.databricks.com/api/workspace/jobs/create
    """

    job_id: int
    job_parameters: dict[str, str] | None = None
    python_params: list[str] | None = None


class ConditionTask(BaseModel):
    """If/else branch, see https://docs.databricks.com/aws/en/jobs/if-else

    API: `tasks[].condition_task` in https://docs.databricks.com/api/workspace/jobs/create
    """

    left: str
    op: str
    right: str


class TaskDependency(BaseModel):
    """API: `tasks[].depends_on[]` in https://docs.databricks.com/api/workspace/jobs/create"""

    task_key: str
    # "true" or "false": the branch of a condition_task this task runs on
    outcome: str | None = None


# Task and job fields that are only sent when set, so the body of jobs that don't use them is unchanged
OPTIONAL_TASK_FIELDS = {"run_if", "run_job_task", "condition_task"}
OPTIONAL_JOB_FIELDS = {"trigger", "description", "queue", "parameters", "tags"}


class JobTaskSettings(BaseModel):
    task_key: str
    description: str | None = None
    depends_on: list[TaskDependency] = []
    run_if: str | None = None
    existing_cluster_id: str | None = None
    new_cluster: NewCluster | None = None
    job_cluster_key: str | None = None
    notebook_task: NotebookTask | None = None
    spark_jar_task: SparkJarTask | None = None
    spark_python_task: SparkPythonTask | None = None
    spark_submit_task: SparkSubmitTask | None = None
    pipeline_task: PipelineTask | None = None
    python_wheel_task: PythonWheelTask | None = None
    run_job_task: RunJobTask | None = None
    condition_task: ConditionTask | None = None
    libraries: list[Library] = []
    email_notifications: JobEmailNotifications | None = None
    timeout_seconds: int | None = None
    max_retries: int | None = None
    min_retry_interval_millis: int | None = None
    retry_on_timeout: bool = False

    @validator("depends_on", pre=True, each_item=True)
    def task_key_to_dependency(cls, value):
        # depends_on used to be a list of task keys, which the Jobs API rejects
        return {"task_key": value} if isinstance(value, str) else value


class CronSchedule(BaseModel):
    quartz_cron_expression: str | None = None
    timezone_id: str | None = None
    pause_status: str | None = None


class FileArrivalTriggerConfiguration(BaseModel):
    """File arrival trigger, see https://docs.databricks.com/aws/en/jobs/file-arrival-triggers

    API: `trigger.file_arrival` in https://docs.databricks.com/api/workspace/jobs/create
    """

    url: str
    min_time_between_triggers_seconds: int | None = None
    wait_after_last_change_seconds: int | None = None


class TableUpdateTriggerConfiguration(BaseModel):
    """Table update trigger, see https://docs.databricks.com/aws/en/jobs/trigger-table-update

    API: `trigger.table_update` in https://docs.databricks.com/api/workspace/jobs/create
    """

    table_names: list[str]
    condition: str | None = None
    min_time_between_triggers_seconds: int | None = None
    wait_after_last_change_seconds: int | None = None


class TriggerSettings(BaseModel):
    """Job trigger, see https://docs.databricks.com/aws/en/jobs/triggers

    API: `trigger` in https://docs.databricks.com/api/workspace/jobs/create, also sent to `/jobs/reset` on update.
    Field docs are on the TypeScript interfaces in typescript/src/resources/jobs/job.ts.
    """

    pause_status: str | None = None
    file_arrival: FileArrivalTriggerConfiguration | None = None
    table_update: TableUpdateTriggerConfiguration | None = None

    @root_validator(skip_on_failure=True)
    def check_one_trigger_type(cls, values: dict) -> dict:
        trigger_types = [name for name in ("file_arrival", "table_update") if values.get(name) is not None]
        if len(trigger_types) != 1:
            raise ValueError(
                "A job trigger must set exactly one of file_arrival or table_update, "
                f"got: {', '.join(trigger_types) or 'none'}"
            )
        return values


class AccessControlRequestForUser(BaseModel):
    user_name: str
    permission_level: str


class AccessControlRequestForGroup(BaseModel):
    group_name: str
    permission_level: str


class QueueSettings(BaseModel):
    enabled: bool


class JobParameterDefinition(BaseModel):
    name: str
    default: str


class JobSettings(BaseModel):
    name: str
    description: str | None = None
    tasks: list[JobTaskSettings]
    # Empty for a job whose tasks only run other jobs
    job_clusters: list[JobCluster] = []
    email_notifications: JobEmailNotifications | None = None
    timeout_seconds: int | None = None
    schedule: CronSchedule | None
    trigger: TriggerSettings | None = None
    queue: QueueSettings | None = None
    parameters: list[JobParameterDefinition] | None = None
    tags: dict[str, str] | None = None
    max_concurrent_runs: int | None = None
    format: str = "MULTI_TASK"
    access_control_list: list[AccessControlRequestForUser | AccessControlRequestForGroup] | None = None


class JobProperties(BaseModel):
    action: str = "job"
    workspace_url: str
    job: JobSettings


class JobResponse(CnfResponse):
    job_id: int


def get_job_url(workspace_url: str):
    """Getting url for job requests"""
    return f"{workspace_url}/api/2.1/jobs"


def get_job_by_id(job_id: str, workspace_url: str):
    body = {"job_id": job_id}
    resp = requests.get(
        f"{get_job_url(workspace_url)}/get",
        json=body,
        headers=get_authorization_headers(),
    )
    if resp.status_code == 400 and "does not exist" in resp.text:
        return None
    resp.raise_for_status()
    return resp.json()


def job_settings_body(job: JobSettings) -> dict:
    """Serialize job settings for the Jobs API.

    The fields in OPTIONAL_JOB_FIELDS and OPTIONAL_TASK_FIELDS are only sent when set, without their own
    unset fields: a trigger carries exactly one trigger type, and a task carries exactly one task type.
    The body of jobs that don't use them is unchanged.
    """
    body = json.loads(job.json(exclude={"tasks"} | OPTIONAL_JOB_FIELDS))
    for field in OPTIONAL_JOB_FIELDS:
        if getattr(job, field) is not None:
            body[field] = json.loads(job.json(include={field}, exclude_none=True))[field]

    body["tasks"] = []
    for task in job.tasks:
        task_body = json.loads(task.json(exclude=OPTIONAL_TASK_FIELDS))
        task_body["depends_on"] = [json.loads(dependency.json(exclude_none=True)) for dependency in task.depends_on]
        for field in OPTIONAL_TASK_FIELDS:
            if getattr(task, field) is not None:
                task_body[field] = json.loads(task.json(include={field}, exclude_none=True))[field]
        body["tasks"].append(task_body)
    return body


def create_or_update_job(properties: JobProperties, physical_resource_id: str | None) -> JobResponse:
    """Create job at databricks"""
    current: dict | None = None
    url = get_job_url(properties.workspace_url)
    if physical_resource_id is not None:
        current = get_job_by_id(physical_resource_id, properties.workspace_url)
    if current is None:
        create_response = post_request(f"{url}/create", body=job_settings_body(properties.job))
        job_id = create_response.get("job_id")
        return JobResponse(job_id=job_id, physical_resource_id=job_id)
    else:
        job_id = current.get("job_id")
        reset_body = {
            "job_id": job_id,
            "new_settings": job_settings_body(properties.job),
        }
        post_request(f"{url}/reset", body=reset_body)
        return JobResponse(job_id=job_id, physical_resource_id=job_id)


def delete_job(properties: JobProperties, physical_resource_id: str) -> CnfResponse:
    """Deletes job at databricks"""
    current = get_job_by_id(physical_resource_id, properties.workspace_url)
    if current is not None:
        url = get_job_url(properties.workspace_url)
        post_request(f"{url}/delete", body={"job_id": current.get("job_id")})
    else:
        logger.warning("Already removed")
    return CnfResponse(physical_resource_id=physical_resource_id)
