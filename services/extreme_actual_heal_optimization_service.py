from __future__ import annotations

from dataclasses import dataclass, replace

from minmax.build_candidate import BuildCandidate
from minmax.character_progression import AttributeAllocation, CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.extreme_healing_event_service import (
    ExtremeHealingEventResult,
    ExtremeHealingEventService,
)
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter


@dataclass(frozen=True)
class ExtremeActualHealStep:
    path: str
    before: object
    after: object
    critical_heal_before: float
    critical_heal_after: float

    @property
    def delta(self) -> float:
        return self.critical_heal_after - self.critical_heal_before


@dataclass(frozen=True)
class ExtremeActualHealOptimizationResult:
    entity_id: str
    baseline_build: PlayerBuild
    optimized_build: PlayerBuild
    baseline_event: ExtremeHealingEventResult
    optimized_event: ExtremeHealingEventResult
    steps: tuple[ExtremeActualHealStep, ...]
    unresolved: tuple[str, ...]
    search_scope: tuple[str, ...]
    omitted_scope: tuple[str, ...]

    @property
    def mechanic_complete(self) -> bool:
        return self.optimized_event.mechanic_complete and not self.unresolved

    @property
    def gain(self) -> float:
        before = float(self.baseline_event.critical_heal or 0.0)
        after = float(self.optimized_event.critical_heal or 0.0)
        return after - before


class ExtremeActualHealOptimizationService:
    """Maximize one identified healing event through canonical whole-build math.

    This is the scoring engine for ``MOST Actual Heal``. It deliberately starts
    with mutation families already owned by the shared Extreme optimizer, then
    adds all-resource attribute allocations because heal coefficients scale from
    the character's highest Max Resource. Class/race/gear-set/skill replacement
    remain explicit omitted scope until their candidate generators are widened.
    """

    SEARCH_SCOPE = (
        "attribute allocation across Health/Magicka/Stamina",
        "Mundus",
        "armor traits",
        "armor enchants",
        "jewelry traits",
        "jewelry enchants",
        "weapon traits",
        "food/drink",
        "canonical healing coefficient scaling",
        "Healing Done and verified healing CP",
        "Critical Healing",
    )
    OMITTED_SCOPE = (
        "gear-set replacement",
        "class change / subclass route",
        "race change",
        "healing-skill replacement",
        "skill-bar passive/proc search",
        "group-only buffs",
        "runtime conditional stacks/procs",
    )

    def __init__(
        self,
        *,
        optimizer: ExtremeCompleteOptimizationService | None = None,
        healing_events: ExtremeHealingEventService | None = None,
    ) -> None:
        self.optimizer = optimizer or ExtremeCompleteOptimizationService()
        self.healing_events = healing_events or ExtremeHealingEventService(
            database_path=self.optimizer.database_path
        )

    def optimize(
        self,
        baseline_build: PlayerBuild,
        entity_id: str,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
    ) -> ExtremeActualHealOptimizationResult:
        normalized_entity = str(entity_id or "").strip()
        if not normalized_entity:
            raise ValueError("Healing entity_id is required")

        progression_resolution = MinmaxCharacterProgressionAdapter(
            self.optimizer.build_service.canonical.catalog_service
        ).resolve(baseline_build)
        if not progression_resolution.resolved:
            raise ValueError("; ".join(progression_resolution.unresolved))

        progression = progression_resolution.progression
        character_id = progression_resolution.character_id
        baseline_build_id = (
            str(getattr(baseline_build, "BuildId", "") or "").strip()
            or str(baseline_build.BuildName or "").strip()
            or "saved-build"
        )

        current = PlayerBuild.from_dict(baseline_build.to_dict())
        baseline_event, baseline_unresolved = self._evaluate(
            current,
            progression=progression,
            character_id=character_id,
            build_id=f"{baseline_build_id}:extreme-actual-heal:baseline",
            entity_id=normalized_entity,
            active_bar=active_bar,
        )
        current_score = self._score(baseline_event)
        current_event = baseline_event
        unresolved = list(baseline_unresolved)
        accepted: list[ExtremeActualHealStep] = []

        proxy_objective = self.optimizer.objective("healing_done")
        for pass_index in range(max(1, int(max_passes))):
            best: tuple[float, str, BuildCandidate, ExtremeHealingEventResult, tuple[str, ...]] | None = None
            candidates = list(self.optimizer._candidates(
                current,
                objective=proxy_objective,
                character_id=character_id,
                baseline_build_id=f"{baseline_build_id}:extreme-actual-heal:{pass_index}",
            ))
            candidates.extend(self._resource_attribute_candidates(
                current,
                character_id=character_id,
                baseline_build_id=f"{baseline_build_id}:extreme-actual-heal:{pass_index}",
            ))

            for candidate in candidates:
                event, candidate_unresolved = self._evaluate(
                    candidate.candidate_build,
                    progression=progression,
                    character_id=character_id,
                    build_id=candidate.candidate_id,
                    entity_id=normalized_entity,
                    active_bar=active_bar,
                )
                unresolved.extend(candidate_unresolved)
                score = self._score(event)
                if score <= current_score + 1e-9:
                    continue
                if best is None or score > best[0] + 1e-9 or (
                    abs(score - best[0]) <= 1e-9 and candidate.candidate_id < best[1]
                ):
                    best = (
                        score,
                        candidate.candidate_id,
                        candidate,
                        event,
                        candidate_unresolved,
                    )

            if best is None:
                break

            next_score, _, winner, winner_event, winner_unresolved = best
            change = winner.changes[0]
            accepted.append(
                ExtremeActualHealStep(
                    path=change.path,
                    before=change.before,
                    after=change.after,
                    critical_heal_before=current_score,
                    critical_heal_after=next_score,
                )
            )
            current = winner.candidate_build
            current_score = next_score
            current_event = winner_event
            unresolved.extend(winner_unresolved)

        return ExtremeActualHealOptimizationResult(
            entity_id=normalized_entity,
            baseline_build=PlayerBuild.from_dict(baseline_build.to_dict()),
            optimized_build=current,
            baseline_event=baseline_event,
            optimized_event=current_event,
            steps=tuple(accepted),
            unresolved=tuple(dict.fromkeys(message for message in unresolved if message)),
            search_scope=self.SEARCH_SCOPE,
            omitted_scope=self.OMITTED_SCOPE,
        )

    def _evaluate(
        self,
        build: PlayerBuild,
        *,
        progression: CharacterProgression,
        character_id: str,
        build_id: str,
        entity_id: str,
        active_bar: str,
    ) -> tuple[ExtremeHealingEventResult, tuple[str, ...]]:
        candidate_progression = replace(
            progression,
            attributes=AttributeAllocation(
                health=int(build.AttributeHealth or 0),
                magicka=int(build.AttributeMagicka or 0),
                stamina=int(build.AttributeStamina or 0),
            ),
        )
        context = self.optimizer.context_factory.build(
            character_id=character_id,
            build_id=build_id,
            build=build,
            progression=candidate_progression,
            active_bar=active_bar,
        )
        event = self.healing_events.evaluate(
            build=build,
            context=context,
            entity_id=entity_id,
        )
        unresolved = tuple(context.unresolved_gear_effects) + tuple(event.unresolved)
        return event, tuple(dict.fromkeys(message for message in unresolved if message))

    @staticmethod
    def _score(event: ExtremeHealingEventResult) -> float:
        if event.critical_heal is None:
            raise ValueError(
                f"Cannot optimize {event.entity_id!r}: critical healing event is unresolved"
            )
        return float(event.critical_heal)

    @staticmethod
    def _resource_attribute_candidates(
        baseline_build: PlayerBuild,
        *,
        character_id: str,
        baseline_build_id: str,
    ) -> tuple[BuildCandidate, ...]:
        before = (
            int(baseline_build.AttributeHealth or 0),
            int(baseline_build.AttributeMagicka or 0),
            int(baseline_build.AttributeStamina or 0),
        )
        result: list[BuildCandidate] = []
        for resource, allocation in (
            ("health", (64, 0, 0)),
            ("magicka", (0, 64, 0)),
            ("stamina", (0, 0, 64)),
        ):
            if before == allocation:
                continue
            build = PlayerBuild.from_dict(baseline_build.to_dict())
            build.AttributeHealth, build.AttributeMagicka, build.AttributeStamina = allocation
            result.append(
                ExtremeCompleteOptimizationService._direct_candidate(
                    build,
                    character_id=character_id,
                    baseline_build_id=baseline_build_id,
                    token=f"actual-heal-attributes:{resource}",
                    path="Attributes",
                    before={"health": before[0], "magicka": before[1], "stamina": before[2]},
                    after={"health": allocation[0], "magicka": allocation[1], "stamina": allocation[2]},
                    source="extreme:actual-heal:attributes",
                )
            )
        return tuple(result)
