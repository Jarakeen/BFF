from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from minmax.character_progression import CharacterProgression
from minmax.combat_state import CombatState
from minmax.potion_cadence import PotionCadence
from minmax.potion_use_event import PotionUseEventResolver
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class RotationPlanPotionCombatStateResult:
    """Exact potion-derived attacker state for one ordered point in a final plan."""

    combat_state: CombatState | None
    latest_potion_action: RotationAction | None = None
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.combat_state is not None and not self.unresolved


class RotationPlanPotionCombatStateService:
    """Project only explicitly scheduled potion activations into CombatState.

    A saved potion selection proves availability, not uptime. This service therefore
    activates no potion effect until a POTION action exists at or before the queried
    ordered point. Source-backed potion traits/durations remain owned by
    ``PotionUseEventResolver`` and Medicinal Use duration scaling remains owned by
    ``PotionCadence``. Cooldown legality and potion scheduling remain separate
    rotation responsibilities.
    """

    _EPSILON = 1e-12

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        event_resolver: PotionUseEventResolver | None = None,
    ) -> None:
        database = Path(database_path) if database_path is not None else get_data_dir() / "eso.db"
        self.event_resolver = event_resolver or PotionUseEventResolver(database_path=database)

    @staticmethod
    def _ordered_before_or_at(
        action: RotationAction,
        *,
        time_seconds: float,
        sequence: int | None,
    ) -> bool:
        action_time = float(action.time_seconds)
        if action_time < float(time_seconds) - RotationPlanPotionCombatStateService._EPSILON:
            return True
        if abs(action_time - float(time_seconds)) > RotationPlanPotionCombatStateService._EPSILON:
            return False
        return sequence is None or int(action.sequence) <= int(sequence)

    @staticmethod
    def _merge(base: CombatState, names: tuple[str, ...]) -> CombatState:
        return CombatState(
            in_combat=base.in_combat,
            active_buffs=tuple(dict.fromkeys((*base.active_buffs, *names))),
            game_update=base.game_update,
            is_emperor=base.is_emperor,
            in_home_campaign=base.in_home_campaign,
            emperor_home_keeps=base.emperor_home_keeps,
        )

    def resolve(
        self,
        build: PlayerBuild,
        *,
        progression: CharacterProgression,
        plan: RotationPlan,
        time_seconds: float,
        sequence: int | None = None,
        base_combat_state: CombatState = CombatState(),
    ) -> RotationPlanPotionCombatStateResult:
        instant = float(time_seconds)
        if instant < 0.0:
            raise ValueError("rotation potion combat-state time cannot be negative")
        if instant > float(plan.duration_seconds) + self._EPSILON:
            raise ValueError("rotation potion combat-state time cannot exceed plan duration")
        if sequence is not None and int(sequence) < 0:
            raise ValueError("rotation potion combat-state sequence cannot be negative")

        potion_name = " ".join(str(getattr(build, "Potion", "") or "").strip().split())
        if not potion_name:
            return RotationPlanPotionCombatStateResult(combat_state=base_combat_state)

        actions = tuple(
            action
            for action in plan.actions
            if action.kind is RotationActionKind.POTION
            and self._ordered_before_or_at(
                action,
                time_seconds=instant,
                sequence=sequence,
            )
        )
        if not actions:
            return RotationPlanPotionCombatStateResult(combat_state=base_combat_state)

        latest = max(actions, key=lambda action: (float(action.time_seconds), int(action.sequence)))
        action_name = " ".join(str(latest.name or "").strip().split())
        if action_name and action_name.casefold() != potion_name.casefold():
            return RotationPlanPotionCombatStateResult(
                combat_state=None,
                latest_potion_action=latest,
                unresolved=(
                    f"scheduled potion identity {action_name!r} does not match saved potion {potion_name!r}",
                ),
            )

        rank = progression.passive_rank("Medicinal Use")
        if rank is None:
            return RotationPlanPotionCombatStateResult(
                combat_state=None,
                latest_potion_action=latest,
                unresolved=("Medicinal Use rank is unresolved for scheduled potion runtime",),
            )

        event = self.event_resolver.resolve(potion_name)
        if not event.resolved:
            return RotationPlanPotionCombatStateResult(
                combat_state=None,
                latest_potion_action=latest,
                unresolved=tuple(event.unresolved) or (
                    f"scheduled potion runtime could not resolve potion evidence: {potion_name}",
                ),
            )

        try:
            cadence = PotionCadence(event, medicinal_use_rank=rank)
        except ValueError as exc:
            return RotationPlanPotionCombatStateResult(
                combat_state=None,
                latest_potion_action=latest,
                unresolved=(str(exc),),
            )

        elapsed = max(0.0, instant - float(latest.time_seconds))
        active_names = cadence.window(elapsed).active_buff_names
        return RotationPlanPotionCombatStateResult(
            combat_state=self._merge(base_combat_state, active_names),
            latest_potion_action=latest,
        )


__all__ = [
    "RotationPlanPotionCombatStateResult",
    "RotationPlanPotionCombatStateService",
]
