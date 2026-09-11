from __future__ import annotations

"""Reviewed high-impact contextual passives for Extreme max-resource records.

This is a proof-boundary ledger, not a second mechanics engine. It records which
known max-resource passives are already applied by shared canonical resolvers and
which still require a finite active-bar axis, explicit runtime state, or mechanic
implementation before the global passive denominator can close.

The catalog is intentionally reviewed and finite. It does not claim that these
rows are the complete canonical passive universe; ``ExtremeResourcePassiveCoverageAuditService``
continues to own that denominator.
"""

from dataclasses import dataclass
from enum import Enum


_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


class ExtremeResourceContextualPassiveStatus(str, Enum):
    CANONICALLY_APPLIED = "canonically_applied"
    ACTIVE_BAR_SEARCH_REQUIRED = "active_bar_search_required"
    RUNTIME_STATE_REQUIRED = "runtime_state_required"
    MECHANIC_IMPLEMENTATION_REQUIRED = "mechanic_implementation_required"


@dataclass(frozen=True)
class ExtremeResourceContextualPassiveReview:
    objective_key: str
    passive_name: str
    skill_line: str
    status: ExtremeResourceContextualPassiveStatus
    source: str
    condition: str = ""

    @property
    def identity(self) -> tuple[str, str, str]:
        return (self.objective_key, self.skill_line, self.passive_name)


class ExtremeResourceContextualPassiveReviewService:
    """Return reviewed max-resource passive boundaries for one objective."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    _ROWS = (
        # Standing canonical passive math already participates in the ordinary
        # context calculation when the required route/progression evidence is supplied.
        ExtremeResourceContextualPassiveReview(
            objective_key="max_health",
            passive_name="Juggernaut",
            skill_line="Heavy Armor",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="ArmorPassiveInputResolver",
            condition="Max-rank Juggernaut is supplied by the Extreme max-Health armor progression and scales through the shared Heavy Armor piece count.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_health",
            passive_name="Last Gasp",
            skill_line="Bone Tyrant",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="NecromancerPassiveInputResolver",
            condition="Max-rank Last Gasp is applied when the selected class route owns Bone Tyrant.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_magicka",
            passive_name="Expert Summoner",
            skill_line="Daedric Summoning",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="SorcererPassiveInputResolver",
            condition="Standing U50 Max Magicka branch is applied when the selected route owns Daedric Summoning.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_stamina",
            passive_name="Expert Summoner",
            skill_line="Daedric Summoning",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="SorcererPassiveInputResolver",
            condition="Standing U50 Max Stamina branch is applied when the selected route owns Daedric Summoning.",
        ),

        # Shared math exists, but the current max-resource record does not yet
        # search the active-bar compositions needed to realize these maxima.
        ExtremeResourceContextualPassiveReview(
            objective_key="max_health",
            passive_name="Dark Vigor",
            skill_line="Shadow",
            status=ExtremeResourceContextualPassiveStatus.ACTIVE_BAR_SEARCH_REQUIRED,
            source="NightbladePassiveInputResolver",
            condition="Max Health scales with the number of Shadow abilities slotted on the active bar.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_magicka",
            passive_name="Magicka Flood",
            skill_line="Siphoning",
            status=ExtremeResourceContextualPassiveStatus.ACTIVE_BAR_SEARCH_REQUIRED,
            source="NightbladePassiveInputResolver",
            condition="Requires at least one Siphoning ability on the active bar.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_stamina",
            passive_name="Magicka Flood",
            skill_line="Siphoning",
            status=ExtremeResourceContextualPassiveStatus.ACTIVE_BAR_SEARCH_REQUIRED,
            source="NightbladePassiveInputResolver",
            condition="Requires at least one Siphoning ability on the active bar.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_magicka",
            passive_name="Magicka Controller",
            skill_line="Mages Guild",
            status=ExtremeResourceContextualPassiveStatus.ACTIVE_BAR_SEARCH_REQUIRED,
            source="GuildPassiveInputResolver",
            condition="Max Magicka scales with the number of Mages Guild abilities slotted on the active bar.",
        ),

        # Reviewed mechanics exist, but the global record does not yet search
        # the explicit runtime states required to activate their maximum branch.
        ExtremeResourceContextualPassiveReview(
            objective_key="max_health",
            passive_name="Expert Summoner",
            skill_line="Daedric Summoning",
            status=ExtremeResourceContextualPassiveStatus.RUNTIME_STATE_REQUIRED,
            source="ExtremeSorcererExpertSummonerPetContextService",
            condition="Additional U50 Max Health branch requires an explicitly active permanent pet.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_health",
            passive_name="Nothing Wasted",
            skill_line="Class Mastery",
            status=ExtremeResourceContextualPassiveStatus.RUNTIME_STATE_REQUIRED,
            source="ClassMasteryExtremeEffectService",
            condition="Maximum is the reviewed 10-stack state; stacks require Corpse Consumption activity.",
        ),
    )

    @classmethod
    def build(
        cls,
        objective_key: str,
    ) -> tuple[ExtremeResourceContextualPassiveReview, ...]:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme contextual resource objective: {objective_key!r}")
        rows = tuple(row for row in cls._ROWS if row.objective_key == key)
        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    row.status.value,
                    row.passive_name.casefold(),
                    row.skill_line.casefold(),
                ),
            )
        )

    @classmethod
    def status_rows(
        cls,
        objective_key: str,
        status: ExtremeResourceContextualPassiveStatus,
    ) -> tuple[ExtremeResourceContextualPassiveReview, ...]:
        return tuple(row for row in cls.build(objective_key) if row.status is status)
