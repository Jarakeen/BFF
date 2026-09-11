from minmax.rotation_active_bar_legality import RotationActiveBarAssessor
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from models.build_model import GearSlot, PlayerBuild
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.rotation_runtime_bar_provenance_service import RotationRuntimeBarProvenanceService
from services.rotation_saved_build_bar_access_service import (
    RotationSavedBuildBarAccessService,
)


def _oakensoul_build() -> PlayerBuild:
    return PlayerBuild(Ring1=GearSlot(Set="Oakensoul Ring"))


def _swap_plan() -> RotationPlan:
    return RotationPlan(
        character_name="Oak",
        build_name="One Bar",
        duration_seconds=5.0,
        actions=(
            RotationAction(1.0, 0, RotationActionKind.SKILL, "Front Skill", "front"),
            RotationAction(2.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(2.0, 1, RotationActionKind.SKILL, "Back Skill", "back"),
        ),
    )


def _front_only_plan() -> RotationPlan:
    return RotationPlan(
        character_name="Oak",
        build_name="One Bar",
        duration_seconds=5.0,
        actions=(
            RotationAction(1.0, 0, RotationActionKind.SKILL, "Front Skill", "front"),
            RotationAction(2.0, 0, RotationActionKind.LIGHT_ATTACK, "Light Attack", "front"),
        ),
    )


def _snapshot() -> ExtremeRuntimeSnapshot:
    attempt = RuntimeEffectEventAttempt(
        RuntimeEvent(
            time_seconds=1.0,
            sequence=0,
            trigger="skill_cast",
            source="oakensoul rotation test",
        )
    )
    return ExtremeRuntimeSnapshot(
        runtime_history=(attempt,),
        snapshot_time_seconds=4.0,
    )


def test_saved_build_oakensoul_rejects_bar_swap_but_preserves_backup_equipment_shape():
    build = _oakensoul_build()
    build.BackBarWeapon = GearSlot(Set="Back Bar Set", WeaponType="Ice Staff")
    plan = _swap_plan()
    base = RotationActiveBarAssessor().assess(plan)

    restricted = RotationSavedBuildBarAccessService.restrict(build, plan, base)

    assert restricted.legal is False
    assert any("Oakensoul Ring prevents swapping" in row.reason for row in restricted.violations)
    assert build.BackBarWeapon.Set == "Back Bar Set"


def test_saved_build_oakensoul_allows_front_only_plan():
    build = _oakensoul_build()
    plan = _front_only_plan()
    base = RotationActiveBarAssessor().assess(plan)

    restricted = RotationSavedBuildBarAccessService.restrict(build, plan, base)

    assert restricted.legal is True
    assert restricted.final_bar == "front"


def test_ordinary_saved_build_keeps_normal_two_bar_legality():
    build = PlayerBuild()
    plan = _swap_plan()
    base = RotationActiveBarAssessor().assess(plan)

    restricted = RotationSavedBuildBarAccessService.restrict(build, plan, base)

    assert restricted == base
    assert restricted.legal is True
    assert restricted.final_bar == "back"


def test_runtime_provenance_fails_closed_on_oakensoul_swap():
    result = RotationRuntimeBarProvenanceService().bind(
        _swap_plan(),
        _snapshot(),
        player_build=_oakensoul_build(),
    )

    assert result.resolved is False
    assert result.snapshot is None
    assert any("Oakensoul Ring prevents swapping" in row for row in result.unresolved)


def test_runtime_provenance_accepts_oakensoul_front_only_plan():
    result = RotationRuntimeBarProvenanceService().bind(
        _front_only_plan(),
        _snapshot(),
        player_build=_oakensoul_build(),
    )

    assert result.resolved is True
    assert result.snapshot is not None
    assert result.snapshot.bar_transitions == ()
    assert result.snapshot.bar_transition_history_complete is True
