import requests
from typing import Iterator
from .models import CRToken, Episode

CR_CONTENT_BASE = "https://beta-api.crunchyroll.com/content/v2"
PAGE_SIZE = 100


class CRHistory:
    def __init__(self, token: CRToken):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token.access_token}",
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
        })

    def fetch_all(self, locale: str = "en-US", stop_at_existing: set[str] | None = None) -> list[Episode]:
        episodes = []
        for ep in self._paginate(locale, stop_at_existing=stop_at_existing):
            episodes.append(ep)
        return episodes

    def _paginate(self, locale: str, stop_at_existing: set[str] | None = None) -> Iterator[Episode]:
        stop_ids = stop_at_existing or set()
        next_url: str | None = f"{CR_CONTENT_BASE}/{self.token.account_id}/watch-history"
        params: dict | None = {"page_size": PAGE_SIZE, "locale": locale}

        while next_url:
            resp_data = self._fetch_page(next_url, params)
            items = resp_data.get("data", [])
            if not items:
                break

            for item in items:
                ep = self._parse_item(item)
                if ep:
                    if ep.episode_id in stop_ids:
                        return
                    yield ep

            next_page = resp_data.get("meta", {}).get("next_page")
            if next_page:
                if next_page.startswith("http"):
                    next_url = next_page
                else:
                    next_url = f"https://beta-api.crunchyroll.com{next_page}"
                params = None  # query params are already encoded in next_page URL
            else:
                break

    def _fetch_page(self, url_or_page: str | int, locale_or_params: str | dict | None = None) -> dict:
        if isinstance(url_or_page, str) and url_or_page.startswith("http"):
            url = url_or_page
            params = locale_or_params if isinstance(locale_or_params, dict) else None
        else:
            # Backward compatibility if called with (page: int, locale: str)
            url = f"{CR_CONTENT_BASE}/{self.token.account_id}/watch-history"
            params = {
                "page_size": PAGE_SIZE,
                "locale": locale_or_params if isinstance(locale_or_params, str) else "en-US",
            }
            if url_or_page != 1:
                params["page"] = url_or_page

        resp = self.session.get(url, params=params, timeout=20)
        if not resp.ok:
            raise RuntimeError(f"History fetch failed {resp.status_code}: {resp.text}")
        return resp.json()

    def _parse_item(self, item: dict) -> Episode | None:
        panel = item.get("panel", {})
        if not panel:
            return None

        ep_meta = panel.get("episode_metadata", {})
        series_meta = ep_meta if ep_meta else panel

        series_id = ep_meta.get("series_id") or panel.get("id", "")
        series_title = ep_meta.get("series_title") or panel.get("title", "unknown")

        try:
            season_number = int(ep_meta.get("season_number") or 1)
        except (ValueError, TypeError):
            season_number = 1

        try:
            episode_number = float(ep_meta.get("episode_number") or 0)
        except (ValueError, TypeError):
            episode_number = 0.0

        return Episode(
            series_id=series_id,
            series_title=series_title,
            season_number=season_number,
            episode_number=episode_number,
            episode_title=panel.get("title", ""),
            episode_id=panel.get("id", ""),
            watched_at=item.get("date_played"),
            fully_watched=item.get("fully_watched", False),
        )
