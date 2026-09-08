from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minmax.character_build.character_class import CharacterClass
from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_heal_class_route_service import (
    ExtremeHealClassRoute,
    ExtremeHealClassRouteService,
)
from services.extreme_hypothetical_class_progression_service import (
    ExtremeHypotheticalClassProgressionService,
)
from services.extreme_sorcerer_blood_magic_actual_heal_service import (
    ExtremeSorcererBloodMagicActualHealResult,
    ExtremeSorcererBloodMagicActualHealService,
)
from services.extreme_sorcerer_blood_magic_trigger_candidate_service import (
    ExtremeSorcererBloodMagicTriggerCandidate,
    ExtremeSorcererBloodMagicTriggerCandidateService,
)
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter


@dataclass(frozen=True)
class ExtremeSorcererBloodMagicClassRouteEntry:
    route: ExtremeHealClassRoute
    trigger: ExtremeSorcererBloodMagicTriggerCandidate
    slotted_index: int
    candidate_build: PlayerBuild
    optimization: ExtremeSorcererBloodMagicActualHealResult | None
    error: str = ""

    @property
    def normal_heal(self) -> float | None:
        if self.optimization is None:
            return None
        return self.optimization.optimized_event.normal_heal

    @property
    def mechanic_complete(self) -> bool:
        return bool(self.optimization and self.optimization.mechanic_complete and not self.error)

    @property
    def unresolved(self) -> tuple[str, ...]:
        if self.optimization is not None:
            return tuple(self.optimization.unresolved)
        return (self.error,) if self.error else ()


@dataclass(frozen=True)
class ExtremeSorcererBloodMagicClassRouteCatalogResult:
    entries: tuple[ExtremeSorcererBloodMagicClassRouteEntry, ...]
    best_scored: ExtremeSorcererBloodMagicClassRouteEntry | None
    best_complete: ExtremeSorcererBloodMagicClassRouteEntry | None
    search_scope: tuple[str, ...]
    omitted_scope: tuple[str, ...]


class ExtremeSorcererBloodMagicClassRouteCatalogService:
    """Rank the U50 Blood Magic normal-heal event across legal class routes.

    A route enters only when it equips Dark Magic and canonical data supplies at
    least one concrete active Dark Magic ability with a positive base cost. Each
    trigger ability is materially slotted into every ordinary active-bar position,
    then the route's normalized hypothetical progression is preserved through the
    whole-build Max Health search.

    This catalog is intentionally normal-heal only. Blood Magic critical
    eligibility remains unresolved, so its results must not be merged into the
    ordinary critical-heal ranking until that mechanic is proven.
    """

    SEARCH_SCOPE = (
        "structurally legal routes that equip Dark Magic",
        "canonical positive-cost active Dark Magic trigger casts",
        "trigger-cast replacement across the five ordinary active-bar slots",
        "hypothetical selected-class-line max progression normalization",
        "whole-build canonical Max Health optimization",
        "Blood Magic U50 rank-2 normal heal at 10% of Max Health",
    )
    OMITTED_SCOPE = (
        "Blood Magic critical-heal eligibility",
        "global comparison against critical ordinary-heal candidates",
        "full multi-skill active/back-bar combinatorial search",
        "runtime proof that caster is below full Health at trigger time",
    )

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        blood_magic: ExtremeSorcererBloodMagicActualHealService | None = None,
        triggers: ExtremeSorcererBloodMagicTriggerCandidateService | None = None,
        routes: ExtremeHealClassRouteService | None = None,
        progression_normalizer: ExtremeHypotheticalClassProgressionService | None = None,
    ) -> None:
        self.blood_magic = blood_magic or ExtremeSorcererBloodMagicActualHealService()
        resolved_path = Path(database_path or self.blood_magic.optimizer.database_path)
        self.triggers = triggers or ExtremeSorcererBloodMagicTriggerCandidateService(resolved_path)
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
    ) -> ExtremeSorcererBloodMagicClassRouteCatalogResult:
        progression = self._progression(baseline_build)
        baseline_class = self._base_class(baseline_build)
        base_classes = tuple(CharacterClass) if include_base_class_changes else (baseline_class,)
        triggers = self.triggers.candidates()

        entries: list[ExtremeSorcererBloodMagicClassRouteEntry] = []
        for base_class in base_classes:
            for route in self.routes.routes_for_base_class(base_class):
                if "dark_magic" not in set(route.equipped_skill_lines):
                    continue
                route_build = self.routes.materialize_build(baseline_build, route)
                route_progression = self.progression_normalizer.normalize(progression, route)
                for trigger in triggers:
                    entries.append(
                        self._best_slot_entry(
                            route_build,
                            route=route,
                            route_progression=route_progression,
                            trigger=trigger,
                            active_bar=active_bar,
                            max_passes=max_passes,
                        )
                    )

        ranked = tuple(sorted(entries, key=self._rank_key))
        scored = tuple(entry for entry in ranked if entry.normal_heal is not None)
        complete = tuple(entry for entry in scored if entry.mechanic_complete)
        search_scope = list(self.SEARCH_SCOPE)
        omitted_scope = list(self.OMITTED_SCOPE)
        if include_base_class_changes:
            search_scope.insert(0, "all seven ESO base classes")
        else:
            search_scope.insert(0, "current saved-build base class")
            omitted_scope.insert(0, "base-class change")
        return ExtremeSorcererBloodMagicClassRouteCatalogResult(
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
        trigger: ExtremeSorcererBloodMagicTriggerCandidate,
        active_bar: str,
        max_passes: int,
    ) -> ExtremeSorcererBloodMagicClassRouteEntry:
        best: ExtremeSorcererBloodMagicClassRouteEntry | None = None
        for slot_index, build in self._slot_variants(
            route_build,
            trigger.name,
            active_bar=active_bar,
        ):
            try:
                optimization = self.blood_magic.optimize(
                    build,
                    active_bar=active_bar,
                    max_passes=max_passes,
                    progression_override=route_progression,
                )
                entry = ExtremeSorcererBloodMagicClassRouteEntry(
                    route=route,
                    trigger=trigger,
                    slotted_index=slot_index,
                    candidate_build=build,
                    optimization=optimization,
                )
            except (ValueError, LookupError) as exc:
                entry = ExtremeSorcererBloodMagicClassRouteEntry(
                    route=route,
                    trigger=trigger,
                    slotted_index=slot_index,
                    candidate_build=build,
                    optimization=None,
                    error=str(exc),
                )
            if best is None or self._slot_rank_key(entry) < self._slot_rank_key(best):
                best = entry
        if best is None:
            raise ValueError(f"No ordinary active-bar slot available for Blood Magic trigger: {trigger.name}")
        return best

    @staticmethod
    def _slot_variants(
        baseline_build: PlayerBuild,
        trigger_name: str,
        *,
        active_bar: str,
    ) -> tuple[tuple[int, PlayerBuild], ...]:
        attr = "BackBarSkills" if str(active_bar or "front").casefold() == "back" else "FrontBarSkills"
        original = list(getattr(baseline_build, attr))
        while len(original) < 6:
            original.append("")
        original = original[:6]
        existing = next(
            (
                index
                for index, name in enumerate(original[:5])
                if str(name or "").strip().casefold() == trigger_name.casefold()
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
            skills[index] = trigger_name
            setattr(build, attr, skills)
            result.append((index, build))
        return tuple(result)

    def _progression(self, build: PlayerBuild) -> CharacterProgression:
        resolution = MinmaxCharacterProgressionAdapter(
            self.blood_magic.optimizer.build_service.canonical.catalog_service
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
    def _slot_rank_key(entry: ExtremeSorcererBloodMagicClassRouteEntry) -> tuple[float, int, str]:
        score = entry.normal_heal
        return (
            -(float(score) if score is not None else float("-inf")),
            entry.slotted_index,
            entry.error,
        )

    @staticmethod
    def _rank_key(entry: ExtremeSorcererBloodMagicClassRouteEntry) -> tuple[float, str, str, tuple[str, ...], int]:
        score = entry.normal_heal
        return (
            -(float(score) if score is not None else float("-inf")),
            entry.route.base_class.value,
            entry.trigger.name.casefold(),
            entry.route.equipped_skill_lines,
            entry.slotted_index,
        )
