from pathlib import Path

from ui.raid_trial_banner_support import trial_banner_filename, trial_banner_path


def test_raid_plan_trial_banner_resolution_accepts_trial_and_plan_labels() -> None:
    assert trial_banner_filename("Cloudrest") == "cloudrest.webp"
    assert trial_banner_filename("Rockgrove") == "rockgrove.webp"
    assert trial_banner_filename("Sunspire", "Sunspire (Godslayer)") == "sunspire.webp"
    assert trial_banner_filename("Dreadsail Reef", "DSR HM") == "dreadsail_reef.webp"


def test_raid_plan_trial_banner_resolution_is_case_insensitive() -> None:
    assert trial_banner_filename("CLOUDREST") == "cloudrest.webp"
    assert trial_banner_filename("ROCKGROVE") == "rockgrove.webp"
    assert trial_banner_filename("sunSPIRE") == "sunspire.webp"
    assert trial_banner_filename("DreadSail Reef") == "dreadsail_reef.webp"


def test_raid_plan_trial_banner_resolution_handles_ossein_spellings() -> None:
    assert trial_banner_filename("Ossein Cage") == "ossein_cage.webp"
    assert trial_banner_filename("Ossein's Cage") == "ossein_cage.webp"
    assert trial_banner_filename("Osseins Cage") == "ossein_cage.webp"
    assert trial_banner_filename("OC") == "ossein_cage.webp"


def test_committed_rockgrove_and_cloudrest_banner_files_resolve() -> None:
    rockgrove = trial_banner_path("Rockgrove")
    cloudrest = trial_banner_path("Cloudrest")

    assert rockgrove is not None and rockgrove.name == "rockgrove.webp"
    assert cloudrest is not None and cloudrest.name == "cloudrest.webp"


def test_raid_plan_trial_selector_directly_refreshes_banner() -> None:
    source = Path("ui/city_raid_plan_workspace_page.py").read_text(encoding="utf-8")

    assert "self.trial_combo.currentTextChanged.connect(self._trial_selection_changed)" in source
    assert "def _refresh_trial_banner(self) -> None:" in source
    assert "self.overview_art.set_source(trial_banner_path(self.trial_combo.currentText()))" in source
