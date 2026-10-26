from unittest.mock import patch

import pytest
from pydantic import ValidationError

from databricks_cdk.resources.jobs.job import (
    AwsAttributes,
    ConditionTask,
    FileArrivalTriggerConfiguration,
    JobCluster,
    JobProperties,
    JobSettings,
    JobTaskSettings,
    NewCluster,
    QueueSettings,
    RunJobTask,
    TableUpdateTriggerConfiguration,
    TaskDependency,
    TriggerSettings,
    create_or_update_job,
    job_settings_body,
)


def get_job_settings(trigger=None) -> JobSettings:
    return JobSettings(
        name="job",
        tasks=[JobTaskSettings(task_key="task", job_cluster_key="cluster")],
        job_clusters=[
            JobCluster(
                job_cluster_key="cluster",
                new_cluster=NewCluster(spark_version="17.3.x-scala2.13", aws_attributes=AwsAttributes()),
            )
        ],
        trigger=trigger,
    )


def test_job_settings_body_without_trigger():
    body = job_settings_body(get_job_settings())

    assert "trigger" not in body
    assert body["schedule"] is None
    assert body["name"] == "job"


def test_job_settings_body_leaves_out_unset_orchestration_fields():
    body = job_settings_body(get_job_settings())

    for field in ("description", "queue", "parameters", "tags"):
        assert field not in body
    task = body["tasks"][0]
    for field in ("run_if", "run_job_task", "condition_task"):
        assert field not in task
    assert task["depends_on"] == []
    assert task["spark_python_task"] is None
    assert task["job_cluster_key"] == "cluster"


def test_job_settings_body_run_job_chain():
    job = JobSettings(
        name="chain",
        tasks=[
            JobTaskSettings(task_key="check", run_job_task=RunJobTask(job_id=1)),
            JobTaskSettings(
                task_key="gate",
                depends_on=[TaskDependency(task_key="check")],
                condition_task=ConditionTask(left="{{tasks.check.values.ok}}", op="EQUAL_TO", right="true"),
            ),
            JobTaskSettings(
                task_key="work",
                depends_on=[TaskDependency(task_key="gate", outcome="true")],
                run_if="ALL_SUCCESS",
                run_job_task=RunJobTask(job_id=2, python_params=["data", "--date", "2026-10-26"]),
            ),
        ],
        queue=QueueSettings(enabled=True),
        tags={"Application": "troll"},
    )

    body = job_settings_body(job)

    assert body["job_clusters"] == []
    assert body["queue"] == {"enabled": True}
    assert body["tags"] == {"Application": "troll"}
    check, gate, work = body["tasks"]
    assert check["run_job_task"] == {"job_id": 1}
    assert "condition_task" not in check
    assert gate["depends_on"] == [{"task_key": "check"}]
    assert gate["condition_task"] == {"left": "{{tasks.check.values.ok}}", "op": "EQUAL_TO", "right": "true"}
    assert "run_job_task" not in gate
    assert work["depends_on"] == [{"task_key": "gate", "outcome": "true"}]
    assert work["run_if"] == "ALL_SUCCESS"
    assert work["run_job_task"] == {"job_id": 2, "python_params": ["data", "--date", "2026-10-26"]}


def test_job_settings_parses_run_job_chain_from_cloudformation_properties():
    properties = JobProperties(
        workspace_url="https://test.cloud.databricks.com",
        job={
            "name": "chain",
            "tasks": [
                {"task_key": "first", "run_job_task": {"job_id": "123"}},
                {"task_key": "second", "depends_on": ["first"], "run_job_task": {"job_id": "456"}},
            ],
            "queue": {"enabled": "true"},
        },
    )

    first, second = properties.job.tasks
    assert first.run_job_task.job_id == 123
    assert second.depends_on == [TaskDependency(task_key="first")]
    assert properties.job.job_clusters == []
    assert properties.job.queue.enabled is True


def test_job_settings_body_file_arrival_trigger():
    trigger = TriggerSettings(
        pause_status="UNPAUSED",
        file_arrival=FileArrivalTriggerConfiguration(url="/Volumes/catalog/schema/volume/"),
    )

    body = job_settings_body(get_job_settings(trigger))

    assert body["trigger"] == {
        "pause_status": "UNPAUSED",
        "file_arrival": {"url": "/Volumes/catalog/schema/volume/"},
    }


def test_job_settings_body_table_update_trigger():
    trigger = TriggerSettings(
        table_update=TableUpdateTriggerConfiguration(table_names=["catalog.schema.table"], condition="ANY_UPDATED"),
    )

    body = job_settings_body(get_job_settings(trigger))

    assert body["trigger"] == {"table_update": {"table_names": ["catalog.schema.table"], "condition": "ANY_UPDATED"}}


def test_job_settings_parses_trigger_from_cloudformation_properties():
    properties = JobProperties(
        workspace_url="https://test.cloud.databricks.com",
        job={
            "name": "job",
            "tasks": [{"task_key": "task"}],
            "job_clusters": [],
            "trigger": {"file_arrival": {"url": "s3://bucket/prefix/", "wait_after_last_change_seconds": "60"}},
        },
    )

    assert properties.job.trigger.file_arrival.url == "s3://bucket/prefix/"
    assert properties.job.trigger.file_arrival.wait_after_last_change_seconds == 60


def test_trigger_settings_rejects_both_trigger_types():
    with pytest.raises(ValidationError, match="got: file_arrival, table_update"):
        TriggerSettings(
            file_arrival=FileArrivalTriggerConfiguration(url="/Volumes/catalog/schema/volume/"),
            table_update=TableUpdateTriggerConfiguration(table_names=["catalog.schema.table"]),
        )


def test_trigger_settings_rejects_no_trigger_type():
    with pytest.raises(ValidationError, match="got: none"):
        TriggerSettings(pause_status="UNPAUSED")


def test_job_properties_rejects_invalid_trigger_from_cloudformation_properties():
    with pytest.raises(ValidationError, match="exactly one of file_arrival or table_update"):
        JobProperties(
            workspace_url="https://test.cloud.databricks.com",
            job={
                "name": "job",
                "tasks": [{"task_key": "task"}],
                "job_clusters": [],
                "trigger": {
                    "file_arrival": {"url": "s3://bucket/prefix/"},
                    "table_update": {"table_names": ["catalog.schema.table"]},
                },
            },
        )


@patch("databricks_cdk.resources.jobs.job.post_request")
@patch("databricks_cdk.resources.jobs.job.get_job_by_id")
def test_create_or_update_job_resets_with_trigger(patched_get_job_by_id, patched_post_request):
    patched_get_job_by_id.return_value = {"job_id": 123}
    trigger = TriggerSettings(file_arrival=FileArrivalTriggerConfiguration(url="/Volumes/catalog/schema/volume/"))
    properties = JobProperties(workspace_url="https://test.cloud.databricks.com", job=get_job_settings(trigger))

    create_or_update_job(properties, physical_resource_id="123")

    patched_post_request.assert_called_once()
    url = patched_post_request.call_args.args[0]
    body = patched_post_request.call_args.kwargs["body"]
    assert url.endswith("/reset")
    assert body["job_id"] == 123
    assert body["new_settings"]["trigger"] == {"file_arrival": {"url": "/Volumes/catalog/schema/volume/"}}
