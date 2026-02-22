import json
from pathlib import Path
from unittest.mock import MagicMock


def test_process_one_cycle_productive(mocker, fake_image, tmp_path):
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

    from main import process_one_cycle

    result = process_one_cycle("Write code", False, "Patrick", 15, "User", tmp_path)

    assert result == "productive"
    mock_sequence.assert_not_called()

    # Verify audit log was written
    log_file = tmp_path / "session.jsonl"
    assert log_file.exists()
    entry = json.loads(log_file.read_text().strip())
    assert entry["determination"] == "productive"
    assert "heckler" not in entry


def test_process_one_cycle_procrastinating(mocker, fake_image, tmp_path):
    """When procrastinating, process_one_cycle should trigger procrastination_sequence."""
    mocker.patch("main.take_screenshots", return_value=[{"filepath": fake_image, "timestamp": "t"}])

    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps({"determination": "procrastinating"})))
    ]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mocker.patch("main.client", mock_client)

    mock_sequence = mocker.patch("main.procrastination_sequence", return_value=("Stop it!", "", "twitter"))

    from main import process_one_cycle

    result = process_one_cycle("Write code", True, "Patrick", 15, "User", tmp_path)

    assert result == "procrastinating"
    mock_sequence.assert_called_once()

    # Verify audit log includes procrastination fields
    entry = json.loads((tmp_path / "session.jsonl").read_text().strip())
    assert entry["determination"] == "procrastinating"
    assert entry["heckler"] == "Stop it!"
    assert entry["countdown_word"] == "twitter"


def test_process_one_cycle_moves_screenshots(mocker, fake_image, tmp_path):
    """Screenshots should be moved to log dir after each cycle."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    mocker.patch("main.take_screenshots", return_value=[{"filepath": fake_image, "timestamp": "t"}])
    mocker.patch("main.determine_productivity", return_value="productive")

    from main import process_one_cycle

    process_one_cycle("Write code", False, "Patrick", 15, "User", log_dir)

    # Screenshot should be moved to log dir
    moved = log_dir / Path(fake_image).name
    assert moved.exists()
    # Original should be gone
    assert not Path(fake_image).exists()
