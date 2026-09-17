from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from models.build_model import PlayerBuild
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.extreme_damage_shield_event_service import ExtremeDamageShieldEventService
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter


@dataclass(frozen=True)
class ExtremeDamageShieldSavedBuildRecordResult:
    skill_name: str | None
    entity_id: str | None
    value: float | None
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def mechanic_complete(self) -> bool:
        return self.value is not None and not self.unresolved


class ExtremeDamageShieldSavedBuildRecordService:
    """Evaluate the strongest reviewed shield already slotted on one saved bar.

    This is deliberately a saved-build lower bound, not the global shield-skill
    denominator. Skill coefficient math and SHIELD component identity remain owned
    by ``ExtremeDamageShieldEventService``. The service only discovers canonical
    entity ids for the selected saved bar, builds one canonical character context,
    and ranks successfully evaluated single-shield applications.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        optimizer: ExtremeCompleteOptimizationService | None = None,
        event_service: ExtremeDamageShieldEventService | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.optimizer = optimizer or ExtremeCompleteOptimizationService(
            database_path=self.database_path
        )
        self.progression = MinmaxCharacterProgressionAdapter(
            self.optimizer.build_service.canonical.catalog_service
        )
        self.events = event_service or ExtremeDamageShieldEventService(self.database_path)

    def evaluate(
        self,
        build: PlayerBuild,
        *,
        active_bar: str = "front",
    ) -> ExtremeDamageShieldSavedBuildRecordResult:
        bar = str(active_bar or "front").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError(f"Unsupported active bar: {active_bar!r}")

        progression_resolution = self.progression.resolve(build)
        if not progression_resolution.resolved:
            raise ValueError("; ".join(progression_resolution.unresolved))

        build_id = (
            str(getattr(build, "BuildId", "") or "").strip()
            or str(build.BuildName or "").strip()
            or "saved-build"
        )
        context = self.optimizer.context_factory.build(
            character_id=progression_resolution.character_id,
            build_id=f"{build_id}:extreme-damage-shield",
            build=build,
            progression=progression_resolution.progression,
            active_bar=bar,
        )

        values = build.FrontBarSkills if bar == "front" else build.BackBarSkills
        skill_names = tuple(
            str(value or "").strip()
            for value in list(values)[:6]
            if str(value or "").strip()
        )

        best_name: str | None = None
        best_entity: str | None = None
        best_value: float | None = None
        evidence: list[str] = []
        unresolved: list[str] = [
            f"Build context: {problem}" for problem in context.unresolved_gear_effects
        ]

        for skill_name in skill_names:
            resolution = self.events.tooltip_service.coefficients.resolve_name(skill_name)
            rank = resolution.rank
            if rank is None:
                unresolved.extend(
                    tuple(resolution.unresolved)
                    or (f"{skill_name}: canonical skill entity unresolved",)
                )
                continue

            result = self.events.evaluate(
                build=build,
                context=context,
                entity_id=rank.entity_id,
            )
            if result.modified_shield is None:
                # A non-shield skill is expected on ordinary bars and does not make
                # the whole saved-build record unresolved. Preserve only ambiguity
                # from a skill that actually exposed SHIELD classification evidence.
                if result.coefficient_number is not None:
                    unresolved.extend(result.unresolved)
                continue

            value = float(result.modified_shield)
            evidence.append(
                f"{skill_name}: {value:.0f} reviewed single shield from coefficient {result.coefficient_number}"
            )
            unresolved.extend(result.unresolved)
            if best_value is None or value > best_value:
                best_name = skill_name
                best_entity = rank.entity_id
                best_value = value

        if best_value is None:
            unresolved.append(f"No single SHIELD-classified skill was resolved on the saved {bar} bar")

        unresolved.extend(
            (
                "Global shield-skill candidate search is not yet included",
                "Damage-shield CP/buff/set/skill modifier source search is not yet composed into the saved-build record",
            )
        )
        return ExtremeDamageShieldSavedBuildRecordResult(
            skill_name=best_name,
            entity_id=best_entity,
            value=best_value,
            evidence=tuple(dict.fromkeys(evidence)),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = [
    "ExtremeDamageShieldSavedBuildRecordResult",
    "ExtremeDamageShieldSavedBuildRecordService",
]
