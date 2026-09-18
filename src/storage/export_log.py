import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence
from src.crunchyroll.models import SeriesSummary

DEFAULT_PATH = Path("data") / "export_log.json"


class ExportLog:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def record(self, target: str, result, series: Sequence[SeriesSummary] | None = None) -> None:
        self._data["last_export"] = datetime.now(timezone.utc).isoformat()
        targets = self._data.setdefault("targets", {})
        target_info = targets.setdefault(target, {})
        target_info.update({
            "updated": len(result.updated),
            "skipped": len(result.skipped),
            "failed": [[t, r] for t, r in result.failed],
        })

        if series:
            series_progress = target_info.setdefault("series", {})
            updated_ids = getattr(result, "updated_ids", set())
            now_str = datetime.now(timezone.utc).isoformat()
            for s in series:
                # If updated_ids is tracked, record only updated series; otherwise fallback to all if updated was non-empty
                if not updated_ids or s.series_id in updated_ids:
                    series_progress[s.series_id] = {
                        "series_title": s.series_title,
                        "max_episode": s.max_episode,
                        "last_exported_at": now_str,
                    }

        self.save()

    def filter_series_for_export(
        self, target: str, series: Sequence[SeriesSummary], mode: str = "all"
    ) -> list[SeriesSummary]:
        if mode != "onlynew":
            return list(series)

        target_info = self.get_target(target) or {}
        recorded_series = target_info.get("series", {})

        filtered = []
        for s in series:
            prev = recorded_series.get(s.series_id)
            if prev is None:
                # Never exported to this target before
                filtered.append(s)
            elif s.max_episode > prev.get("max_episode", 0):
                # New episodes watched since last export to this target
                filtered.append(s)

        return filtered

    @property
    def last_export(self) -> str | None:
        return self._data.get("last_export")

    def get_target(self, target: str) -> dict | None:
        return self._data.get("targets", {}).get(target)
