import pytest

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.character_build.gear_piece import ArmorPiece, GearPieceCategory, GearSlot
from minmax.healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    HealerHeavyAttackBuildIncentive,
)
from minmax.heavy_attack_restoration import HeavyAttackWeaponType
from minmax.heavy_attack_runtime_state import (
    HeavyAttackEffectRuntimeState,
    evaluate_required_heavy_attack_due_state,
)
from minmax.role import Role
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType
from services.rotation_build_effect_duration_service import RotationBuildEffectDurationService
from services.rotation_heavy_attack_effect_duration_service import (
    RotationHeavyAttackEffectDurationService,
)


class _NoGearSetResolver:
    def resolve(self, set_id: int, piece_count: int):
        return ()


def _jorvulds_modifier() -> EffectVariant:
    return EffectVariant(
        name="major_minor_buff_duration_increase",
        layer=EffectLayer.PASSIVE,
        source="Jorvuld's Guidance (5)",
        magnitude=0.40,
        scaling="increases duration of Major and Minor buffs applied by 40%",
        target_type=SupportTargetType.SELF,
        category=SupportEffectCategory.OTHER,
        stacking=StackingBehavior.UNIQUE,
        exclusivity_group="jorvulds_guidance_buff_duration",
    )


def _build() -> CharacterBuild:
    return CharacterBuild(
        name="RoJo healer",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        armor=(
            ArmorPiece(
                slot=GearSlot.CHEST,
                category=GearPieceCategory.SET_PIECE,
                set_id="jorvulds-guidance-fixture",
                effects=(_jorvulds_modifier(),),
            ),
        ),
    )


def _ro() -> HealerHeavyAttackBuildIncentive:
    return HealerHeavyAttackBuildIncentive(
        bar="front",
        weapon=HeavyAttackWeaponType.RESTORATION_STAFF,
        kind=HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT,
        name="Roaring Opportunist",
        source="verified RO base fixture",
        recurrence_seconds=22.0,
        maximum_effect_duration_seconds=12.0,
        required_effect_name="major_slayer",
        required_effect_category=SupportEffectCategory.BUFF,
    )


def test_rojo_keeps_base_duration_but_runtime_uses_build_effective_major_slayer_window() -> None:
    shared_duration = RotationBuildEffectDurationService(
        gear_set_effect_resolver=_NoGearSetResolver(),
    )
    evidence = RotationHeavyAttackEffectDurationService(shared_duration).enrich(
        build=_build(),
        incentives=(_ro(),),
    )

    assert evidence.unresolved == ()
    assert len(evidence.incentives) == 1
    incentive = evidence.incentives[0]

    # Preserve each mechanic separately. RO owns the 12s source cap and 22s
    # re-eligibility rule; Jorvuld's changes only the build-effective buff window.
    assert incentive.maximum_effect_duration_seconds == pytest.approx(12.0)
    assert incentive.effective_effect_duration_seconds == pytest.approx(16.8)
    assert incentive.recurrence_seconds == pytest.approx(22.0)

    runtime = HeavyAttackEffectRuntimeState(
        incentive_name="Roaring Opportunist",
        bar="front",
        last_trigger_seconds=3.8,
    )
    due = evaluate_required_heavy_attack_due_state(
        incentive=incentive,
        current_time_seconds=10.0,
        runtime=runtime,
    )

    assert due.due is False
    assert due.effect_expires_seconds == pytest.approx(20.6)
    assert due.next_eligible_seconds == pytest.approx(25.8)
    assert due.seconds_until_due == pytest.approx(15.8)
