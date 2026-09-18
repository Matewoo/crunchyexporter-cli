import pytest
from pathlib import Path
from src.crunchyroll.models import SeriesSummary
from src.exporters.base import ExportResult
from src.storage.export_log import ExportLog


def make_summary(series_id="S1", title="Title 1", max_ep=5):
    s = SeriesSummary(series_id=series_id, series_title=title)
    s.max_episode = max_ep
    return s


def test_export_log_initial_empty(tmp_path):
    log = ExportLog(tmp_path / "export_log.json")
    assert log.last_export is None
    assert log.get_target("anilist") is None


def test_export_log_record_with_series(tmp_path):
    log = ExportLog(tmp_path / "export_log.json")
    result = ExportResult()
    result.updated.append("Title 1")
    result.updated_ids.add("S1")

    s1 = make_summary("S1", "Title 1", 5)
    s2 = make_summary("S2", "Title 2", 3)

    log.record("anilist", result, series=[s1, s2])

    target = log.get_target("anilist")
    assert target is not None
    assert target["updated"] == 1
    assert "S1" in target["series"]
    assert target["series"]["S1"]["max_episode"] == 5
    # S2 was not in updated_ids, so it should not be marked as updated
    assert "S2" not in target["series"]


def test_filter_series_for_export_all_mode(tmp_path):
    log = ExportLog(tmp_path / "export_log.json")
    s1 = make_summary("S1", "Title 1", 5)
    result = ExportResult()
    result.updated.append("Title 1")
    result.updated_ids.add("S1")
    log.record("anilist", result, series=[s1])

    summaries = [s1]
    filtered = log.filter_series_for_export("anilist", summaries, mode="all")
    assert len(filtered) == 1


def test_filter_series_for_export_onlynew_mode(tmp_path):
    log = ExportLog(tmp_path / "export_log.json")
    s1 = make_summary("S1", "Title 1", 5)
    result = ExportResult()
    result.updated.append("Title 1")
    result.updated_ids.add("S1")
    log.record("anilist", result, series=[s1])

    # Case 1: Same episode progress -> should be filtered out
    s1_same = make_summary("S1", "Title 1", 5)
    filtered = log.filter_series_for_export("anilist", [s1_same], mode="onlynew")
    assert len(filtered) == 0

    # Case 2: Progress increased -> should be included
    s1_new_ep = make_summary("S1", "Title 1", 6)
    filtered = log.filter_series_for_export("anilist", [s1_new_ep], mode="onlynew")
    assert len(filtered) == 1
    assert filtered[0].max_episode == 6

    # Case 3: Brand new series -> should be included
    s2_new = make_summary("S2", "Title 2", 1)
    filtered = log.filter_series_for_export("anilist", [s1_same, s2_new], mode="onlynew")
    assert len(filtered) == 1
    assert filtered[0].series_id == "S2"
