from unittest.mock import patch

import pytest
from pydantic import ValidationError

from databricks_cdk.resources.jobs.job import (
    AwsAttributes,
    FileArrivalTriggerConfiguration,
    JobCluster,
    JobProperties,
    JobSettings,
    JobTaskSettings,
    NewCluster,
    TableUpdateTriggerConfiguration,
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
