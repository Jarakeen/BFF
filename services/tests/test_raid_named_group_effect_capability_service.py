from types import SimpleNamespace

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.support_target_type import SupportTargetType
from models.build_model import PlayerBuild
from services.raid_named_group_effect_capability_service import (
    RaidNamedGroupEffectCapabilityService,
)
from services.saved_build_capability_service import RaidCoverageSnapshot


class _CapabilityService:
    def __init__(self, effects):
        self.effects = tuple(effects)

    def audit_build(self, _build):
        return SimpleNamespace(resolved_effects=self.effects)


def _empty_snapshot(*names: str) -> RaidCoverageSnapshot:
    return RaidCoverageSnapshot(
        status={name: "unverified" for name in names},
        providers={name: [] for name in names},
        conditional_providers={name: [] for name in names},
    )


def test_exact_group_effect_identity_is_promoted_to_available() -> None:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    effect = EffectVariant(
        name="minor_sorcery",
        layer=EffectLayer.PASSIVE,
        source="Illuminate",
        target_type=SupportTargetType.GROUP,
    )

    result = RaidNamedGroupEffectCapabilityService().overlay(
        _empty_snapshot("Minor Sorcery"),
        (build,),
        capability_service=_CapabilityService((effect,)),
    )

    assert result.status["Minor Sorcery"] == "available"
    assert result.providers["Minor Sorcery"] == ["Magrat"]


def test_triggered_group_effect_is_promoted_as_conditional() -> None:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    effect = EffectVariant(
        name="major_force",
        layer=EffectLayer.ULTIMATE,
        source="Aggressive Horn",
        trigger="ultimate_cast",
        target_type=SupportTargetType.GROUP,
    )

    result = RaidNamedGroupEffectCapabilityService().overlay(
        _empty_snapshot("Major Force"),
        (build,),
        capability_service=_CapabilityService((effect,)),
    )

    assert result.status["Major Force"] == "conditional"
    assert result.conditional_providers["Major Force"] == ["Magrat"]


def test_self_only_named_buff_is_not_misreported_as_raid_coverage() -> None:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    effect = EffectVariant(
        name="major_sorcery",
        layer=EffectLayer.CONSUMABLE,
        source="Spell Power Potion",
        target_type=SupportTargetType.SELF,
    )

    result = RaidNamedGroupEffectCapabilityService().overlay(
        _empty_snapshot("Major Sorcery"),
        (build,),
        capability_service=_CapabilityService((effect,)),
    )

    assert result.status["Major Sorcery"] == "unverified"
    assert result.providers["Major Sorcery"] == []
    assert result.conditional_providers["Major Sorcery"] == []


def test_unclassified_target_fails_closed_instead_of_guessing_group_coverage() -> None:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    effect = EffectVariant(
        name="major_breach",
        layer=EffectLayer.CAST,
        source="Unknown Source",
        target_type=None,
    )

    result = RaidNamedGroupEffectCapabilityService().overlay(
        _empty_snapshot("Major Breach"),
        (build,),
        capability_service=_CapabilityService((effect,)),
    )

    assert result.status["Major Breach"] == "unverified"
