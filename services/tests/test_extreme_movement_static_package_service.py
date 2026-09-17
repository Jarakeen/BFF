from __future__ import annotations

import pytest

from minmax.champion_point_static_repository import ChampionPointRecord
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.stat_ids import StatId
from services.extreme_movement_static_package_service import (
    ExtremeMovementStaticPackageService,
)


class _Mundus:
    def effects_for_name(self, name: str):
        assert name == "The Steed"
        return (
            (
                Effect(
                    stat=StatId.MOVEMENT_SPEED,
                    operation=EffectOperation.ADD_PERCENT,
                    value=10.0,
                    unit=EffectUnit.PERCENT,
                    source="Mundus: The Steed",
                ),
            ),
            (),
        )


class _ChampionPoints:
    RECORDS = {
        "Celerity": ChampionPointRecord(
            name="Celerity",
            skill_type=1,
            max_points=50,
            jump_points=(10, 20, 30, 40, 50),
            description="Increases your Movement Speed by 2% per stage.",
        ),
        "Wind Chaser": ChampionPointRecord(
            name="Wind Chaser",
            skill_type=1,
            max_points=16,
            jump_points=(8, 16),
            description="Increases your Movement Speed when Sprinting by 2% per stage.",
        ),
    }

    def get(self, name: str):
        return self.RECORDS.get(name)

    @staticmethod
    def _stages(record: ChampionPointRecord, points: int) -> int:
        allocated = max(0, min(int(points), record.max_points or int(points)))
        return sum(1 for value in record.jump_points if allocated >= value)


def _service() -> ExtremeMovementStaticPackageService:
    return ExtremeMovementStaticPackageService(
        "unused.db",
        mundus=_Mundus(),
        jewelry=JewelryTraitRepository("unused.db"),
        champion_points=_ChampionPoints(),
    )


def test_static_movement_package_reuses_steed_three_swift_and_celerity() -> None:
    result = _service().evaluate("movement_speed")

    assert result.result.raw_multiplier == pytest.approx(1.41)
    assert result.result.effective_multiplier == pytest.approx(1.41)
    assert "Major/Minor Expedition provider search not yet included" in result.unresolved
    assert any("Necklace: Legendary Swift" == row for row in result.evidence)
    assert any("Champion Point: Celerity max rank" == row for row in result.evidence)


def test_static_sprint_package_reuses_same_sources_plus_wind_chaser() -> None:
    result = _service().evaluate("sprint_speed")

    # Inner sprint bucket: 1 + 0.40 + 0.21 Swift + 0.10 Steed + 0.04 Wind Chaser.
    # Celerity is the canonical multiplicative CP.MovementSpeed bucket.
    assert result.result.raw_multiplier == pytest.approx(1.75 * 1.10)
    assert result.result.effective_multiplier == pytest.approx(1.75 * 1.10)
    assert any("Champion Point: Wind Chaser max rank" == row for row in result.evidence)


def test_static_stealth_package_preserves_unresolved_stealth_provider_search() -> None:
    result = _service().evaluate("stealthed_movement_speed")

    # Base sneak penalty remains until a reviewed penalty-removal source is searched.
    assert result.result.raw_multiplier == pytest.approx((1.0 - 0.40 + 0.21 + 0.10) * 1.10)
    assert "stealth penalty-removal and sneak-speed provider search not yet included" in result.unresolved
    assert result.mechanic_complete is False
