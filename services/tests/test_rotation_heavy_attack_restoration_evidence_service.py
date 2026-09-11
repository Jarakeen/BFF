from __future__ import annotations

import pytest

from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_layer import BarId
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.heavy_attack_restoration import HeavyAttackRestorationModifiers
from minmax.resource_costs import ResourceType
from minmax.role import Role
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_heavy_attack_restoration_evidence_service import (
    RotationHeavyAttackCompletionEvidence,
    RotationHeavyAttackRestorationEvidenceService,
)


def _slots() -> tuple[SlottedSkill, ...]:
    return tuple(
        SlottedSkill(
            skill_id=f"dummy_{index}",
            skill_line_id="fighters_guild",
            is_ultimate=index == 5,
        )
        for index in range(6)
    )


def _bar(bar_id: BarId, weapon: WeaponType) -> Bar:
    return Bar(
        bar_id=bar_id,
        main_hand=Weapon(weapon),
        off_hand=None,
        slots=_slots(),
    )


def _build(
    *,
    front_weapon: WeaponType = WeaponType.FROST_STAFF,
    back_weapon: WeaponType = WeaponType.RESTORATION_STAFF,
) -> CharacterBuild:
    return CharacterBuild(
        name="Heavy Evidence Build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=_bar(BarId.FRONT, front_weapon),
        back_bar=_bar(BarId.BACK, back_weapon),
    )


def _heavy(time: float, sequence: int = 0) -> RotationAction:
    return RotationAction(time, sequence, RotationActionKind.HEAVY_ATTACK)


def _plan(*actions: RotationAction, duration: float = 30.0) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="Heavy Evidence Build",
        duration_seconds=duration,
        actions=tuple(actions),
    )


def _evidence(
    *,
    start: float,
    sequence: int = 0,
    completion: float,
    fully_charged: bool = True,
    base_restore: float | None = None,
    modifiers: HeavyAttackRestorationModifiers = HeavyAttackRestorationModifiers(),
) -> RotationHeavyAttackCompletionEvidence:
    return RotationHeavyAttackCompletionEvidence(
        action_time_seconds=start,
        action_sequence=sequence,
        completion_time_seconds=completion,
        fully_charged=fully_charged,
        verified_base_restore=base_restore,
        modifiers=modifiers,
        source="verified test heavy",
    )


def test_fully_charged_resto_heavy_uses_canonical_base_at_completion() -> None:
    plan = _plan(
        RotationAction(5.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        _heavy(6.0, 0),
    )
    projection = RotationHeavyAttackRestorationEvidenceService().project(
        build=_build(),
        plan=plan,
        initial_bar="front",
        completion_evidence=(_evidence(start=6.0, completion=8.5),),
    )

    assert projection.is_resolved is True
    assert projection.unresolved == ()
    assert len(projection.restoration_events) == 1
    event = projection.restoration_events[0]
    assert event.time_seconds == 8.5
    assert event.resource is ResourceType.MAGICKA
    assert event.amount == 3267.0
    assert event.source == "verified test heavy"


def test_explicit_reviewed_base_override_still_wins_before_modifiers() -> None:
    plan = _plan(
        RotationAction(5.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        _heavy(6.0, 0),
    )
    modifiers = HeavyAttackRestorationModifiers(
        restoration_staff_cycle_of_life_percent=0.3,
    )
    projection = RotationHeavyAttackRestorationEvidenceService().project(
        build=_build(),
        plan=plan,
        initial_bar="front",
        completion_evidence=(
            _evidence(
                start=6.0,
                completion=8.0,
                base_restore=3000.0,
                modifiers=modifiers,
            ),
        ),
    )

    assert projection.restoration_events[0].amount == pytest.approx(3900.0)


def test_canonical_resto_base_then_cycle_of_life_matches_reviewed_log_return() -> None:
    plan = _plan(
        RotationAction(5.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        _heavy(6.0, 0),
    )
    projection = RotationHeavyAttackRestorationEvidenceService().project(
        build=_build(),
        plan=plan,
        initial_bar="front",
        completion_evidence=(
            _evidence(
                start=6.0,
                completion=8.0,
                modifiers=HeavyAttackRestorationModifiers(
                    restoration_staff_cycle_of_life_percent=0.30,
                ),
            ),
        ),
    )

    assert projection.restoration_events[0].amount == pytest.approx(4247.1)


def test_explicit_not_fully_charged_is_known_zero_restore() -> None:
    plan = _plan(_heavy(2.0))
    projection = RotationHeavyAttackRestorationEvidenceService().project(
        build=_build(),
        plan=plan,
        initial_bar="front",
        completion_evidence=(
            _evidence(
                start=2.0,
                completion=2.7,
                fully_charged=False,
            ),
        ),
    )

    assert projection.is_resolved is True
    assert projection.unresolved == ()
    assert len(projection.resolutions) == 1
    assert projection.resolutions[0].restoration_event is None
    assert projection.restoration_events == ()


def test_missing_completion_evidence_is_unresolved_not_zero_restore() -> None:
    projection = RotationHeavyAttackRestorationEvidenceService().project(
        build=_build(),
        plan=_plan(_heavy(2.0)),
        initial_bar="front",
        completion_evidence=(),
    )

    assert projection.is_resolved is False
    assert projection.restoration_events == ()
    assert "lacks completion/full-charge evidence" in projection.unresolved[0]


def test_fully_charged_heavy_without_any_verified_base_restore_is_unresolved() -> None:
    projection = RotationHeavyAttackRestorationEvidenceService().project(
        build=_build(front_weapon=WeaponType.FLAME_STAFF),
        plan=_plan(_heavy(2.0)),
        initial_bar="front",
        completion_evidence=(
            _evidence(start=2.0, completion=4.0),
        ),
    )

    assert projection.is_resolved is False
    assert projection.restoration_events == ()
    assert "lacks verified base restore evidence" in projection.unresolved[0]


def test_completion_after_plan_horizon_is_unresolved() -> None:
    projection = RotationHeavyAttackRestorationEvidenceService().project(
        build=_build(),
        plan=_plan(_heavy(9.0), duration=10.0),
        initial_bar="front",
        completion_evidence=(
            _evidence(start=9.0, completion=10.5),
        ),
    )

    assert projection.is_resolved is False
    assert "after the rotation plan horizon" in projection.unresolved[0]


def test_evidence_without_matching_scheduled_heavy_fails_closed() -> None:
    with pytest.raises(ValueError, match="has no scheduled heavy"):
        RotationHeavyAttackRestorationEvidenceService().project(
            build=_build(),
            plan=_plan(),
            initial_bar="front",
            completion_evidence=(
                _evidence(start=3.0, completion=5.0),
            ),
        )


def test_duplicate_completion_evidence_fails_closed() -> None:
    item = _evidence(start=2.0, completion=4.0)
    with pytest.raises(ValueError, match="duplicate heavy-attack completion evidence"):
        RotationHeavyAttackRestorationEvidenceService().project(
            build=_build(),
            plan=_plan(_heavy(2.0)),
            initial_bar="front",
            completion_evidence=(item, item),
        )


def test_replay_resolver_returns_event_for_exact_scheduled_heavy_only() -> None:
    plan = _plan(_heavy(2.0), _heavy(8.0, 1))
    projection = RotationHeavyAttackRestorationEvidenceService().project(
        build=_build(),
        plan=plan,
        initial_bar="front",
        completion_evidence=(
            _evidence(start=2.0, completion=4.0),
            _evidence(
                start=8.0,
                sequence=1,
                completion=9.0,
                fully_charged=False,
            ),
        ),
    )
    resolver = RotationHeavyAttackRestorationEvidenceService.resolver(projection)

    assert resolver(plan.actions[0]) == projection.restoration_events[0]
    assert resolver(plan.actions[1]) is None
