from pathlib import Path
from types import SimpleNamespace

import pytest

from minmax.effects import EffectUnit
from models.build_model import GearSlot, PlayerBuild
from services.rotation_saved_build_charged_status_chance_service import (
    RotationSavedBuildChargedStatusChanceService,
)


class _Rules:
    def __init__(self, rules=None):
        self.rules = tuple(
            rules
            or (
                SimpleNamespace(
                    rule_type="status_effect_chance",
                    value=182.5,
                    unit=EffectUnit.PERCENT,
                    source="Charged",
                ),
            )
        )

    def get_weapon_trait_rules(self, trait_name):
        assert trait_name == "Charged"
        return list(self.rules)


class _UnexpectedRules:
    def get_weapon_trait_rules(self, _trait_name):
        raise AssertionError("Charged rule lookup should not occur when the build has no Charged weapon")


def _weapon(*, trait="", weapon_type="Dagger") -> GearSlot:
    return GearSlot(
        Set="Test Set",
        Trait=trait,
        Quality="Gold",
        Level="CP160",
        WeaponType=weapon_type,
    )


def test_front_offhand_charged_resolves_exact_saved_slot() -> None:
    build = PlayerBuild(
        FrontBarWeapon=_weapon(trait="Precise", weapon_type="Dagger"),
        FrontBarOffHand=_weapon(trait="Charged", weapon_type="Dagger"),
    )
    service = RotationSavedBuildChargedStatusChanceService(
        rule_repository=_Rules(),  # type: ignore[arg-type]
    )

    result = service.resolve(build)

    assert result.resolved is True
    assert result.unresolved == ()
    assert len(result.sources) == 1
    source = result.sources[0]
    assert source.bar == "front"
    assert source.slot_name == "Front Bar Off Hand"
    assert source.weapon_type == "Dagger"
    assert source.bonus_percent == pytest.approx(182.5)
    assert result.bonus_percent_for("front") == pytest.approx(182.5)
    assert result.bonus_percent_for("back") == 0.0


def test_two_slot_weapon_uses_existing_double_trait_scaling() -> None:
    build = PlayerBuild(
        BackBarWeapon=_weapon(trait="Charged", weapon_type="Inferno Staff"),
    )
    service = RotationSavedBuildChargedStatusChanceService(
        rule_repository=_Rules(),  # type: ignore[arg-type]
    )

    result = service.resolve(build)

    assert result.resolved is True
    assert result.bonus_percent_for("back") == pytest.approx(365.0)


def test_multiple_charged_weapons_fail_closed_until_stacking_is_reviewed() -> None:
    build = PlayerBuild(
        FrontBarWeapon=_weapon(trait="Charged", weapon_type="Dagger"),
        FrontBarOffHand=_weapon(trait="Charged", weapon_type="Dagger"),
    )
    service = RotationSavedBuildChargedStatusChanceService(
        rule_repository=_Rules(),  # type: ignore[arg-type]
    )

    result = service.resolve(build)

    assert result.resolved is False
    assert result.sources == ()
    assert result.unresolved == (
        "front bar has multiple Charged weapons; stacking semantics are not yet reviewed",
    )


def test_non_percent_charged_rule_fails_closed() -> None:
    service = RotationSavedBuildChargedStatusChanceService(
        rule_repository=_Rules(
            (
                SimpleNamespace(
                    rule_type="status_effect_chance",
                    value=182.5,
                    unit=EffectUnit.FLAT,
                    source="Charged",
                ),
            )
        ),  # type: ignore[arg-type]
    )
    build = PlayerBuild(FrontBarWeapon=_weapon(trait="Charged"))

    result = service.resolve(build)

    assert result.resolved is False
    assert "unsupported unit" in result.unresolved[0]


def test_build_without_charged_skips_rule_repository_lookup() -> None:
    service = RotationSavedBuildChargedStatusChanceService(
        rule_repository=_UnexpectedRules(),  # type: ignore[arg-type]
    )

    result = service.resolve(PlayerBuild())

    assert result.resolved is True
    assert result.sources == ()


def test_real_database_exposes_one_positive_percent_charged_rule() -> None:
    build = PlayerBuild(
        FrontBarWeapon=_weapon(trait="Precise", weapon_type="Dagger"),
        FrontBarOffHand=_weapon(trait="Charged", weapon_type="Dagger"),
    )
    service = RotationSavedBuildChargedStatusChanceService(Path("data/eso.db"))

    result = service.resolve(build)

    assert result.resolved is True
    assert result.bonus_percent_for("front") > 0.0
