import pytest

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_duration_resolver import EffectDurationResolution
from minmax.character_build.saved_build_adapter import SavedBuildAdaptation
from minmax.healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    HealerHeavyAttackBuildIncentive,
)
from minmax.heavy_attack_restoration import HeavyAttackWeaponType
from minmax.role import Role
from minmax.support_effect_category import SupportEffectCategory
from models.build_model import PlayerBuild
from services.rotation_heavy_attack_effect_duration_service import (
    RotationHeavyAttackEffectDurationService,
)


class _DurationService:
    def __init__(self, effective: float | None = 16.8, unresolved=()):
        self.effective = effective
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, *, build, active_bar, effect, passives=()):
        self.calls.append((build, active_bar, effect, tuple(passives)))
        return EffectDurationResolution(
            effect_name=effect.name,
            base_duration_seconds=effect.duration,
            effective_duration_seconds=self.effective,
            unresolved=self.unresolved,
        )


class _BuildAdapter:
    def __init__(self, adaptation: SavedBuildAdaptation):
        self.adaptation = adaptation
        self.calls = []

    def adapt(self, saved, *, character_id=None):
        self.calls.append((saved, character_id))
        return self.adaptation


def _build() -> CharacterBuild:
    return CharacterBuild(
        name="RoJo",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
    )


def _ro() -> HealerHeavyAttackBuildIncentive:
    return HealerHeavyAttackBuildIncentive(
        bar="front",
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
        kind=HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT,
        name="Roaring Opportunist",
        source="verified RO fixture",
        recurrence_seconds=22.0,
        maximum_effect_duration_seconds=12.0,
        required_effect_name="major_slayer",
        required_effect_category=SupportEffectCategory.BUFF,
    )


def test_required_heavy_effect_receives_build_effective_duration_without_overwriting_base() -> None:
    duration = _DurationService(effective=16.8)

    result = RotationHeavyAttackEffectDurationService(duration).enrich(
        build=_build(),
        incentives=(_ro(),),
    )

    assert result.unresolved == ()
    assert len(result.incentives) == 1
    incentive = result.incentives[0]
    assert incentive.maximum_effect_duration_seconds == pytest.approx(12.0)
    assert incentive.effective_effect_duration_seconds == pytest.approx(16.8)
    assert duration.calls[0][2].name == "major_slayer"
    assert duration.calls[0][2].duration == pytest.approx(12.0)
    assert duration.calls[0][2].category is SupportEffectCategory.BUFF


def test_saved_build_enrichment_adapts_once_then_uses_shared_duration_service() -> None:
    canonical = _build()
    saved = PlayerBuild(Name="Magrat", BuildName="RoJo Healer", Role="Healer")
    adapter = _BuildAdapter(SavedBuildAdaptation(canonical, ()))
    duration = _DurationService(effective=16.8)
    service = RotationHeavyAttackEffectDurationService(
        duration,
        build_adapter=adapter,
    )

    result = service.enrich_saved_build(
        build=saved,
        incentives=(_ro(),),
        character_id="magrat",
    )

    assert adapter.calls == [(saved, "magrat")]
    assert result.canonical_build is canonical
    assert result.unresolved == ()
    assert result.incentives[0].effective_effect_duration_seconds == pytest.approx(16.8)
    assert duration.calls[0][0] is canonical


def test_failed_saved_build_adaptation_preserves_incentive_and_fails_closed() -> None:
    saved = PlayerBuild(Name="Magrat", BuildName="RoJo Healer", Role="Healer")
    adapter = _BuildAdapter(
        SavedBuildAdaptation(
            None,
            ("front main hand: gear set not found in GearSetRepository: Jorvuld's Guidance",),
        )
    )
    service = RotationHeavyAttackEffectDurationService(
        _DurationService(),
        build_adapter=adapter,
    )

    result = service.enrich_saved_build(
        build=saved,
        incentives=(_ro(),),
    )

    assert result.canonical_build is None
    assert result.incentives == (_ro(),)
    assert result.incentives[0].effective_effect_duration_seconds is None
    assert result.unresolved == (
        "front main hand: gear set not found in GearSetRepository: Jorvuld's Guidance",
    )


def test_non_required_heavy_incentive_is_not_sent_through_effect_duration_resolution() -> None:
    duration = _DurationService()
    recovery = HealerHeavyAttackBuildIncentive(
        bar="front",
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
        kind=HeavyAttackBuildIncentiveKind.RECOVERY_VALUE,
        name="Recovery",
        source="fixture",
    )

    result = RotationHeavyAttackEffectDurationService(duration).enrich(
        build=_build(),
        incentives=(recovery,),
    )

    assert result.incentives == (recovery,)
    assert result.unresolved == ()
    assert duration.calls == []


def test_missing_required_effect_semantics_remain_explicit() -> None:
    incomplete = HealerHeavyAttackBuildIncentive(
        bar="front",
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
        kind=HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT,
        name="Future HA Set",
        source="fixture",
        recurrence_seconds=10.0,
        maximum_effect_duration_seconds=8.0,
    )

    result = RotationHeavyAttackEffectDurationService(_DurationService()).enrich(
        build=_build(),
        incentives=(incomplete,),
    )

    assert result.incentives[0].effective_effect_duration_seconds is None
    assert result.unresolved == (
        "Future HA Set: required heavy effect identity/category unresolved",
    )


def test_unresolved_shared_duration_does_not_invent_effective_duration() -> None:
    result = RotationHeavyAttackEffectDurationService(
        _DurationService(
            effective=None,
            unresolved=("major_slayer: duration modifier evidence unresolved",),
        )
    ).enrich(
        build=_build(),
        incentives=(_ro(),),
    )

    assert result.incentives[0].maximum_effect_duration_seconds == pytest.approx(12.0)
    assert result.incentives[0].effective_effect_duration_seconds is None
    assert result.unresolved == (
        "major_slayer: duration modifier evidence unresolved",
    )
