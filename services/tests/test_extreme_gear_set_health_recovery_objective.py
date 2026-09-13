from minmax.stat_ids import StatId
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


def test_health_recovery_is_a_reviewed_named_gear_objective():
    assert "health_recovery" in ExtremeGearSetObjectiveService.REVIEWED_OBJECTIVES
    assert ExtremeGearSetObjectiveService._target_stats("health_recovery") == {
        StatId.HEALTH_RECOVERY
    }
