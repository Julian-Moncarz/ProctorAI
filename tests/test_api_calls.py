from unittest.mock import MagicMock


def test_make_api_call_with_images(fake_image, mocker):
    """make_api_call should include image content when image_paths provided."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="response"))]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    mocker.patch("main.client", mock_client)

    from main import make_api_call

    result = make_api_call("heckler", "prompt", image_paths=[fake_image])
    assert result["role"] == "heckler"

    # Verify the messages included image content
    call_kwargs = mock_client.chat.completions.create.call_args
    messages = call_kwargs.kwargs["messages"]
    user_msg = messages[-1]
    assert isinstance(user_msg["content"], list)
    assert any(item.get("type") == "image_url" for item in user_msg["content"])


def test_parallel_api_calls_returns_all_results(mocker):
    """parallel_api_calls should return results for all params."""
    mocker.patch("main.make_api_call", side_effect=[
        {"role": "heckler", "result": "msg1"},
        {"role": "pledge", "result": "msg2"},
        {"role": "countdown", "result": "msg3"},
    ])

    from main import parallel_api_calls

    params = [
        {"role": "heckler", "user_prompt": "p1"},
        {"role": "pledge", "user_prompt": "p2"},
        {"role": "countdown", "user_prompt": "p3"},
    ]
    results = parallel_api_calls(params)

    assert len(results) == 3
    roles = {r["role"] for r in results}
    assert roles == {"heckler", "pledge", "countdown"}
