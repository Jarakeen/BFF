from __future__ import annotations

from pathlib import Path
import shutil

from services.antiquity_service import AntiquityService


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DATA = REPO_ROOT / "data"


def _copy_catalog(tmp_path: Path) -> Path:
    for source in sorted(SOURCE_DATA.glob("antiquities_[0-9][0-9].csv")):
        shutil.copy2(source, tmp_path / source.name)
    return tmp_path


def test_antiquity_catalog_contains_all_uesp_rows(tmp_path):
    service = AntiquityService(_copy_catalog(tmp_path))

    assert service.available is True
    assert service.progress_summary() == (0, 773)
    assert len(service.items()) == 773
    assert service.item(548)["name"] == "Admiral's Carved Trestle Base"
    assert service.item(789)["name"] == "Zenithar Devotional Stele"


def test_antiquity_progress_is_profile_aware_and_persistent(tmp_path):
    data_dir = _copy_catalog(tmp_path)
    service = AntiquityService(data_dir)
    service.set_active_profile("Jarakeen")
    service.set_progress(548, recovered=True, recovered_on="2026-09-03", notes="Recovered.")

    assert service.progress_summary() == (1, 773)
    assert service.item(548)["owned"] is True

    reloaded = AntiquityService(data_dir)
    reloaded.set_active_profile("Jarakeen")
    assert reloaded.progress_summary() == (1, 773)
    assert reloaded.item(548)["notes"] == "Recovered."

    reloaded.set_active_profile("Rylo")
    assert reloaded.progress_summary() == (0, 773)


def test_antiquity_search_matches_zone_and_reward_set(tmp_path):
    service = AntiquityService(_copy_catalog(tmp_path))

    assert any(row["name"] == "Aetherquartz Prayer Beads" for row in service.items("Pearls of Ehlnofey"))
    assert any(row["name"] == "Zenithar Devotional Stele" for row in service.items("Glenumbra"))
