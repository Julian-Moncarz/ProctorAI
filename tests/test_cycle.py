import json
from unittest.mock import MagicMock


def test_process_one_cycle_productive(mocker, fake_image):
    """When productive, process_one_cycle should not trigger procrastination_sequence."""
    mocker.patch("main.take_screenshots", return_value=[{"filepath": fake_image, "timestamp": "t"}])

    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps({"determination": "productive"})))
    ]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mocker.patch("main.client", mock_client)

    mock_sequence = mocker.patch("main.procrastination_sequence")
    mocker.patch("main.os.remove")

    from main import process_one_cycle

    result = process_one_cycle("Write code", False, "Patrick", 15, "User")

    assert result == "productive"
    mock_sequence.assert_not_called()


def test_process_one_cycle_procrastinating(mocker, fake_image):
    """When procrastinating, process_one_cycle should trigger procrastination_sequence."""
    mocker.patch("main.take_screenshots", return_value=[{"filepath": fake_image, "timestamp": "t"}])

    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps({"determination": "procrastinating"})))
    ]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mocker.patch("main.client", mock_client)

    mock_sequence = mocker.patch("main.procrastination_sequence")
    mocker.patch("main.os.remove")

    from main import process_one_cycle

    result = process_one_cycle("Write code", True, "Patrick", 15, "User")

    assert result == "procrastinating"
    mock_sequence.assert_called_once()


def test_process_one_cycle_cleans_up_screenshots(mocker, fake_image):
    """Screenshots should be deleted after each cycle."""
    mocker.patch("main.take_screenshots", return_value=[
        {"filepath": "/tmp/s1.png", "timestamp": "t"},
        {"filepath": "/tmp/s2.png", "timestamp": "t"},
    ])

    mocker.patch("main.determine_productivity", return_value="productive")
    mock_remove = mocker.patch("main.os.remove")

    from main import process_one_cycle

    process_one_cycle("Write code", False, "Patrick", 15, "User")

    assert mock_remove.call_count == 2
    mock_remove.assert_any_call("/tmp/s1.png")
    mock_remove.assert_any_call("/tmp/s2.png")
