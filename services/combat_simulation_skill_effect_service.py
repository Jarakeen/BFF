from __future__ import annotations

"""Project reviewed skill support effects into deterministic simulation windows."""

from dataclasses import dataclass
from pathlib import Path

from engine.config import DEFAULT_DATABASE
from minmax.character_build.effect_instance import EffectVariant
from minmax.runtime_effect_stacking import apply_runtime_effect_window_stacking
from minmax.runtime_effect_window import RuntimeEffectActiveWindow
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.skill_effect_repository import SkillEffectRepository
from models.build_model import PlayerBuild
from models.combat_simulation import CombatSimulationEvent, SimulationEventPriority


@dataclass(frozen=True)
class CombatSimulationEffectProjection:
    events: tuple[CombatSimulationEvent, ...]
    windows: tuple[RuntimeEffectActiveWindow, ...]
    unresolved: tuple[str, ...] = ()


class CombatSimulationSkillEffectService:
    """Project cast-time reviewed skill effects without inventing target recipients."""

    def __init__(
        self,
        database_path: str | Path = DEFAULT_DATABASE,
        *,
        repository: SkillEffectRepository | object | None = None,
    ) -> None:
        self.repository = repository or SkillEffectRepository(database_path)

    def project(
        self,
        *,
        build: PlayerBuild,
        plan: RotationPlan,
    ) -> CombatSimulationEffectProjection:
        available = {
            str(name or "").strip().casefold(): int(ability_id)
            for ability_id, name in self.repository.available_skills(build.EsoClass)
        }
        windows_by_effect: dict[str, tuple[RuntimeEffectActiveWindow, ...]] = {}
        effect_by_name: dict[str, EffectVariant] = {}
        unresolved: list[str] = []

        for action in plan.actions:
            if action.kind not in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}:
                continue
            name = str(action.name or "").strip()
            if not name:
                continue
            ability_id = available.get(name.casefold())
            if ability_id is None:
                unresolved.append(
                    f"{name} at {action.time_seconds:g}s: canonical skill-effect identity unavailable"
                )
                continue

            for effect in self.repository.resolve(ability_id):
                if effect.layer.value != "cast":
                    continue
                if not effect.eligible:
                    unresolved.append(
                        f"{name} {effect.name} at {action.time_seconds:g}s: effect is not eligible"
                    )
                    continue
                if effect.trigger is not None:
                    # Triggered effects are owned by the Phase 7 runtime path and
                    # must not be treated as unconditional cast consequences here.
                    continue
                if effect.condition is not None:
                    unresolved.append(
                        f"{name} {effect.name} at {action.time_seconds:g}s: "
                        f"condition context required: {effect.condition}"
                    )
                    continue
                if effect.duration is None:
                    unresolved.append(
                        f"{name} {effect.name} at {action.time_seconds:g}s: "
                        "bounded duration is unavailable"
                    )
                    continue
                duration = float(effect.duration)
                if duration <= 0:
                    continue
                if effect.target_type is None:
                    unresolved.append(
                        f"{name} {effect.name} at {action.time_seconds:g}s: "
                        "target scope is unresolved"
                    )
                    continue

                window = RuntimeEffectActiveWindow(
                    effect_name=effect.name,
                    source=effect.source,
                    start_time_seconds=float(action.time_seconds),
                    end_time_seconds=float(action.time_seconds) + duration,
                    target=effect.target_type.value,
                    sequence=int(action.sequence),
                    magnitude=effect.magnitude,
                )
                prior = windows_by_effect.get(effect.name, ())
                stacked = apply_runtime_effect_window_stacking(
                    prior,
                    window,
                    behavior=effect.stacking,
                )
                unresolved.extend(
                    f"{name} {effect.name} at {action.time_seconds:g}s: {message}"
                    for message in stacked.unresolved
                )
                if stacked.resolved:
                    windows_by_effect[effect.name] = stacked.retained
                    effect_by_name[effect.name] = effect

        windows = tuple(
            sorted(
                (
                    window
                    for values in windows_by_effect.values()
                    for window in values
                ),
                key=lambda item: (
                    item.start_time_seconds,
                    item.sequence,
                    item.effect_name,
                    item.target or "",
                ),
            )
        )

        events: list[CombatSimulationEvent] = []
        for window in windows:
            effect = effect_by_name[window.effect_name]
            payload = (
                ("effect_name", window.effect_name),
                ("target_scope", window.target or ""),
                ("magnitude", window.magnitude),
                ("duration_seconds", window.duration_seconds),
                ("category", effect.category.value if effect.category is not None else ""),
                ("stacking", effect.stacking.value if effect.stacking is not None else ""),
            )
            events.append(
                CombatSimulationEvent(
                    time_seconds=window.start_time_seconds,
                    priority=int(SimulationEventPriority.EFFECT_APPLY),
                    sequence=window.sequence,
                    event_type="effect_apply",
                    source=window.source,
                    payload=payload,
                )
            )
            if window.end_time_seconds <= plan.duration_seconds:
                events.append(
                    CombatSimulationEvent(
                        time_seconds=window.end_time_seconds,
                        priority=int(SimulationEventPriority.EXPIRATION),
                        sequence=window.sequence,
                        event_type="effect_expire",
                        source=window.source,
                        payload=payload,
                    )
                )

        return CombatSimulationEffectProjection(
            events=tuple(
                sorted(
                    events,
                    key=lambda event: (
                        event.time_seconds,
                        event.priority,
                        event.sequence,
                        event.event_type,
                        event.source.casefold(),
                    ),
                )
            ),
            windows=windows,
            unresolved=tuple(
                dict.fromkeys(
                    str(message).strip()
                    for message in unresolved
                    if str(message).strip()
                )
            ),
        )


__all__ = [
    "CombatSimulationEffectProjection",
    "CombatSimulationSkillEffectService",
]
