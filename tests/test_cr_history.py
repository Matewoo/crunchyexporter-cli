import pytest
from unittest.mock import MagicMock
from src.crunchyroll.history import CRHistory
from src.crunchyroll.models import CRToken


def make_history() -> CRHistory:
    token = CRToken(access_token="x", refresh_token="y", account_id="123")
    h = object.__new__(CRHistory)
    h.token = token
    return h


def make_raw_item(ep_id: str, series_id: str = "S1", ep_num: float = 1.0) -> dict:
    return {
        "date_played": "2026-01-01T00:00:00Z",
        "fully_watched": True,
        "panel": {
            "id": ep_id,
            "title": f"Episode {ep_num}",
            "episode_metadata": {
                "series_id": series_id,
                "series_title": f"Series {series_id}",
                "season_number": 1,
                "episode_number": ep_num,
            },
        },
    }


def test_fetch_all_stops_at_existing_episode():
    h = make_history()
    # Mock _fetch_page to return page 1 with episodes EP3, EP2, and next_page pointing to page 2
    page1 = {
        "data": [make_raw_item("EP3", ep_num=3.0), make_raw_item("EP2", ep_num=2.0)],
        "meta": {"next_page": "/content/v2/acc/watch-history?page=2"},
    }
    page2 = {
        "data": [make_raw_item("EP1", ep_num=1.0)],
        "meta": {},
    }

    def fake_fetch_page(url, params):
        if "page=2" in str(url):
            return page2
        return page1

    h._fetch_page = MagicMock(side_effect=fake_fetch_page)

    # When stop_at_existing contains "EP2", it should yield EP3 and stop immediately without fetching page 2
    eps = h.fetch_all(stop_at_existing={"EP2"})
    assert len(eps) == 1
    assert eps[0].episode_id == "EP3"
    assert h._fetch_page.call_count == 1


def test_fetch_all_without_stop_fetches_all():
    h = make_history()
    page1 = {
        "data": [make_raw_item("EP3", ep_num=3.0), make_raw_item("EP2", ep_num=2.0)],
        "meta": {},
    }

    h._fetch_page = MagicMock(return_value=page1)
    eps = h.fetch_all()
    assert len(eps) == 2
    assert [ep.episode_id for ep in eps] == ["EP3", "EP2"]
