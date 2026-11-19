from pydantic import BaseModel

from databricks_cdk.utils import get_request


class StatusJobEvent(BaseModel):
    workspace_url: str
    run_id: int


def handler(event, context):
    parsed_event = StatusJobEvent.model_validate(event)
    url = f"{parsed_event.workspace_url}/api/2.1/jobs/runs/get"
    return get_request(url, params={"run_id": parsed_event.run_id})
