from __future__ import annotations

import json
from pathlib import Path

from services.achievement_progress_service import AchievementProgressService
from services import profiled_collectible_service
from ui import collectibles_profile_support


def test_achievement_legacy_progress_migrates_to_default_profile(tmp_path: Path) -> None:
    path = tmp_path / "achievement_progress.json"
    path.write_text(json.dumps({"Completed": [10, 20]}), encoding="utf-8")

    service = AchievementProgressService(path)

    assert service.active_profile == "Default"
    assert service.completed_ids() == {"10", "20"}
    service.ensure_profile("Jarakeen")
    service.set_active_profile("Jarakeen")
    service.set_complete(30, True)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["Version"] == 2
    assert payload["Profiles"]["Default"]["Completed"] == ["10", "20"]
    assert payload["Profiles"]["Jarakeen"]["Completed"] == ["30"]


def test_achievement_merge_does_not_delete_local_progress(tmp_path: Path) -> None:
    path = tmp_path / "achievement_progress.json"
    service = AchievementProgressService(path)
    service.ensure_profile("Ryan")
    service.set_active_profile("Ryan")
    service.set_complete(100, True)

    added = service.merge_completed("Ryan", [100, 200, 300])

    assert added == 2
    assert service.completed_ids("Ryan") == {"100", "200", "300"}


def test_collectible_profile_support_uses_profile_dimension() -> None:
    service_source = Path(profiled_collectible_service.__file__).read_text(encoding="utf-8")
    ui_source = Path(collectibles_profile_support.__file__).read_text(encoding="utf-8")

    assert "PRIMARY KEY (profile_name, collectible_id)" in service_source
    assert "Existing single-profile progress is migrated conservatively" in service_source
    assert "class ProfiledCollectibleService" in service_source
    assert 'context_field("PROFILE", self.profile_combo)' in ui_source
    assert "Save or discard pending collectible changes before switching profiles" in ui_source
    assert "set_owned_batch" in ui_source
