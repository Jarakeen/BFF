from types import SimpleNamespace

from minmax.skill_component_utility_effect import (
    SkillComponentUtilityEffect,
    SkillComponentUtilityEffectType,
)
from services.rotation_tank_taunt_duration_service import (
    RotationTankTauntDurationService,
)


class _CoefficientRepository:
    def resolve_name(self, name):
        return SimpleNamespace(
            rank=SimpleNamespace(
                name="Pierce Armor",
                skill_rank_id=42,
                ability_id=84,
                coefficients=(SimpleNamespace(coefficient_number=1),),
            ),
            unresolved=(),
        )


class _UtilityRepository:
    def __init__(self, component_text):
        self.component_text = component_text

    def resolve(self, skill_rank_id, coefficient_number):
        return (
            SkillComponentUtilityEffect(
                skill_rank_id=skill_rank_id,
                coefficient_number=coefficient_number,
                effect_type=SkillComponentUtilityEffectType.TAUNT,
                evidence="taunting",
            ),
        )

    def resolve_component_text(self, skill_rank_id, coefficient_number):
        return self.component_text


def test_owned_taunt_component_duration_resolves_without_generic_duration_evidence() -> None:
    service = RotationTankTauntDurationService(
        "unused.db",
        coefficient_repository=_CoefficientRepository(),
        utility_repository=_UtilityRepository(
            "Physical Damage and taunting them to attack you for 15 seconds."
        ),
        duration_resolver=lambda _name: SimpleNamespace(
            evidence=(),
            unresolved=("no positive canonical duration evidence found",),
        ),
    )

    result = service.resolve("Pierce Armor")

    assert result.resolved is True
    assert result.duration_seconds == 15.0
    assert result.unresolved == ()
    assert any("taunt duration 15s" in item for item in result.evidence)


def test_component_owned_taunt_duration_outranks_unrelated_generic_skill_durations() -> None:
    service = RotationTankTauntDurationService(
        "unused.db",
        coefficient_repository=_CoefficientRepository(),
        utility_repository=_UtilityRepository(
            "Physical Damage and taunting them to attack you for 15 seconds."
        ),
        duration_resolver=lambda _name: SimpleNamespace(
            evidence=(
                SimpleNamespace(duration_seconds=8.0, effect_name="other", source="test"),
                SimpleNamespace(duration_seconds=12.0, effect_name="other2", source="test"),
            ),
            unresolved=(),
        ),
    )

    result = service.resolve("Pierce Armor")

    assert result.resolved is True
    assert result.duration_seconds == 15.0
