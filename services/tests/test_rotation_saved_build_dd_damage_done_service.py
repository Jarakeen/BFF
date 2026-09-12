from dataclasses import dataclass

from minmax.champion_point_static_repository import ChampionPointRecord
from models.build_model import ChampionPointEntry, PlayerBuild
from services.rotation_saved_build_dd_damage_done_service import (
    RotationSavedBuildDDDamageDoneService,
)


@dataclass
class _Repository:
    records: dict[str, ChampionPointRecord]

    def get(self, name: str):
        return self.records.get(name)


def _record(name: str, description: str) -> ChampionPointRecord:
    return ChampionPointRecord(
        name=name,
        skill_type=1,
        max_points=50,
        jump_points=(25, 50),
        description=description,
    )


def test_resolves_reviewed_unconditional_dd_damage_done_buckets() -> None:
    repository = _Repository(
        {
            "Master-at-Arms": _record(
                "Master-at-Arms",
                "Increases your damage done with direct damage attacks by 3% per stage.",
            ),
            "Biting Aura": _record(
                "Biting Aura",
                "Increases your damage done with area of effect attacks by 3% per stage.",
            ),
            "Thaumaturge": _record(
                "Thaumaturge",
                "Increases your damage done with damage over time effects by 3% per stage.",
            ),
        }
    )
    build = PlayerBuild(
        Name="Rylonia",
        Role="DD",
        ChampionPoints=[
            ChampionPointEntry(Name="Master-at-Arms", Points="50"),
            ChampionPointEntry(Name="Biting Aura", Points="50"),
            ChampionPointEntry(Name="Thaumaturge", Points="25"),
        ],
    )

    result = RotationSavedBuildDDDamageDoneService(
        champion_point_repository=repository,
    ).resolve(build)

    assert result.unresolved == ()
    assert result.modifiers.direct == 0.06
    assert result.modifiers.area == 0.06
    assert result.modifiers.dot == 0.03
    assert result.modifiers.generic == 0.0


def test_conditional_exploiter_is_not_promoted_to_static_damage_done() -> None:
    repository = _Repository({})
    build = PlayerBuild(
        Name="Rylonia",
        Role="DD",
        ChampionPoints=[ChampionPointEntry(Name="Exploiter", Points="50")],
    )

    result = RotationSavedBuildDDDamageDoneService(
        champion_point_repository=repository,
    ).resolve(build)

    assert result.unresolved == ()
    assert result.modifiers.generic == 0.0


def test_reviewed_tooltip_drift_fails_closed() -> None:
    repository = _Repository(
        {
            "Master-at-Arms": _record(
                "Master-at-Arms",
                "Changed tooltip semantics that no longer match the reviewed contract.",
            )
        }
    )
    build = PlayerBuild(
        Name="Rylonia",
        Role="DD",
        ChampionPoints=[ChampionPointEntry(Name="Master-at-Arms", Points="50")],
    )

    result = RotationSavedBuildDDDamageDoneService(
        champion_point_repository=repository,
    ).resolve(build)

    assert result.resolved is False
    assert "reviewed DD Damage Done semantics no longer match canonical tooltip" in result.unresolved[0]
