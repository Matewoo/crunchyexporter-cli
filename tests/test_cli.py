import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from src.main import cli
from src.crunchyroll.models import Episode, SeriesSummary
from src.exporters.base import ExportResult


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "sync" in result.output
    assert "fetch" in result.output
    assert "export" in result.output


def test_cli_fetch_mode_option():
    runner = CliRunner()
    result = runner.invoke(cli, ["fetch", "--help"])
    assert result.exit_code == 0
    assert "--mode" in result.output
    assert "--exportmode" in result.output


def test_cli_export_mode_option():
    runner = CliRunner()
    result = runner.invoke(cli, ["export", "--help"])
    assert result.exit_code == 0
    assert "--mode" in result.output
    assert "--exportmode" in result.output


def test_cli_sync_mode_option():
    runner = CliRunner()
    result = runner.invoke(cli, ["sync", "--help"])
    assert result.exit_code == 0
    assert "--mode" in result.output
    assert "--exportmode" in result.output


@patch("src.main.CRHistory")
@patch("src.main.CRAuth")
def test_fetch_onlynew_passes_existing_ids(mock_auth, mock_history_cls, tmp_path):
    store_file = tmp_path / "history.json"
    runner = CliRunner()

    # Pre-populate history with an existing episode
    from src.storage.history_store import HistoryStore
    store = HistoryStore(store_file)
    ep = Episode(
        series_id="S1", series_title="Anime 1", season_number=1,
        episode_number=1.0, episode_title="Ep 1", episode_id="EP1"
    )
    store.update([ep])

    mock_auth_instance = MagicMock()
    mock_auth.return_value = mock_auth_instance
    mock_auth_instance.login_with_etp_rt.return_value = MagicMock(account_id="acc123")

    mock_history_instance = MagicMock()
    mock_history_cls.return_value = mock_history_instance
    mock_history_instance.fetch_all.return_value = []

    config_file = tmp_path / "config.yaml"
    config_file.write_text(f"""
storage:
  path: "{store_file}"
crunchyroll:
  etp_rt: "fake-cookie"
""")

    result = runner.invoke(cli, ["-c", str(config_file), "fetch", "--mode", "onlynew"])
    assert result.exit_code == 0

    # Ensure fetch_all was called with stop_at_existing containing "EP1"
    mock_history_instance.fetch_all.assert_called_once()
    kwargs = mock_history_instance.fetch_all.call_args.kwargs
    assert kwargs.get("stop_at_existing") == {"EP1"}
