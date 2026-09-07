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

    Phase 13.2 now inventories the complete canonical player-skill universe.
    That is deliberately different from claiming every passive/active mechanic
    is numerically solved.  Each skill family remains ``PARTIAL`` until every
    relevant static and contextual mechanic in that family is losslessly mapped
    or explicitly proven irrelevant to the objective.
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
        "active_skills",
        "class_skill_passives",
        "weapon_skill_passives",
        "armor_skill_passives",
        "guild_skill_passives",
        "alliance_war_passives",
        "world_skill_passives",
        "racial_skill_passives",
        "craft_utility_passives",
        "armor_base_values_traits",
        "gear_sets",
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
        "active_skills": (
            ExtremeSourceCoverageStatus.PARTIAL,
            "All canonical player active-skill families are now in the route-aware candidate universe, but reviewed standing/activated effect projection is not yet exhaustive for every legal active skill.",
        ),
        "class_skill_passives": (
            ExtremeSourceCoverageStatus.PARTIAL,
            "All canonical class passives are inventoried; reviewed formulas exist for a subset while remaining conditional/unresolved mechanics stay explicit.",
        ),
        "weapon_skill_passives": (
            ExtremeSourceCoverageStatus.PARTIAL,
            "All canonical weapon passives are inventoried, but equipment/bar/attack-type conditions are not yet exhaustively projected for every passive.",
        ),
        "armor_skill_passives": (
            ExtremeSourceCoverageStatus.PARTIAL,
            "All canonical armor passives are inventoried and reviewed Light/Medium/Heavy piece-count formulas are partially projected; the full passive set is not yet exhaustive.",
        ),
        "guild_skill_passives": (
            ExtremeSourceCoverageStatus.PARTIAL,
            "All canonical guild passives are inventoried; reviewed formulas exist for some standing passives while remaining guild mechanics require mapping/context.",
        ),
        "alliance_war_passives": (
            ExtremeSourceCoverageStatus.PARTIAL,
            "All canonical Assault/Support passives are inventoried; reviewed standing formulas exist for some effects but the family is not yet exhaustive.",
        ),
        "world_skill_passives": (
            ExtremeSourceCoverageStatus.PARTIAL,
            "All canonical Soul Magic/Vampire/Werewolf and other player world passives are inventoried; transformation/runtime conditions remain explicit where needed.",
        ),
        "racial_skill_passives": (
            ExtremeSourceCoverageStatus.PARTIAL,
            "All canonical racial passive skill records are inventoried; simple static effects may be projected while conditional/non-structured racial mechanics remain unresolved/contextual.",
        ),
        "craft_utility_passives": (
            ExtremeSourceCoverageStatus.PARTIAL,
            "Crafting/utility player passives are retained in the canonical skill universe and classified as known noncombat unless a reviewed combat-relevant mechanic proves otherwise; exhaustive relevance review is not complete.",
        ),
        "armor_base_values_traits": (
            ExtremeSourceCoverageStatus.PARTIAL,
            "Deterministic armor base values and several modeled traits exist in the shared build stack, but Extreme has not yet exhaustively searched weight/quality/slot/trait combinations for every objective.",
        ),
        "gear_sets": (
            ExtremeSourceCoverageStatus.NOT_MODELED,
            "Extreme candidate generation does not yet exhaustively enumerate gear-set contributions.",
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
