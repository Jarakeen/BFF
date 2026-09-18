from pathlib import Path


def test_raid_plan_and_live_raid_share_trial_banner_support() -> None:
    plan = Path("ui/city_raid_plan_workspace_page.py").read_text(encoding="utf-8")
    live = Path("ui/city_live_raid_page.py").read_text(encoding="utf-8")
    support = Path("ui/raid_trial_banner_support.py").read_text(encoding="utf-8")
    manifest = Path("packaging/release_manifest.py").read_text(encoding="utf-8")

    assert "TrialBannerLabel" in plan
    assert "trial_banner_path(selected_trial)" in plan
    assert "TrialBannerLabel" in live
    assert "trial_banner_path(plan.trial_id, plan.name)" in live
    assert '"rockgrove": "rockgrove.webp"' in support
    assert '"dsr": "dreadsail_reef.webp"' in support
    assert '("assets/raid_plans/trial_banners", "assets/raid_plans/trial_banners")' in manifest
