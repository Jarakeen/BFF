from types import SimpleNamespace

import pytest

from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_layer import BarId
from minmax.character_build.saved_build_adapter import SavedBuildAdaptation
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.role import Role
from minmax.stat_ids import StatId
from models.build_model import ChampionPointEntry, PlayerBuild
from services.rotation_saved_build_weapon_attack_evaluation_service import (
    RotationSavedBuildWeaponAttackContributionService,
    RotationSavedBuildWeaponAttackEvaluationService,
)


def _slots():
    return tuple(
        SlottedSkill(
            skill_id=f"skill_{index}",
            skill_line_id="destruction_staff",
            is_ultimate=index == 5,
        )
        for index in range(6)
    )


def _canonical_build() -> CharacterBuild:
    return CharacterBuild(
        name="DD",
        character_class=CharacterClass.WARDEN,
        role=Role.DD,
        front_bar=Bar(
            bar_id=BarId.FRONT,
            main_hand=Weapon(WeaponType.FLAME_STAFF),
            off_hand=None,
            slots=_slots(),
        ),
        back_bar=Bar(
            bar_id=BarId.BACK,
            main_hand=Weapon(WeaponType.FROST_STAFF),
            off_hand=None,
            slots=_slots(),
        ),
    )


class _Adapter:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def adapt(self, build, *, character_id=None):
        self.calls.append((build, character_id))
        return self.result


def _trace(value):
    return SimpleNamespace(final_value=value)


def _context(bar: str, *, dd_exploiter_bonus=0.0):
    derived = {
        StatId.MAX_MAGICKA: _trace(30000.0 if bar == "front" else 31000.0),
        StatId.MAX_STAMINA: _trace(18000.0 if bar == "front" else 19000.0),
        StatId.WEAPON_DAMAGE: _trace(4000.0 if bar == "front" else 4500.0),
        StatId.SPELL_DAMAGE: _trace(5000.0 if bar == "front" else 5500.0),
        StatId.PHYSICAL_PENETRATION: _trace(6000.0),
        StatId.SPELL_PENETRATION: _trace(7000.0),
        StatId.CRITICAL_DAMAGE: _trace(0.5),
        StatId.CRITICAL_CHANCE: _trace(0.4),
    }
    return SimpleNamespace(
        active_bar=bar,
        core_state=SimpleNamespace(derived=derived),
        dd_exploiter_bonus=float(dd_exploiter_bonus),
    )


class _StaticContext:
    resolved = True
    unresolved = ()
    progression = SimpleNamespace(character_id="char-1")
    contexts = (_context("front"), _context("back"))


class _StaticContextWithExploiter:
    resolved = True
    unresolved = ()
    progression = SimpleNamespace(character_id="char-1")
    contexts = (
        _context("front", dd_exploiter_bonus=0.04),
        _context("back", dd_exploiter_bonus=0.04),
    )


def test_contribution_service_maps_reviewed_cp_weapon_attack_buckets() -> None:
    build = PlayerBuild(
        ChampionPoints=[
            ChampionPointEntry(Name="Weapons Expert", Points="50"),
            ChampionPointEntry(Name="Master-at-Arms", Points="50"),
            ChampionPointEntry(Name="Deadly Aim", Points="25"),
        ]
    )

    contributions, unresolved = RotationSavedBuildWeaponAttackContributionService().resolve(build)

    assert unresolved == ()
    values = {item.effect_type: item.effective_value for item in contributions}
    assert values == {
        "cp_la_damage": pytest.approx(0.20),
        "cp_ha_damage": pytest.approx(0.20),
        "direct_damage_done": pytest.approx(0.06),
        "single_target_damage_done": pytest.approx(0.03),
    }
    assert all(item.uptime == 1.0 for item in contributions)


def test_contribution_service_uses_jump_points_not_linear_point_fraction() -> None:
    build = PlayerBuild(
        ChampionPoints=[
            ChampionPointEntry(Name="Weapons Expert", Points="29"),
            ChampionPointEntry(Name="Master-at-Arms", Points="49"),
            ChampionPointEntry(Name="Deadly Aim", Points="24"),
        ]
    )

    contributions, unresolved = RotationSavedBuildWeaponAttackContributionService().resolve(build)

    assert unresolved == ()
    values = {item.effect_type: item.effective_value for item in contributions}
    assert values["cp_la_damage"] == pytest.approx(0.08)
    assert values["cp_ha_damage"] == pytest.approx(0.08)
    assert values["direct_damage_done"] == pytest.approx(0.03)
    assert "single_target_damage_done" not in values


def test_contribution_service_invalid_reviewed_cp_allocation_fails_closed() -> None:
    build = PlayerBuild(
        ChampionPoints=[ChampionPointEntry(Name="Weapons Expert", Points="banana")]
    )

    contributions, unresolved = RotationSavedBuildWeaponAttackContributionService().resolve(build)

    assert contributions == ()
    assert unresolved == (
        "Champion Point Weapons Expert: allocation is not a non-negative integer",
    )


def test_evaluation_bridge_projects_bar_specific_stats_and_contributions() -> None:
    build = PlayerBuild(
        Name="Parse Cat",
        BuildName="DD",
        Role="DD",
        ChampionPoints=[ChampionPointEntry(Name="Weapons Expert", Points="50")],
    )
    adapter = _Adapter(SavedBuildAdaptation(_canonical_build(), ()))
    service = RotationSavedBuildWeaponAttackEvaluationService(
        database_path="unused.db",
        build_adapter=adapter,  # type: ignore[arg-type]
    )

    result = service.resolve(player_build=build, static_context=_StaticContext())

    assert result.resolved is True
    assert result.build is not None
    assert adapter.calls == [(build, "char-1")]
    front = result.evaluation_for("front")
    back = result.evaluation_for("back")
    assert front is not None and back is not None
    assert front.stats.value(StatId.MAX_MAGICKA) == pytest.approx(30000.0)
    assert back.stats.value(StatId.MAX_MAGICKA) == pytest.approx(31000.0)
    assert front.stats.value(StatId.MAX_STAMINA) == pytest.approx(18000.0)
    assert back.stats.value(StatId.MAX_STAMINA) == pytest.approx(19000.0)
    assert front.stats.value(StatId.SPELL_DAMAGE) == pytest.approx(5000.0)
    assert back.stats.value(StatId.SPELL_DAMAGE) == pytest.approx(5500.0)
    assert front.stats.value(StatId.CRITICAL_DAMAGE) == pytest.approx(50.0)
    assert {item.effect_type: item.effective_value for item in front.combat_contributions}[
        "cp_la_damage"
    ] == pytest.approx(0.20)


def test_evaluation_bridge_carries_exploiter_magnitude_without_claiming_uptime() -> None:
    build = PlayerBuild(Name="Parse Cat", BuildName="DD", Role="DD")
    adapter = _Adapter(SavedBuildAdaptation(_canonical_build(), ()))
    service = RotationSavedBuildWeaponAttackEvaluationService(
        database_path="unused.db",
        build_adapter=adapter,  # type: ignore[arg-type]
    )

    result = service.resolve(
        player_build=build,
        static_context=_StaticContextWithExploiter(),
    )

    assert result.resolved is True
    front = result.evaluation_for("front")
    back = result.evaluation_for("back")
    assert front is not None and back is not None
    for evaluation in (front, back):
        values = {
            item.effect_type: item.effective_value
            for item in evaluation.combat_contributions
        }
        assert values["conditional_exploiter_damage_done"] == pytest.approx(0.04)


def test_evaluation_bridge_preserves_adapter_unresolved() -> None:
    build = PlayerBuild(Name="Parse Cat", BuildName="DD", Role="DD")
    adapter = _Adapter(SavedBuildAdaptation(None, ("canonical weapon unresolved",)))
    service = RotationSavedBuildWeaponAttackEvaluationService(
        database_path="unused.db",
        build_adapter=adapter,  # type: ignore[arg-type]
    )

    result = service.resolve(player_build=build, static_context=_StaticContext())

    assert result.resolved is False
    assert result.unresolved == ("canonical weapon unresolved",)