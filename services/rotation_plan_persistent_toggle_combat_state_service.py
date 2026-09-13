from __future__ import annotations

from dataclasses import dataclass
import math

from minmax.combat_state import CombatState
from minmax.rotation_plan import RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_scribed_skill_damage_semantics_service import (
    RotationScribedSkillDamageSemanticsService,
)


@dataclass(frozen=True)
class RotationPlanPersistentToggleCombatStateResult:
    """Plan-derived attacker combat state for reviewed persistent toggles."""

    combat_state: CombatState | None
    active_toggle_names: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.combat_state is not None and not self.unresolved


class RotationPlanPersistentToggleCombatStateService:
    """Layer reviewed persistent-toggle state onto one explicit CombatState.

    This service derives only activation lifetime that is proven by the final
    rotation plan plus the saved bar layout. It does not infer resource sustain,
    automatic reactivation, or single-bar swap behavior. A reviewed persistent
    toggle must be present on both bars and have exactly one final-plan activation
    before it can be treated as continuously active after that ordered action.
    """

    def __init__(
        self,
        *,
        semantics: RotationScribedSkillDamageSemanticsService | None = None,
    ) -> None:
        self.semantics = semantics or RotationScribedSkillDamageSemanticsService()

    def resolve(
        self,
        build: PlayerBuild,
        *,
        plan: RotationPlan,
        time_seconds: float,
        sequence: int | None = None,
        base_combat_state: CombatState = CombatState(),
    ) -> RotationPlanPersistentToggleCombatStateResult:
        instant = float(time_seconds)
        if not math.isfinite(instant) or instant < 0.0:
            raise ValueError("persistent-toggle runtime time must be finite and non-negative")
        if instant > float(plan.duration_seconds) + 1e-12:
            raise ValueError("persistent-toggle runtime time cannot exceed plan duration")
        boundary_sequence = None if sequence is None else int(sequence)
        if boundary_sequence is not None and boundary_sequence < 0:
            raise ValueError("persistent-toggle runtime sequence cannot be negative")

        persistent_names: dict[str, str] = {}
        slotted_bars: dict[str, set[str]] = {}
        for bar, values in (
            ("front", tuple(getattr(build, "FrontBarSkills", ()) or ())[:5]),
            ("back", tuple(getattr(build, "BackBarSkills", ()) or ())[:5]),
        ):
            for raw in values:
                name = str(raw or "").strip()
                if not name:
                    continue
                semantic = self.semantics.resolve(name)
                if semantic is None or not semantic.persistent_toggle:
                    continue
                key = semantic.result_name.casefold()
                persistent_names.setdefault(key, semantic.result_name)
                slotted_bars.setdefault(key, set()).add(bar)

        if not persistent_names:
            return RotationPlanPersistentToggleCombatStateResult(
                combat_state=base_combat_state,
            )

        unresolved: list[str] = []
        active_names: list[str] = []
        for key, result_name in persistent_names.items():
            bars = slotted_bars.get(key, set())
            if bars != {"front", "back"}:
                unresolved.append(
                    f"persistent toggle '{result_name}' is not represented on both bars; "
                    "runtime lifetime across bar swaps is unresolved"
                )
                continue

            activations = tuple(
                action
                for action in plan.actions
                if action.kind is RotationActionKind.SKILL
                and action.name
                and action.name.casefold() == key
            )
            if len(activations) > 1:
                unresolved.append(
                    f"persistent toggle '{result_name}' has {len(activations)} final-plan activations; "
                    "toggle on/off state is unresolved"
                )
                continue
            if not activations:
                continue

            activation = activations[0]
            if self._is_active_after(
                activation_time=float(activation.time_seconds),
                activation_sequence=int(activation.sequence),
                query_time=instant,
                query_sequence=boundary_sequence,
            ):
                active_names.append(result_name)

        if unresolved:
            return RotationPlanPersistentToggleCombatStateResult(
                combat_state=None,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        if not active_names:
            return RotationPlanPersistentToggleCombatStateResult(
                combat_state=base_combat_state,
            )

        merged = CombatState(
            in_combat=base_combat_state.in_combat,
            active_buffs=tuple(base_combat_state.active_buffs) + tuple(active_names),
            game_update=base_combat_state.game_update,
            is_emperor=base_combat_state.is_emperor,
            in_home_campaign=base_combat_state.in_home_campaign,
            emperor_home_keeps=base_combat_state.emperor_home_keeps,
        )
        return RotationPlanPersistentToggleCombatStateResult(
            combat_state=merged,
            active_toggle_names=tuple(active_names),
        )

    @staticmethod
    def _is_active_after(
        *,
        activation_time: float,
        activation_sequence: int,
        query_time: float,
        query_sequence: int | None,
    ) -> bool:
        if query_time > activation_time:
            return True
        if query_time < activation_time:
            return False
        if query_sequence is None:
            # Sequence-less exact-time runtime events are interpreted after all
            # scheduled actions at that timestamp.
            return True
        return int(query_sequence) >= activation_sequence


__all__ = [
    "RotationPlanPersistentToggleCombatStateResult",
    "RotationPlanPersistentToggleCombatStateService",
]
