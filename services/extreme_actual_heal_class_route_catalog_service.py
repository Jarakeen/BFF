from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minmax.character_build.character_class import CharacterClass
from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationResult,
    ExtremeActualHealOptimizationService,
)
from services.extreme_canonical_actual_heal_optimization_service import (
    ExtremeCanonicalActualHealOptimizationService,
)
from services.extreme_heal_class_route_service import (
    ExtremeHealClassRoute,
    ExtremeHealClassRouteService,
)
from services.extreme_heal_skill_candidate_service import (
    ExtremeHealSkillCandidate,
    ExtremeHealSkillCandidateService,
)
from services.extreme_hypothetical_class_progression_service import (
    ExtremeHypotheticalClassProgressionService,
)
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter


@dataclass(frozen=True)
class ExtremeActualHealClassRouteEntry:
    route: ExtremeHealClassRoute
    candidate: ExtremeHealSkillCandidate
    slotted_index: int
    candidate_build: PlayerBuild
    optimization: ExtremeActualHealOptimizationResult | None
    error: str = ""

    @property
    def critical_heal(self) -> float | None:
        if self.optimization is None:
            return None
        return self.optimization.optimized_event.critical_heal

    @property
    def mechanic_complete(self) -> bool:
        return bool(self.optimization and self.optimization.mechanic_complete and not self.error)

    @property
    def unresolved(self) -> tuple[str, ...]:
        if self.optimization is not None:
            return tuple(self.optimization.unresolved)
        return (self.error,) if self.error else ()


@dataclass(frozen=True)
class ExtremeActualHealClassRouteCatalogResult:
    entries: tuple[ExtremeActualHealClassRouteEntry, ...]
    best_scored: ExtremeActualHealClassRouteEntry | None
    best_complete: ExtremeActualHealClassRouteEntry | None
    search_scope: tuple[str, ...]
    omitted_scope: tuple[str, ...]

    @property
    def global_maximum_proven(self) -> bool:
        # Route scoring remains a lower-bound comparison until every class-line
        # passive/proc family and the remaining runtime/group surfaces are modeled.
        return bool(
            self.entries
            and not self.omitted_scope
            and self.best_scored is not None
            and self.best_scored.mechanic_complete
            and all(entry.mechanic_complete for entry in self.entries)
        )


class ExtremeActualHealClassRouteCatalogService:
    """Score legal base-class/class-line routes plus one selected active heal.

    By default the service keeps the saved build's base class and exhaustively
    searches structurally legal three-class-line configurations for that class.
    ``include_base_class_changes=True`` widens discovery across all seven ESO
    base classes, materializing each route onto a real ``PlayerBuild`` before
    heal discovery and whole-build scoring.

    Every route receives a hypothetical fully-leveled class progression snapshot:
    non-class progression is preserved, unequipped class-line passives are removed,
    and passives belonging to the three selected class lines are populated at the
    canonical recorded maximum rank. That exact progression snapshot is then
    passed through every whole-build candidate context rebuild.

    This progression normalization proves ownership/rank availability only. It
    does not pretend every passive effect/proc is modeled, so incomplete mechanic
    families remain explicit omitted scope and prevent a false global-proof claim.

    The five ordinary skill positions are searched because the selected heal
    must be present for slot-counted passive math. Weapon-skill heals are filtered
    against the concrete weapon configuration on the selected active bar before
    scoring. The ultimate slot is preserved. This is not yet a full multi-skill
    bar optimizer.
    """

    SEARCH_SCOPE = (
        "structurally legal class-line routes",
        "hypothetical selected-class-line max progression normalization",
        "class-line-aware canonical HEAL candidate discovery per route",
        "active-bar weapon-skill legality for HEAL candidates",
        "selected heal replacement across the five ordinary active-bar slots",
        *ExtremeActualHealOptimizationService.SEARCH_SCOPE,
    )
    OMITTED_SCOPE = (
        "full multi-skill active/back-bar combinatorial search",
        "complete class-line passive/proc coverage for every equipped route",
        "group-only buffs",
        "runtime conditional stacks/procs",
    )

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        optimizer: ExtremeActualHealOptimizationService | None = None,
        candidates: ExtremeHealSkillCandidateService | None = None,
        routes: ExtremeHealClassRouteService | None = None,
        progression_normalizer: ExtremeHypotheticalClassProgressionService | None = None,
    ) -> None:
        self.optimizer = optimizer or ExtremeCanonicalActualHealOptimizationService()
        resolved_path = Path(database_path or self.optimizer.optimizer.database_path)
        self.candidates = candidates or ExtremeHealSkillCandidateService(resolved_path)
        self.routes = routes or ExtremeHealClassRouteService()
        self.progression_normalizer = progression_normalizer or (
            ExtremeHypotheticalClassProgressionService(resolved_path)
        )

    def rank(
        self,
        baseline_build: PlayerBuild,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
        include_base_class_changes: bool = False,
    ) -> ExtremeActualHealClassRouteCatalogResult:
        progression = self._progression(baseline_build)
        baseline_class = self._base_class(baseline_build)
        base_classes = (
            tuple(CharacterClass)
            if include_base_class_changes
            else (baseline_class,)
        )

        entries: list[ExtremeActualHealClassRouteEntry] = []
        for base_class in base_classes:
            for route in self.routes.routes_for_base_class(base_class):
                route_build = self.routes.materialize_build(baseline_build, route)
                route_progression = self.progression_normalizer.normalize(
                    progression,
                    route,
                )
                route_candidates = self.candidates.candidates_for_build(
                    route_build,
                    route_progression,
                    class_configuration=route.configuration,
                    active_bar=active_bar,
                )
                for candidate in route_candidates:
                    entry = self._best_slot_entry(
                        route_build,
                        route=route,
                        route_progression=route_progression,
                        candidate=candidate,
                        active_bar=active_bar,
                        max_passes=max_passes,
                    )
                    entries.append(entry)

        ranked = tuple(sorted(entries, key=self._rank_key))
        scored = tuple(entry for entry in ranked if entry.critical_heal is not None)
        complete = tuple(entry for entry in scored if entry.mechanic_complete)

        search_scope = list(self.SEARCH_SCOPE)
        omitted_scope = list(self.OMITTED_SCOPE)
        if include_base_class_changes:
            search_scope.insert(0, "all seven ESO base classes")
        else:
            search_scope.insert(0, "current saved-build base class")
            omitted_scope.insert(0, "base-class change")

        return ExtremeActualHealClassRouteCatalogResult(
            entries=ranked,
            best_scored=scored[0] if scored else None,
            best_complete=complete[0] if complete else None,
            search_scope=tuple(search_scope),
            omitted_scope=tuple(omitted_scope),
        )

    def _best_slot_entry(
        self,
        route_build: PlayerBuild,
        *,
        route: ExtremeHealClassRoute,
        route_progression: CharacterProgression,
        candidate: ExtremeHealSkillCandidate,
        active_bar: str,
        max_passes: int,
    ) -> ExtremeActualHealClassRouteEntry:
        best: ExtremeActualHealClassRouteEntry | None = None
        for slot_index, build in self._heal_slot_variants(
            route_build,
            candidate.name,
            active_bar=active_bar,
        ):
            try:
                optimization = self.optimizer.optimize(
                    build,
                    candidate.entity_id,
                    active_bar=active_bar,
                    max_passes=max_passes,
                    progression_override=route_progression,
                )
                entry = ExtremeActualHealClassRouteEntry(
                    route=route,
                    candidate=candidate,
                    slotted_index=slot_index,
                    candidate_build=build,
                    optimization=optimization,
                )
            except (ValueError, LookupError) as exc:
                entry = ExtremeActualHealClassRouteEntry(
                    route=route,
                    candidate=candidate,
                    slotted_index=slot_index,
                    candidate_build=build,
                    optimization=None,
                    error=str(exc),
                )

            if best is None or self._slot_rank_key(entry) < self._slot_rank_key(best):
                best = entry

        if best is None:
            raise ValueError(f"No ordinary active-bar slot available for heal: {candidate.name}")
        return best

    @staticmethod
    def _heal_slot_variants(
        baseline_build: PlayerBuild,
        heal_name: str,
        *,
        active_bar: str,
    ) -> tuple[tuple[int, PlayerBuild], ...]:
        normalized_bar = str(active_bar or "front").casefold()
        attr = "BackBarSkills" if normalized_bar == "back" else "FrontBarSkills"
        original = list(getattr(baseline_build, attr))
        while len(original) < 6:
            original.append("")
        original = original[:6]

        existing = next(
            (
                index
                for index, name in enumerate(original[:5])
                if str(name or "").strip().casefold() == str(heal_name or "").strip().casefold()
            ),
            None,
        )
        indices = (existing,) if existing is not None else tuple(range(5))

        result: list[tuple[int, PlayerBuild]] = []
        for index in indices:
            build = PlayerBuild.from_dict(baseline_build.to_dict())
            skills = list(getattr(build, attr))
            while len(skills) < 6:
                skills.append("")
            skills = skills[:6]
            skills[index] = heal_name
            setattr(build, attr, skills)
            result.append((index, build))
        return tuple(result)

    def _progression(self, build: PlayerBuild) -> CharacterProgression:
        core_optimizer = self.optimizer.optimizer
        resolution = MinmaxCharacterProgressionAdapter(
            core_optimizer.build_service.canonical.catalog_service
        ).resolve(build)
        if not resolution.resolved:
            raise ValueError("; ".join(resolution.unresolved))
        return resolution.progression

    @staticmethod
    def _base_class(build: PlayerBuild) -> CharacterClass:
        key = str(build.EsoClass or "").strip().casefold()
        match = next((value for value in CharacterClass if value.value == key), None)
        if match is None:
            raise ValueError(f"Unsupported or missing ESO class: {build.EsoClass or '(empty)'}")
        return match

    @staticmethod
    def _slot_rank_key(entry: ExtremeActualHealClassRouteEntry) -> tuple[float, int, str]:
        score = entry.critical_heal
        return (
            -(float(score) if score is not None else float("-inf")),
            entry.slotted_index,
            entry.error,
        )

    @staticmethod
    def _rank_key(
        entry: ExtremeActualHealClassRouteEntry,
    ) -> tuple[float, str, str, tuple[str, ...], int]:
        score = entry.critical_heal
        return (
            -(float(score) if score is not None else float("-inf")),
            entry.route.base_class.value,
            entry.candidate.name.casefold(),
            entry.route.equipped_skill_lines,
            entry.slotted_index,
        )
