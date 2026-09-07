from __future__ import annotations

"""Truthful source-coverage contract for Extreme Build objectives.

The Extreme engine can only call a result globally maximal when every source
family that could materially affect the objective has been either reviewed or
explicitly proven not applicable. Candidate generation may still return a
useful best reviewed lower bound while that broader proof is incomplete.

This module intentionally contains no ESO stat values. It describes coverage
of mechanic *families*, not their numeric contribution.
"""

from dataclasses import dataclass
from enum import Enum


class ExtremeSourceCoverageStatus(str, Enum):
    REVIEWED = "reviewed"
    PARTIAL = "partial"
    CONTEXT_ONLY = "context_only"
    NOT_MODELED = "not_modeled"
    UNREVIEWED = "unreviewed"
    NOT_APPLICABLE = "not_applicable"


class ExtremeObjectiveClaim(str, Enum):
    BEST_REVIEWED_LOWER_BOUND = "best_reviewed_lower_bound"
    COMPLETE_WITHIN_REVIEWED_SOURCE_CONTRACT = "complete_within_reviewed_source_contract"
    GLOBAL_MAXIMUM_READY = "global_maximum_ready"


@dataclass(frozen=True)
class ExtremeSourceFamilyCoverage:
    source_family: str
    status: ExtremeSourceCoverageStatus
    note: str = ""

    @property
    def blocks_global_maximum(self) -> bool:
        return self.status not in {
            ExtremeSourceCoverageStatus.REVIEWED,
            ExtremeSourceCoverageStatus.NOT_APPLICABLE,
        }


@dataclass(frozen=True)
class ExtremeObjectiveCoverage:
    objective_key: str
    sources: tuple[ExtremeSourceFamilyCoverage, ...]
    source_universe_reviewed: bool = False

    @property
    def blocking_sources(self) -> tuple[ExtremeSourceFamilyCoverage, ...]:
        return tuple(source for source in self.sources if source.blocks_global_maximum)

    @property
    def reviewed_sources(self) -> tuple[ExtremeSourceFamilyCoverage, ...]:
        return tuple(
            source
            for source in self.sources
            if source.status is ExtremeSourceCoverageStatus.REVIEWED
        )

    @property
    def global_maximum_ready(self) -> bool:
        return self.source_universe_reviewed and not self.blocking_sources

    @property
    def claim(self) -> ExtremeObjectiveClaim:
        if self.global_maximum_ready:
            return ExtremeObjectiveClaim.GLOBAL_MAXIMUM_READY
        if not self.blocking_sources and self.reviewed_sources:
            return ExtremeObjectiveClaim.COMPLETE_WITHIN_REVIEWED_SOURCE_CONTRACT
        return ExtremeObjectiveClaim.BEST_REVIEWED_LOWER_BOUND


class ExtremeObjectiveCoverageService:
    """Describe what the current Extreme engine can honestly claim.

    ``source_universe_reviewed=False`` is deliberate for the Phase 13.2 seed.
    The source-family list is a conservative audit surface, not a claim that
    every listed family contributes to every ESO objective. A later review may
    mark a family ``NOT_APPLICABLE`` for a specific objective once that absence
    itself is established.
    """

    REVIEWED_OBJECTIVES = (
        "critical_damage",
        "magicka_recovery",
        "stamina_recovery",
        "physical_resistance",
        "spell_resistance",
        "spell_damage",
        "weapon_damage",
        "spell_critical",
        "weapon_critical",
    )

    SOURCE_FAMILIES = (
        "class_passives",
        "slotted_skills",
        "gear_sets",
        "armor_weight_passives",
        "race",
        "mundus",
        "champion_points",
        "enchantments",
        "consumables",
        "runtime_procs",
        "group_context",
        "encounter_context",
    )

    _PHASE13_2_STATUS = {
        "class_passives": (
            ExtremeSourceCoverageStatus.REVIEWED,
            "Reviewed class/subclass passive formulas are represented for the current objective matrix.",
        ),
        "slotted_skills": (
            ExtremeSourceCoverageStatus.REVIEWED,
            "Reviewed standing slotted-skill effects and front/back/either-bar scope are represented.",
        ),
        "gear_sets": (
            ExtremeSourceCoverageStatus.NOT_MODELED,
            "Extreme candidate generation does not yet exhaustively enumerate gear-set contributions.",
        ),
        "armor_weight_passives": (
            ExtremeSourceCoverageStatus.NOT_MODELED,
            "Armor-weight/passive combinations are not yet exhaustively searched by the Extreme engine.",
        ),
        "race": (
            ExtremeSourceCoverageStatus.PARTIAL,
            "Canonical aggregate/max-rank race_stat contributions can now be enumerated for reviewed Extreme objectives, but conditional and non-structured racial passive mechanics are not yet exhaustively projected.",
        ),
        "mundus": (
            ExtremeSourceCoverageStatus.PARTIAL,
            "Canonical update-versioned Mundus base effects can now be projected for reviewed Extreme objectives, but armor-trait/other Mundus multipliers are not yet exhaustively optimized.",
        ),
        "champion_points": (
            ExtremeSourceCoverageStatus.NOT_MODELED,
            "Champion Point contributions are not yet exhaustively enumerated for Extreme objectives.",
        ),
        "enchantments": (
            ExtremeSourceCoverageStatus.NOT_MODELED,
            "Glyph/enchantment contributions are not yet exhaustively enumerated for Extreme objectives.",
        ),
        "consumables": (
            ExtremeSourceCoverageStatus.PARTIAL,
            "External named-effect context can represent supplied consumable effects, but the engine does not exhaustively choose consumables.",
        ),
        "runtime_procs": (
            ExtremeSourceCoverageStatus.PARTIAL,
            "Runtime/context effects can be supplied, but proc eligibility and activation are not exhaustively generated for Extreme candidates.",
        ),
        "group_context": (
            ExtremeSourceCoverageStatus.CONTEXT_ONLY,
            "Named group effects are resolved when supplied; the Extreme engine does not assume or exhaustively construct a raid context.",
        ),
        "encounter_context": (
            ExtremeSourceCoverageStatus.CONTEXT_ONLY,
            "Encounter/runtime state can alter practical value but is supplied by the caller rather than exhaustively searched.",
        ),
    }

    @classmethod
    def coverage_for(cls, objective_key: str) -> ExtremeObjectiveCoverage:
        objective = objective_key.strip().casefold()
        if objective not in cls.REVIEWED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme objective: {objective_key!r}")

        sources = tuple(
            ExtremeSourceFamilyCoverage(
                source_family=source_family,
                status=cls._PHASE13_2_STATUS[source_family][0],
                note=cls._PHASE13_2_STATUS[source_family][1],
            )
            for source_family in cls.SOURCE_FAMILIES
        )
        return ExtremeObjectiveCoverage(
            objective_key=objective,
            sources=sources,
            source_universe_reviewed=False,
        )

    @classmethod
    def reviewed_matrix(cls) -> tuple[ExtremeObjectiveCoverage, ...]:
        return tuple(cls.coverage_for(objective) for objective in cls.REVIEWED_OBJECTIVES)
