from __future__ import annotations

import json
from dataclasses import dataclass, replace

from minmax.build_candidate import BuildCandidate
from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.race_repository import RaceRepository
from models.build_model import PlayerBuild
from services.extreme_actual_heal_arena_weapon_package_service import (
    ExtremeActualHealArenaWeaponPackageService,
)
from services.extreme_actual_heal_double_five_package_service import (
    ExtremeActualHealDoubleFivePackageService,
)
from services.extreme_actual_heal_gear_set_candidate_service import (
    ExtremeActualHealGearSetCandidateService,
)
from services.extreme_actual_heal_monster_package_service import (
    ExtremeActualHealMonsterPackageService,
)
from services.extreme_actual_heal_mythic_package_service import (
    ExtremeActualHealMythicPackageService,
)
from services.extreme_actual_heal_non_ring_mythic_package_service import (
    ExtremeActualHealNonRingMythicPackageService,
)
from services.extreme_actual_heal_reviewed_bar_candidate_service import (
    ExtremeActualHealReviewedBarCandidateService,
)
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.extreme_healing_event_service import (
    ExtremeHealingEventResult,
    ExtremeHealingEventService,
)
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter


ExtremeActualHealEvaluationCache = dict[
    tuple[str, str, str, str, str],
    tuple[ExtremeHealingEventResult, tuple[str, ...]],
]


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

    Candidate changes are materialized onto a real ``PlayerBuild`` and the full
    canonical context is rebuilt before the healing event is scored. Reviewed
    single five-piece, legal five-plus-monster, legal double-five, slot-aware
    mythic 5+5+1 shapes, and exact-subtype arena weapon packages are physically
    equipped before canonical resource/power/healing math is recalculated.
    Slot-aware non-ring mythics support both exact two-slot weapons and explicit
    paired main/off-hand weapon routing. Tooltip deltas only bound candidate
    discovery; they are never the final score.

    ``progression_override`` lets higher-level hypothetical-build search provide
    the exact progression snapshot that must survive every candidate context
    rebuild. The saved-build adapter still resolves the character identity; the
    override changes progression math only.

    ``evaluation_cache`` is an optional caller-owned structural cache. Cache keys
    contain the complete saved-build payload, normalized progression, character,
    active bar, and heal entity. Diagnostic ``build_id`` is deliberately excluded
    because it does not affect combat math. This lets staged searches share proved
    evaluations without creating persistent process-wide state.
    """

    SEARCH_SCOPE = (
        "attribute allocation across Health/Magicka/Stamina",
        "race",
        "Mundus",
        "armor traits",
        "armor enchants",
        "jewelry traits",
        "jewelry enchants",
        "weapon traits",
        "food/drink",
        "reviewed ordinary five-piece body-set replacement",
        "reviewed legal five-piece + two-piece monster body package",
        "reviewed legal five-piece + five-piece body/jewelry package",
        "reviewed legal five-piece + five-piece + ring mythic package with exact active weapon subtype proof",
        "reviewed legal five-piece + five-piece + canonically slotted non-ring mythic package with exact active two-slot or paired main/off-hand weapon proof",
        "structurally proven arena-weapon replacement with exact active weapon subtype proof, including paired main/off-hand packages",
        "reviewed active-bar Mages Guild/Fighters Guild slot-count passive carriers",
        "canonical healing coefficient scaling",
        "Healing Done and verified healing CP",
        "Critical Healing",
    )
    OMITTED_SCOPE = (
        "class change / subclass route",
        "healing-skill replacement",
        "unreviewed skill-bar passive/proc families beyond reviewed Mages/Fighters Guild slot-count effects",
        "group-only buffs",
        "runtime conditional stacks/procs",
    )

    def __init__(
        self,
        *,
        optimizer: ExtremeCompleteOptimizationService | None = None,
        healing_events: ExtremeHealingEventService | None = None,
        race_repository: RaceRepository | None = None,
        gear_set_candidates: ExtremeActualHealGearSetCandidateService | None = None,
        monster_packages: ExtremeActualHealMonsterPackageService | None = None,
        double_five_packages: ExtremeActualHealDoubleFivePackageService | None = None,
        mythic_packages: ExtremeActualHealMythicPackageService | None = None,
        non_ring_mythic_packages: ExtremeActualHealNonRingMythicPackageService | None = None,
        arena_weapon_packages: ExtremeActualHealArenaWeaponPackageService | None = None,
        reviewed_bar_candidates: ExtremeActualHealReviewedBarCandidateService | None = None,
    ) -> None:
        self.optimizer = optimizer or ExtremeCompleteOptimizationService()
        self.healing_events = healing_events or ExtremeHealingEventService(
            database_path=self.optimizer.database_path
        )
        database_path = getattr(self.optimizer, "database_path", None)
        self.race_repository = race_repository or (
            RaceRepository(database_path) if database_path else None
        )
        self.gear_set_candidates = gear_set_candidates or (
            ExtremeActualHealGearSetCandidateService(database_path)
            if database_path
            else None
        )
        self.monster_packages = monster_packages or (
            ExtremeActualHealMonsterPackageService(database_path)
            if database_path
            else None
        )
        self.double_five_packages = double_five_packages or (
            ExtremeActualHealDoubleFivePackageService(database_path)
            if database_path
            else None
        )
        self.mythic_packages = mythic_packages or (
            ExtremeActualHealMythicPackageService(database_path)
            if database_path
            else None
        )
        self.non_ring_mythic_packages = non_ring_mythic_packages or (
            ExtremeActualHealNonRingMythicPackageService(database_path)
            if database_path
            else None
        )
        self.arena_weapon_packages = arena_weapon_packages or (
            ExtremeActualHealArenaWeaponPackageService(database_path)
            if database_path
            else None
        )
        self.reviewed_bar_candidates = reviewed_bar_candidates or (
            ExtremeActualHealReviewedBarCandidateService(database_path)
            if database_path
            else None
        )

    def optimize(
        self,
        baseline_build: PlayerBuild,
        entity_id: str,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
        progression_override: CharacterProgression | None = None,
        evaluation_cache: ExtremeActualHealEvaluationCache | None = None,
    ) -> ExtremeActualHealOptimizationResult:
        normalized_entity = str(entity_id or "").strip()
        if not normalized_entity:
            raise ValueError("Healing entity_id is required")

        progression_resolution = MinmaxCharacterProgressionAdapter(
            self.optimizer.build_service.canonical.catalog_service
        ).resolve(baseline_build)
        if not progression_resolution.resolved:
            raise ValueError("; ".join(progression_resolution.unresolved))

        progression = progression_override or progression_resolution.progression
        character_id = progression_resolution.character_id
        baseline_build_id = (
            str(getattr(baseline_build, "BuildId", "") or "").strip()
            or str(baseline_build.BuildName or "").strip()
            or "saved-build"
        )
        cache = evaluation_cache if evaluation_cache is not None else {}

        current = PlayerBuild.from_dict(baseline_build.to_dict())
        baseline_event, baseline_unresolved = self._evaluate_cached(
            current,
            progression=progression,
            character_id=character_id,
            build_id=f"{baseline_build_id}:extreme-actual-heal:baseline",
            entity_id=normalized_entity,
            active_bar=active_bar,
            evaluation_cache=cache,
        )
        current_score = self._score(baseline_event)
        current_event = baseline_event
        current_unresolved = baseline_unresolved
        accepted: list[ExtremeActualHealStep] = []

        proxy_objective = self.optimizer.objective("healing_done")
        for pass_index in range(max(1, int(max_passes))):
            best: tuple[
                float,
                str,
                BuildCandidate,
                ExtremeHealingEventResult,
                tuple[str, ...],
            ] | None = None
            candidate_build_id = f"{baseline_build_id}:extreme-actual-heal:{pass_index}"
            candidates = list(
                self.optimizer._candidates(
                    current,
                    objective=proxy_objective,
                    character_id=character_id,
                    baseline_build_id=candidate_build_id,
                )
            )
            candidates.extend(
                self._resource_attribute_candidates(
                    current,
                    character_id=character_id,
                    baseline_build_id=candidate_build_id,
                )
            )
            candidates.extend(
                self._race_candidates(
                    current,
                    character_id=character_id,
                    baseline_build_id=candidate_build_id,
                )
            )
            if self.reviewed_bar_candidates is not None:
                candidates.extend(
                    self.reviewed_bar_candidates.build_candidates(
                        current,
                        progression,
                        character_id=character_id,
                        baseline_build_id=candidate_build_id,
                        protected_entity_id=normalized_entity,
                        active_bar=active_bar,
                    )
                )
            if self.gear_set_candidates is not None:
                candidates.extend(
                    self.gear_set_candidates.build_candidates(
                        current,
                        character_id=character_id,
                        baseline_build_id=candidate_build_id,
                    )
                )
            if self.monster_packages is not None:
                candidates.extend(
                    self.monster_packages.build_candidates(
                        current,
                        character_id=character_id,
                        baseline_build_id=candidate_build_id,
                    )
                )
            if self.double_five_packages is not None:
                candidates.extend(
                    self.double_five_packages.build_candidates(
                        current,
                        character_id=character_id,
                        baseline_build_id=candidate_build_id,
                    )
                )
            if self.mythic_packages is not None:
                candidates.extend(
                    self.mythic_packages.build_candidates(
                        current,
                        character_id=character_id,
                        baseline_build_id=candidate_build_id,
                        active_bar=active_bar,
                    )
                )
            if self.non_ring_mythic_packages is not None:
                candidates.extend(
                    self.non_ring_mythic_packages.build_candidates(
                        current,
                        character_id=character_id,
                        baseline_build_id=candidate_build_id,
                        active_bar=active_bar,
                    )
                )
            if self.arena_weapon_packages is not None:
                candidates.extend(
                    self.arena_weapon_packages.build_candidates(
                        current,
                        character_id=character_id,
                        baseline_build_id=candidate_build_id,
                        active_bar=active_bar,
                    )
                )
            candidates.extend(
                self._additional_candidates(
                    current,
                    progression=progression,
                    character_id=character_id,
                    baseline_build_id=candidate_build_id,
                    entity_id=normalized_entity,
                    active_bar=active_bar,
                )
            )

            for candidate in candidates:
                event, candidate_unresolved = self._evaluate_cached(
                    candidate.candidate_build,
                    progression=progression,
                    character_id=character_id,
                    build_id=candidate.candidate_id,
                    entity_id=normalized_entity,
                    active_bar=active_bar,
                    evaluation_cache=cache,
                )
                score = self._score(event)
                if score <= current_score + 1e-9:
                    continue
                if best is None or score > best[0] + 1e-9 or (
                    abs(score - best[0]) <= 1e-9
                    and candidate.candidate_id < best[1]
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
            current_unresolved = winner_unresolved

        return ExtremeActualHealOptimizationResult(
            entity_id=normalized_entity,
            baseline_build=PlayerBuild.from_dict(baseline_build.to_dict()),
            optimized_build=current,
            baseline_event=baseline_event,
            optimized_event=current_event,
            steps=tuple(accepted),
            unresolved=tuple(current_unresolved),
            search_scope=self.SEARCH_SCOPE,
            omitted_scope=self.OMITTED_SCOPE,
        )

    def _additional_candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        progression: CharacterProgression,
        character_id: str,
        baseline_build_id: str,
        entity_id: str,
        active_bar: str,
    ) -> tuple[BuildCandidate, ...]:
        _ = (
            baseline_build,
            progression,
            character_id,
            baseline_build_id,
            entity_id,
            active_bar,
        )
        return ()

    @staticmethod
    def _evaluation_key(
        build: PlayerBuild,
        *,
        progression: CharacterProgression,
        character_id: str,
        entity_id: str,
        active_bar: str,
    ) -> tuple[str, str, str, str, str]:
        build_payload = json.dumps(
            build.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return (
            build_payload,
            repr(progression),
            str(character_id or ""),
            str(entity_id or "").strip(),
            str(active_bar or "front").casefold(),
        )

    def _evaluate_cached(
        self,
        build: PlayerBuild,
        *,
        progression: CharacterProgression,
        character_id: str,
        build_id: str,
        entity_id: str,
        active_bar: str,
        evaluation_cache: ExtremeActualHealEvaluationCache,
    ) -> tuple[ExtremeHealingEventResult, tuple[str, ...]]:
        key = self._evaluation_key(
            build,
            progression=progression,
            character_id=character_id,
            entity_id=entity_id,
            active_bar=active_bar,
        )
        cached = evaluation_cache.get(key)
        if cached is not None:
            return cached
        resolved = self._evaluate(
            build,
            progression=progression,
            character_id=character_id,
            build_id=build_id,
            entity_id=entity_id,
            active_bar=active_bar,
        )
        evaluation_cache[key] = resolved
        return resolved

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
        return event, tuple(
            dict.fromkeys(message for message in unresolved if message)
        )

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
            (
                build.AttributeHealth,
                build.AttributeMagicka,
                build.AttributeStamina,
            ) = allocation
            result.append(
                ExtremeCompleteOptimizationService._direct_candidate(
                    build,
                    character_id=character_id,
                    baseline_build_id=baseline_build_id,
                    token=f"actual-heal-attributes:{resource}",
                    path="Attributes",
                    before={
                        "health": before[0],
                        "magicka": before[1],
                        "stamina": before[2],
                    },
                    after={
                        "health": allocation[0],
                        "magicka": allocation[1],
                        "stamina": allocation[2],
                    },
                    source="extreme:actual-heal:attributes",
                )
            )
        return tuple(result)

    def _race_candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        character_id: str,
        baseline_build_id: str,
    ) -> tuple[BuildCandidate, ...]:
        if self.race_repository is None:
            return ()
        before = str(baseline_build.Race or "").strip()
        result: list[BuildCandidate] = []
        for race in self.race_repository.list_races():
            name = str(race.name or "").strip()
            if not name or name.casefold() == before.casefold():
                continue
            build = PlayerBuild.from_dict(baseline_build.to_dict())
            build.Race = name
            result.append(
                ExtremeCompleteOptimizationService._direct_candidate(
                    build,
                    character_id=character_id,
                    baseline_build_id=baseline_build_id,
                    token=f"actual-heal-race:{name}",
                    path="Race",
                    before=before,
                    after=name,
                    source="extreme:actual-heal:race",
                )
            )
        return tuple(result)
