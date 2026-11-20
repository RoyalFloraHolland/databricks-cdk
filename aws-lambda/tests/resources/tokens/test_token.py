from unittest.mock import patch

from src.databricks_cdk.resources.tokens.token import (
    TokenInfo,
    TokenProperties,
    _create_token,
    _delete_token,
    create_or_update_token,
    get_existing_tokens,
    get_token_url,
)


def test_get_token_url():
    workspace_url = "https://test.cloud.databricks.com"

    assert get_token_url(workspace_url) == "https://test.cloud.databricks.com/api/2.0/token"


@patch("src.databricks_cdk.resources.tokens.token._create_token")
@patch("src.databricks_cdk.resources.tokens.token.get_existing_tokens")
@patch("src.databricks_cdk.resources.tokens.token.add_token_to_secrets_manager")
@patch("src.databricks_cdk.resources.tokens.token.token_exists_in_secrets_manager")
def test_create_token_not_exist(
    patched_token_exists_in_secrets_manager,
    patched_add_token_to_secrets_manager,
    patched_get_existing_tokens,
    patched__create_token,
):
    token_properties = TokenProperties(
        token_name="test",
        workspace_url="https://test.cloud.databricks.com",
        lifetime_seconds=1000,
        comment="some test token",
    )

    patched__create_token.return_value = {
        "token_value": "some_value",
        "token_info": {
            "token_id": "some_id",
            "creation_time": 1234,
            "expiry_time": 1234,
            "comment": "some test token",
        },
    }
    patched_get_existing_tokens.return_value = []

    patched_add_token_to_secrets_manager.return_value = "arn:aws::fake"
    patched_token_exists_in_secrets_manager.return_value = False

    response = create_or_update_token(token_properties)

    assert response.physical_resource_id == "some_id"

    assert patched__create_token.call_args.args == (
        "https://test.cloud.databricks.com/api/2.0/token",
        "some test token",
        1000,
    )


@patch("src.databricks_cdk.resources.tokens.token._delete_token")
@patch("src.databricks_cdk.resources.tokens.token._create_token")
@patch("src.databricks_cdk.resources.tokens.token.get_existing_tokens")
@patch("src.databricks_cdk.resources.tokens.token.update_token_in_secrets_manager")
@patch("src.databricks_cdk.resources.tokens.token.token_exists_in_secrets_manager")
def test_create_token_already_exist(
    patched_token_exists_in_secrets_manager,
    patched_update_token_to_secrets_manager,
    patched_get_existing_tokens,
    patched__create_token,
    patched__delete_token,
):
    token_properties = TokenProperties(
        token_name="test",
        workspace_url="https://test.cloud.databricks.com",
        lifetime_seconds=1000,
        comment="some test token",
    )
    patched_token_exists_in_secrets_manager.return_value = True
    patched__create_token.return_value = {
        "token_value": "some_value",
        "token_info": {
            "token_id": "some_other_id",
            "creation_time": 1234,
            "expiry_time": 1234,
            "comment": "some test token",
        },
    }
    patched_get_existing_tokens.return_value = [
        TokenInfo(token_id="existing", creation_time=1, expiry_time=2, comment="blah")
    ]

    patched_update_token_to_secrets_manager.return_value = "fake_arn"

    response = create_or_update_token(token_properties, physical_resource_id="existing")

    assert response.physical_resource_id == "some_other_id"

    assert patched__create_token.call_args.args == (
        "https://test.cloud.databricks.com/api/2.0/token",
        "some test token",
        1000,
    )


@patch("src.databricks_cdk.resources.tokens.token.get_request")
def test_get_existing_token(patched_get_request):
    patched_get_request.return_value = {
        "token_infos": [
            {
                "token_id": "test",
                "creation_time": 1,
                "expiry_time": 2,
                "comment": "test_comment",
            }
        ]
    }

    token_list = get_existing_tokens(token_url="https://test.cloud.databricks.com/api/2.0/token")

    assert len(token_list) == 1
    assert isinstance(token_list[0], TokenInfo)
    assert token_list[0].comment == "test_comment"
    assert token_list[0].token_id == "test"
    assert token_list[0].creation_time == 1
    assert token_list[0].expiry_time == 2


@patch("src.databricks_cdk.resources.tokens.token.post_request")
def test__create_token(patched_post_request):
    _create_token(
        "https://test.cloud.databricks.com/api/2.0/token",
        comment="test_comment",
        lifetime_seconds=1,
    )

    assert patched_post_request.call_args.kwargs == {"body": {"comment": "test_comment", "lifetime_seconds": 1}}


@patch("src.databricks_cdk.resources.tokens.token.post_request")
def test__delete_token(patched_post_request):
    _delete_token("https://test.cloud.databricks.com/api/2.0/token", token_id="test_id")

    assert patched_post_request.call_args.kwargs == {
        "url": "https://test.cloud.databricks.com/api/2.0/token/delete",
        "body": {"token_id": "test_id"},
    }
