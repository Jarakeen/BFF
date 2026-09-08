from models.performance_model import AbilityUptime, PerformanceSnapshot
from ui.performance_dashboard_polish_support import _tracked_results


def test_tracked_results_prefers_higher_uptime_for_same_effect():
    snapshot = PerformanceSnapshot(
        BuffUptimes=[AbilityUptime(Name="Major Courage", UptimePercent=72.0)],
        RaidDebuffUptimes=[AbilityUptime(Name="Major Courage", UptimePercent=91.0)],
    )

    result = _tracked_results(snapshot, ["Major Courage"])[0]

    assert result.name == "Major Courage"
    assert result.source == "Raid-Wide"
    assert result.uptime_percent == 91.0


def test_tracked_results_keeps_requested_missing_effect_visible():
    snapshot = PerformanceSnapshot(
        RaidDebuffUptimes=[AbilityUptime(Name="Major Brittle", UptimePercent=84.5)]
    )

    results = _tracked_results(snapshot, ["Major Brittle", "Major Slayer"])

    assert results[0].uptime_percent == 84.5
    assert results[1].name == "Major Slayer"
    assert results[1].source == "Not found"
    assert results[1].uptime_percent is None
