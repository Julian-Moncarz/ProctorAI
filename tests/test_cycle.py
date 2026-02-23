import json
from pathlib import Path
from unittest.mock import MagicMock


def test_process_one_cycle_productive(mocker, fake_image, tmp_path):
    """When productive, process_one_cycle should not show popup."""
    mocker.patch("main.take_screenshots", return_value=[{"filepath": fake_image, "timestamp": "t"}])
    mocker.patch("main._load_memory", return_value="test memory")

    # Mock Anthropic client to return productive determination
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.input = {"reasoning": "Working on task", "determination": "productive", "heckler_message": ""}
    mock_response = MagicMock()
    mock_response.content = [tool_block]
    mocker.patch("main.client").messages.create.return_value = mock_response

    mock_popup = mocker.patch("main.ProcrastinationEvent")

    from main import process_one_cycle
    result = process_one_cycle("Write code", False, "Patrick", 15, "User", tmp_path)

    assert result == "productive"
    mock_popup.assert_not_called()

    log_file = tmp_path / "session.jsonl"
    assert log_file.exists()
    entry = json.loads(log_file.read_text().strip())
    assert entry["determination"] == "productive"
    assert "heckler" not in entry


def test_process_one_cycle_procrastinating(mocker, fake_image, tmp_path):
    """When procrastinating, process_one_cycle should show popup."""
    mocker.patch("main.take_screenshots", return_value=[{"filepath": fake_image, "timestamp": "t"}])
    mocker.patch("main._load_memory", return_value="test memory")

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.input = {"reasoning": "On Twitter", "determination": "procrastinating", "heckler_message": "Get back to work!"}
    mock_response = MagicMock()
    mock_response.content = [tool_block]
    mocker.patch("main.client").messages.create.return_value = mock_response

    mock_event = MagicMock()
    mocker.patch("main.ProcrastinationEvent", return_value=mock_event)

    from main import process_one_cycle
    result = process_one_cycle("Write code", False, "Patrick", 15, "User", tmp_path)

    assert result == "procrastinating"
    mock_event.show_popup.assert_called_once_with("Get back to work!")

    entry = json.loads((tmp_path / "session.jsonl").read_text().strip())
    assert entry["determination"] == "procrastinating"
    assert entry["heckler"] == "Get back to work!"


def test_process_one_cycle_moves_screenshots(mocker, fake_image, tmp_path):
    """Screenshots should be moved to log dir after each cycle."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    mocker.patch("main.take_screenshots", return_value=[{"filepath": fake_image, "timestamp": "t"}])
    mocker.patch("main._load_memory", return_value="test memory")

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.input = {"reasoning": "Working", "determination": "productive", "heckler_message": ""}
    mock_response = MagicMock()
    mock_response.content = [tool_block]
    mocker.patch("main.client").messages.create.return_value = mock_response

    from main import process_one_cycle
    process_one_cycle("Write code", False, "Patrick", 15, "User", log_dir)

    moved = log_dir / Path(fake_image).name
    assert moved.exists()
    assert not Path(fake_image).exists()
