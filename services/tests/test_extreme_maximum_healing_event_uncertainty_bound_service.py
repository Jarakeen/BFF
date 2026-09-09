from types import SimpleNamespace

import pytest

from services.extreme_dragon_blood_skill_component_repository import (
    ExtremeDragonBloodSkillComponentRepository,
)
from services.extreme_maximum_healing_event_uncertainty_bound_service import (
    ExtremeMaximumHealingEventUncertaintyBoundService,
)


def _entry(*, value, rank_id=None):
    candidate = None if rank_id is None else SimpleNamespace(skill_rank_id=rank_id)
    return SimpleNamespace(
        event_value=value,
        route_entry=SimpleNamespace(candidate=candidate),
    )


def test_elder_dragon_blood_exposes_source_supported_fifty_percent_ceiling():
    result = ExtremeMaximumHealingEventUncertaintyBoundService().bound(
        _entry(
            value=14877.979,
            rank_id=ExtremeDragonBloodSkillComponentRepository.ELDER_DRAGON_BLOOD_RANK_ID,
        )
    )

    assert result.lower_bound == pytest.approx(14877.979)
    assert result.upper_bound == pytest.approx(22316.9685)
    assert "up to 50% additional healing" in result.reason


def test_non_dragon_blood_entry_has_exact_numeric_bound():
    result = ExtremeMaximumHealingEventUncertaintyBoundService().bound(
        _entry(value=17859.313, rank_id=4847)
    )

    assert result.lower_bound == pytest.approx(17859.313)
    assert result.upper_bound == pytest.approx(17859.313)
    assert result.reason == ""


def test_unscored_entry_has_no_numeric_interval():
    result = ExtremeMaximumHealingEventUncertaintyBoundService().bound(
        _entry(value=None)
    )

    assert result.lower_bound is None
    assert result.upper_bound is None
    assert result.bounded is False
