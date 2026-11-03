from pydantic import BaseModel

from databricks_cdk.utils import post_request


class JobArgs(BaseModel):
    job_id: int
    idempotency_token: str | None
    jar_params: list[str] | None
    notebook_params: dict | None
    python_params: list[str] | None
    spark_submit_params: list[str] | None
    python_named_params: dict | None


class SubmitJobEvent(BaseModel):
    workspace_url: str
    job_args: JobArgs


def handler(event, context):
    parsed_event = SubmitJobEvent.parse_obj(event)
    url = f"{parsed_event.workspace_url}/api/2.1/jobs/run-now"
    return post_request(url, body=parsed_event.job_args.dict())
