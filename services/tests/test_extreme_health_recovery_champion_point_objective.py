from __future__ import annotations

import pytest

from minmax.champion_point_static_repository import (
    CHAMPION_SKILL_TYPE_NORMAL,
    ChampionPointRecord,
)
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.stat_ids import StatId
from services.extreme_champion_point_objective_service import (
    ExtremeChampionPointObjectiveService,
)


class _Repository:
    def resolve(self, name, points):
        return (
            [
                Effect(
                    source=f"Champion Point: {name}",
                    stat=StatId.HEALTH_RECOVERY,
                    operation=EffectOperation.ADD,
                    value=90.0,
                    unit=EffectUnit.FLAT,
                ),
                Effect(
                    source=f"Champion Point: {name}",
                    stat=StatId.MAGICKA_RECOVERY,
                    operation=EffectOperation.ADD,
                    value=90.0,
                    unit=EffectUnit.FLAT,
                ),
                Effect(
                    source=f"Champion Point: {name}",
                    stat=StatId.STAMINA_RECOVERY,
                    operation=EffectOperation.ADD,
                    value=90.0,
                    unit=EffectUnit.FLAT,
                ),
            ],
            [],
        )


def test_projects_health_recovery_from_reviewed_shared_recovery_star():
    record = ChampionPointRecord(
        name="Rejuvenation",
        skill_type=CHAMPION_SKILL_TYPE_NORMAL,
        max_points=50,
        jump_points=(),
        description="Grants Health, Magicka, and Stamina Recovery.",
    )

    row = ExtremeChampionPointObjectiveService.candidate_for_record(
        _Repository(),
        record,
        "health_recovery",
    )

    assert row.reviewed_delta == pytest.approx(90.0)
    assert row.unresolved == ()
