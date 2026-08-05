# services/eso_data_service.py
from __future__ import annotations

import json
from pathlib import Path


class EsoAchievementDataService:
    """Read-only access to the parsed ESO achievement data (tree + details).

    tree.json: top_category -> subcategory -> {index: [achievement_ids]}
    achievements.json: achievement_id (str) -> {name, desc, points, criteria, ...}
    """

    def __init__(self, tree_path: Path, achievements_path: Path) -> None:
        self.tree_path = tree_path
        self.achievements_path = achievements_path
        self._tree: dict | None = None
        self._achievements: dict | None = None

    def _ensure_loaded(self) -> None:
        if self._tree is None:
            self._tree = json.loads(self.tree_path.read_text(encoding="utf-8"))
        if self._achievements is None:
            self._achievements = json.loads(self.achievements_path.read_text(encoding="utf-8"))

    def top_categories(self) -> list[str]:
        self._ensure_loaded()
        return list(self._tree.keys())

    def subcategories(self, category: str) -> list[str]:
        self._ensure_loaded()
        return list(self._tree.get(category, {}).keys())

    def achievements_in(self, category: str, subcategory: str) -> list[dict]:
        """Returns achievement dicts (id, name, desc, points) in the game's own
        display order for this category/subcategory."""
        self._ensure_loaded()
        index_map = self._tree.get(category, {}).get(subcategory, {})
        # index_map keys are string numbers ("1", "2", ...) - sort numerically
        results = []
        for index in sorted(index_map.keys(), key=lambda k: int(k)):
            for achievement_id in index_map[index]:
                record = self._achievements.get(str(achievement_id))
                if record:
                    results.append({
                        "id": achievement_id,
                        "name": record.get("name", ""),
                        "desc": record.get("desc", ""),
                        "points": record.get("points", 0),
                    })
        return results

    def search(self, query: str) -> list[dict]:
        """Case-insensitive search across all achievement names. Returns
        dicts including which category/subcategory each result lives in."""
        self._ensure_loaded()
        query_lower = query.lower().strip()
        if not query_lower:
            return []
        results = []
        for category, subcats in self._tree.items():
            for subcategory, index_map in subcats.items():
                for index in index_map.values():
                    for achievement_id in index:
                        record = self._achievements.get(str(achievement_id))
                        if record and query_lower in record.get("name", "").lower():
                            results.append({
                                "id": achievement_id,
                                "name": record.get("name", ""),
                                "desc": record.get("desc", ""),
                                "points": record.get("points", 0),
                                "category": category,
                                "subcategory": subcategory,
                            })
        return results
