from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.potion_use_event import PotionBuffGrant, PotionTraitUse, PotionUseEvent
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_plan_potion_combat_state_service import (
    RotationPlanPotionCombatStateService,
)


class _Resolver:
    def resolve(self, selected_label: str) -> PotionUseEvent:
        assert selected_label == "Alliance Battle Draught"
        return PotionUseEvent(
            selected_label=selected_label,
            traits=(
                PotionTraitUse(
                    trait="Increase Weapon Power",
                    kind="timed_trait",
                    magnitude=None,
                    duration=36.6,
                    triple_duration=None,
                    tier_name="Alliance Battle Draught",
                    solvent="Lorkhan's Tears",
                    level=50,
                ),
                PotionTraitUse(
                    trait="Weapon Critical",
                    kind="timed_trait",
                    magnitude=None,
                    duration=36.6,
                    triple_duration=None,
                    tier_name="Alliance Battle Draught",
                    solvent="Lorkhan's Tears",
                    level=50,
                ),
            ),
            buff_grants=(
                PotionBuffGrant(
                    source_trait="Increase Weapon Power",
                    buff_name="Major Brutality",
                    duration=36.6,
                    triple_duration=None,
                    tier_name="Alliance Battle Draught",
                ),
                PotionBuffGrant(
                    source_trait="Weapon Critical",
                    buff_name="Major Savagery",
                    duration=36.6,
                    triple_duration=None,
                    tier_name="Alliance Battle Draught",
                ),
            ),
        )


def _build() -> PlayerBuild:
    return PlayerBuild(
        Name="Rylonia",
        BuildName="Corpsebuster DD",
        Role="DD",
        Potion="Alliance Battle Draught",
    )


def _progression(rank: int | None = 3) -> CharacterProgression:
    return CharacterProgression(
        passive_ranks=None if rank is None else {"Medicinal Use": rank},
        passive_cp_points={},
    )


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=90.0,
        actions=(
            RotationAction(5.0, 0, RotationActionKind.POTION, name="Alliance Battle Draught"),
            RotationAction(50.0, 0, RotationActionKind.POTION, name="Alliance Battle Draught"),
        ),
    )


def _service() -> RotationPlanPotionCombatStateService:
    return RotationPlanPotionCombatStateService(event_resolver=_Resolver())


def test_selected_potion_does_not_create_standing_buff_before_explicit_use() -> None:
    result = _service().resolve(
        _build(),
        progression=_progression(),
        plan=_plan(),
        time_seconds=4.0,
        base_combat_state=CombatState(active_buffs=("Minor Berserk",)),
    )

    assert result.resolved is True
    assert result.latest_potion_action is None
    assert result.combat_state.active_buffs == ("Minor Berserk",)


def test_explicit_potion_action_projects_named_buffs_with_medicinal_use_duration() -> None:
    result = _service().resolve(
        _build(),
        progression=_progression(3),
        plan=_plan(),
        time_seconds=40.0,
        base_combat_state=CombatState(active_buffs=("Minor Berserk",)),
    )

    # 36.6s x 1.30 Medicinal Use = 47.58s, so the 5s use is still active at 40s.
    assert result.resolved is True
    assert result.latest_potion_action.time_seconds == 5.0
    assert result.combat_state.active_buffs == (
        "Minor Berserk",
        "Major Brutality",
        "Major Savagery",
    )


def test_latest_explicit_potion_action_refreshes_the_runtime_window() -> None:
    result = _service().resolve(
        _build(),
        progression=_progression(3),
        plan=_plan(),
        time_seconds=80.0,
    )

    assert result.resolved is True
    assert result.latest_potion_action.time_seconds == 50.0
    assert result.combat_state.has_buff("Major Brutality") is True


def test_ordered_sequence_does_not_activate_later_same_timestamp_potion() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=10.0,
        actions=(
            RotationAction(5.0, 3, RotationActionKind.POTION, name="Alliance Battle Draught"),
        ),
    )

    before = _service().resolve(
        _build(), progression=_progression(), plan=plan, time_seconds=5.0, sequence=2
    )
    after = _service().resolve(
        _build(), progression=_progression(), plan=plan, time_seconds=5.0, sequence=3
    )

    assert before.latest_potion_action is None
    assert before.combat_state.active_buffs == ()
    assert after.latest_potion_action is not None
    assert after.combat_state.has_buff("Major Brutality") is True


def test_potion_identity_drift_fails_closed() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=10.0,
        actions=(RotationAction(1.0, 0, RotationActionKind.POTION, name="Different Potion"),),
    )

    result = _service().resolve(
        _build(), progression=_progression(), plan=plan, time_seconds=2.0
    )

    assert result.resolved is False
    assert result.combat_state is None
    assert "does not match saved potion" in result.unresolved[0]


def test_scheduled_potion_requires_recorded_medicinal_use_rank() -> None:
    result = _service().resolve(
        _build(), progression=_progression(None), plan=_plan(), time_seconds=6.0
    )

    assert result.resolved is False
    assert result.combat_state is None
    assert result.unresolved == (
        "Medicinal Use rank is unresolved for scheduled potion runtime",
    )
