import json
from unittest.mock import MagicMock, patch

from databricks_cdk.resources.cluster_policies.cluster_policy import (
    ClusterPolicy,
    ClusterPolicyProperties,
    create_or_update_cluster_policy,
    delete_cluster_policy,
)

WORKSPACE_URL = "https://dbc-test.cloud.databricks.com"
CLUSTER_POLICY_URL = f"{WORKSPACE_URL}/api/2.0/policies/clusters"


@patch("databricks_cdk.resources.cluster_policies.cluster_policy.get_request")
@patch("databricks_cdk.resources.cluster_policies.cluster_policy.post_request")
def test_create_cluster_policy(mock_request: MagicMock, mock_get_request: MagicMock):
    definition = {
        "test": {
            "type": "regex",
            "value": 10,
            "pattern": "*",
            "hidden": "true",
        }
    }
    cluster_policy = ClusterPolicy(name="Test Policy", definition=definition, description="test create policy")
    properties = ClusterPolicyProperties(workspace_url=WORKSPACE_URL, cluster_policy=cluster_policy)
    mock_request.return_value = {"policy_id": "12345"}
    expected_body = {
        "definition": """{"test": {"type": "regex", "value": 10, "hidden": true, "pattern": "*"}}""",
        "description": "test create policy",
        "name": "Test Policy",
    }
    response = create_or_update_cluster_policy(properties=properties, physical_resource_id=None)
    mock_request.assert_called_once_with(url=f"{CLUSTER_POLICY_URL}/create", body=expected_body)
    assert response.physical_resource_id == "12345"


@patch("databricks_cdk.resources.cluster_policies.cluster_policy.get_request")
@patch("databricks_cdk.resources.cluster_policies.cluster_policy.post_request")
def test_update_cluster_policy(mock_post_request: MagicMock, mock_get_request: MagicMock):
    definition = {
        "spark_conf.spark.databricks.cluster.profile": {
            "type": "forbidden",
            "hidden": True,
        }
    }
    cluster_policy = ClusterPolicy(name="Update Policy", definition=definition, description="test update policy")
    properties = ClusterPolicyProperties(workspace_url=WORKSPACE_URL, cluster_policy=cluster_policy)
    expected_body = {
        "definition": json.dumps(definition),
        "description": "test update policy",
        "name": "Update Policy",
        "policy_id": "12345",
    }

    policy_id_return_value = {"policy_id": expected_body["policy_id"]}

    mock_get_request.return_value = policy_id_return_value
    mock_post_request.return_value = policy_id_return_value

    response = create_or_update_cluster_policy(properties=properties, physical_resource_id="12345")

    mock_get_request.assert_called_once_with(url=f"{CLUSTER_POLICY_URL}/get", body=policy_id_return_value)
    mock_post_request.assert_called_once_with(url=f"{CLUSTER_POLICY_URL}/edit", body=expected_body)
    assert response.physical_resource_id == "12345"


@patch("databricks_cdk.resources.cluster_policies.cluster_policy.get_request")
@patch("databricks_cdk.resources.cluster_policies.cluster_policy.post_request")
def test_delete_cluster_policy(mock_delete_request: MagicMock, mock_get_request: MagicMock):
    definition = {
        "spark_conf.spark.databricks.cluster.profile": {
            "type": "forbidden",
            "hidden": True,
        }
    }
    cluster_policy = ClusterPolicy(name="Updated Policy", definition=definition, description="test update policy")
    properties = ClusterPolicyProperties(workspace_url=WORKSPACE_URL, cluster_policy=cluster_policy)
    policy_id = {"policy_id": "12345"}
    mock_get_request.return_value = policy_id
    mock_delete_request.return_value = policy_id

    response = delete_cluster_policy(properties=properties, physical_resource_id="12345")

    mock_get_request.assert_called_once_with(url=f"{CLUSTER_POLICY_URL}/get", body=policy_id)
    mock_delete_request.assert_called_once_with(url=f"{CLUSTER_POLICY_URL}/delete", body=policy_id)
    assert response.physical_resource_id == "12345"
