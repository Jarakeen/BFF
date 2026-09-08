from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationResult,
    ExtremeActualHealOptimizationService,
)
from services.extreme_heal_skill_candidate_service import (
    ExtremeHealSkillCandidate,
    ExtremeHealSkillCandidateService,
)
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter


@dataclass(frozen=True)
class ExtremeActualHealCatalogEntry:
    candidate: ExtremeHealSkillCandidate
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
class ExtremeActualHealCatalogResult:
    entries: tuple[ExtremeActualHealCatalogEntry, ...]
    blocked_candidates: tuple[ExtremeHealSkillCandidate, ...]
    best_scored: ExtremeActualHealCatalogEntry | None
    best_complete: ExtremeActualHealCatalogEntry | None
    search_scope: tuple[str, ...]
    omitted_scope: tuple[str, ...]

    @property
    def global_maximum_proven(self) -> bool:
        # This claim is scoped to candidates proven legal for the current build.
        # Wrong-class, passive, non-player, and explicitly unowned-line rows stay
        # visible in blocked_candidates for evidence, but they cannot invalidate
        # a maximum among the legal candidate set.
        return bool(
            self.entries
            and self.best_scored is not None
            and self.best_scored.mechanic_complete
            and all(entry.mechanic_complete for entry in self.entries)
        )


class ExtremeActualHealCatalogService:
    """Compare every currently legal canonical heal through whole-build scoring.

    ``best_scored`` is the largest numeric evaluated event, even when that event
    is only a reviewed lower bound. ``best_complete`` is the largest fully
    resolved event. ``global_maximum_proven`` is intentionally stricter and is
    true only when every discovered legal candidate evaluated completely.

    Current-build legality is the boundary here. Subclass-route expansion,
    weapon/bar replacement, skill-bar passive/proc search, gear-set replacement,
    and race replacement remain explicit omitted scope rather than disappearing.
    """

    OMITTED_SCOPE = (
        "subclass-route expansion",
        "weapon/bar replacement required to unlock another skill line",
        "skill-bar passive/proc search",
        "gear-set replacement",
        "race replacement",
        "group-only buffs",
        "runtime conditional stacks/procs",
    )

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        optimizer: ExtremeActualHealOptimizationService | None = None,
        candidates: ExtremeHealSkillCandidateService | None = None,
    ) -> None:
        self.optimizer = optimizer or ExtremeActualHealOptimizationService()
        resolved_path = Path(
            database_path
            or self.optimizer.optimizer.database_path
        )
        self.candidates = candidates or ExtremeHealSkillCandidateService(resolved_path)

    def rank(
        self,
        baseline_build: PlayerBuild,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
    ) -> ExtremeActualHealCatalogResult:
        progression = self._progression(baseline_build)
        all_candidates = self.candidates.candidates_for_build(
            baseline_build,
            progression,
            include_blocked=True,
        )
        legal = tuple(candidate for candidate in all_candidates if candidate.legal)
        blocked = tuple(candidate for candidate in all_candidates if not candidate.legal)

        entries: list[ExtremeActualHealCatalogEntry] = []
        for candidate in legal:
            try:
                optimization = self.optimizer.optimize(
                    baseline_build,
                    candidate.entity_id,
                    active_bar=active_bar,
                    max_passes=max_passes,
                )
            except (ValueError, LookupError) as exc:
                entries.append(
                    ExtremeActualHealCatalogEntry(
                        candidate=candidate,
                        optimization=None,
                        error=str(exc),
                    )
                )
                continue
            entries.append(
                ExtremeActualHealCatalogEntry(
                    candidate=candidate,
                    optimization=optimization,
                )
            )

        ranked = tuple(sorted(entries, key=self._rank_key))
        scored = tuple(entry for entry in ranked if entry.critical_heal is not None)
        complete = tuple(entry for entry in scored if entry.mechanic_complete)
        best_scored = scored[0] if scored else None
        best_complete = complete[0] if complete else None

        return ExtremeActualHealCatalogResult(
            entries=ranked,
            blocked_candidates=blocked,
            best_scored=best_scored,
            best_complete=best_complete,
            search_scope=(
                "all canonical HEAL-classified active skills legal to the current build",
                *ExtremeActualHealOptimizationService.SEARCH_SCOPE,
            ),
            omitted_scope=self.OMITTED_SCOPE,
        )

    def _progression(self, build: PlayerBuild) -> CharacterProgression:
        core_optimizer = self.optimizer.optimizer
        resolution = MinmaxCharacterProgressionAdapter(
            core_optimizer.build_service.canonical.catalog_service
        ).resolve(build)
        if not resolution.resolved:
            raise ValueError("; ".join(resolution.unresolved))
        return resolution.progression

    @staticmethod
    def _rank_key(entry: ExtremeActualHealCatalogEntry) -> tuple[float, str, str]:
        score = entry.critical_heal
        return (
            -(float(score) if score is not None else float("-inf")),
            entry.candidate.name.casefold(),
            entry.candidate.entity_id,
        )
