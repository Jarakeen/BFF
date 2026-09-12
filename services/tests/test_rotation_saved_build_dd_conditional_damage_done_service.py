from dataclasses import dataclass

from minmax.champion_point_static_repository import ChampionPointRecord
from models.build_model import ChampionPointEntry, PlayerBuild
from services.rotation_saved_build_dd_conditional_damage_done_service import (
    RotationSavedBuildDDConditionalDamageDoneService,
)


@dataclass
class _Repository:
    record: ChampionPointRecord | None

    def get(self, name: str):
        assert name == "Exploiter"
        return self.record


def _record(description: str) -> ChampionPointRecord:
    return ChampionPointRecord(
        name="Exploiter",
        skill_type=1,
        max_points=50,
        jump_points=(25, 50),
        description=description,
    )


def test_resolves_exploiter_bonus_without_assuming_off_balance_is_active() -> None:
    build = PlayerBuild(
        Name="Rylonia",
        Role="DD",
        ChampionPoints=[ChampionPointEntry(Name="Exploiter", Points="50")],
    )
    result = RotationSavedBuildDDConditionalDamageDoneService(
        champion_point_repository=_Repository(
            _record("Increases your damage done against Off Balance enemies by 2% per stage.")
        )
    ).resolve(build)

    assert result.resolved is True
    assert result.exploiter_bonus == 0.04
    assert result.unresolved == ()


def test_absent_exploiter_resolves_to_zero_without_inventing_target_state() -> None:
    result = RotationSavedBuildDDConditionalDamageDoneService(
        champion_point_repository=_Repository(None)
    ).resolve(PlayerBuild(Name="Rylonia", Role="DD", ChampionPoints=[]))

    assert result.resolved is True
    assert result.exploiter_bonus == 0.0


def test_exploiter_tooltip_drift_fails_closed() -> None:
    build = PlayerBuild(
        Name="Rylonia",
        Role="DD",
        ChampionPoints=[ChampionPointEntry(Name="Exploiter", Points="50")],
    )
    result = RotationSavedBuildDDConditionalDamageDoneService(
        champion_point_repository=_Repository(_record("Different semantics."))
    ).resolve(build)

    assert result.resolved is False
    assert "no longer match canonical tooltip" in result.unresolved[0]
