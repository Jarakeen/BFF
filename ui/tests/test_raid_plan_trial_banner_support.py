from ui.city_raid_plan_workspace_page import _trial_banner_filename


def test_raid_plan_trial_banner_resolution_accepts_trial_and_plan_labels() -> None:
    assert _trial_banner_filename("Cloudrest") == "cloudrest.webp"
    assert _trial_banner_filename("Sunspire", "Sunspire (Godslayer)") == "sunspire.webp"
    assert _trial_banner_filename("Dreadsail Reef", "DSR HM") == "dreadsail_reef.webp"


def test_raid_plan_trial_banner_resolution_is_case_insensitive() -> None:
    assert _trial_banner_filename("CLOUDREST") == "cloudrest.webp"
    assert _trial_banner_filename("sunSPIRE") == "sunspire.webp"
    assert _trial_banner_filename("DreadSail Reef") == "dreadsail_reef.webp"


def test_raid_plan_trial_banner_resolution_fails_closed_for_unmapped_trials() -> None:
    assert _trial_banner_filename("Rockgrove") is None
    assert _trial_banner_filename("") is None
    assert _trial_banner_filename(None) is None
