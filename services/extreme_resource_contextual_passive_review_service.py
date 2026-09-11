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
            objective_key="max_health",
            passive_name="Dark Vigor",
            skill_line="Shadow",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="NightbladePassiveInputResolver",
            condition="The reviewed Extreme active-bar reducer searches the legal six-slot bar and maximizes distinct Shadow abilities; shared Nightblade passive math applies the resulting Max Health bonus.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_health",
            passive_name="Maturation",
            skill_line="Green Balance",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="ExtremeResourceMaxHealthRuntimeStateService + canonical Minor Toughness CombatState",
            condition="The reviewed Max Health runtime reducer selects Maturation when Green Balance is legal, assumes a qualifying self-heal window, and routes canonical Minor Toughness through CombatState; the witness can stack with Expert Summoner on legal subclass routes.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_health",
            passive_name="Expert Summoner",
            skill_line="Daedric Summoning",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="ExtremeSorcererExpertSummonerPetContextService",
            condition="The reviewed Max Health runtime reducer activates the permanent-pet witness only on legal Daedric Summoning routes, and the canonical context rebuilder inserts the additional U50 5% Max Health branch before resource rounding.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_health",
            passive_name="Nothing Wasted",
            skill_line="Class Mastery",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="ClassMasteryExtremeEffectService",
            condition="The reviewed Max Health runtime reducer selects canonical Nothing Wasted Class Mastery only on a legal pure Necromancer route and applies the reviewed 10-stack Corpse Consumption maximum as +20% Max Health before resource rounding.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_health",
            passive_name="Undaunted Mettle",
            skill_line="Undaunted",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="ExtremeHypotheticalUndauntedProgressionService",
            condition="Extreme canonical resource scoring grants reviewed max-rank Undaunted Mettle and applies its shared distinct-armor-weight max-resource bonus.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_health",
            passive_name="Emperor",
            skill_line="Emperor",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory + EmperorPassiveInputResolver",
            condition="The reviewed Extreme max-resource continuation uses the legal active-Emperor six-Home-Keep ceiling; CombatState carries campaign legality and the shared Emperor resolver applies the canonical U50 75% maximum-resource bonus.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_magicka",
            passive_name="Blood Magic",
            skill_line="Dark Magic",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="ExtremeResourceActiveBarStateService + ExtremeSorcererBloodMagicService + ExtremeResourceBloodMagicRuntimeContextService",
            condition="The reviewed bar reducer preserves a canonical positive-cost Dark Magic trigger alongside competing Siphoning/Mages Guild witnesses; the pre-window canonical context chooses the higher Max Magicka/Stamina pool and the matching named Blood Magic resource buff is then rebuilt through CombatState.",
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
            objective_key="max_magicka",
            passive_name="Magicka Flood",
            skill_line="Siphoning",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="NightbladePassiveInputResolver",
            condition="The reviewed Extreme active-bar reducer searches a legal Siphoning trigger jointly with Mages Guild slot competition; shared Nightblade passive math applies the 6% Max Magicka trigger.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_magicka",
            passive_name="Magicka Controller",
            skill_line="Mages Guild",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="GuildPassiveInputResolver",
            condition="The reviewed Extreme active-bar reducer maximizes legal Mages Guild slots jointly with Magicka Flood and supplies canonical max-rank Magicka Controller progression.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_magicka",
            passive_name="Undaunted Mettle",
            skill_line="Undaunted",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="ExtremeHypotheticalUndauntedProgressionService",
            condition="Extreme canonical resource scoring grants reviewed max-rank Undaunted Mettle and applies its shared distinct-armor-weight max-resource bonus.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_magicka",
            passive_name="Emperor",
            skill_line="Emperor",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory + EmperorPassiveInputResolver",
            condition="The reviewed Extreme max-resource continuation uses the legal active-Emperor six-Home-Keep ceiling; CombatState carries campaign legality and the shared Emperor resolver applies the canonical U50 75% maximum-resource bonus.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_stamina",
            passive_name="Blood Magic",
            skill_line="Dark Magic",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="ExtremeResourceActiveBarStateService + ExtremeSorcererBloodMagicService + ExtremeResourceBloodMagicRuntimeContextService",
            condition="The reviewed bar reducer preserves a canonical positive-cost Dark Magic trigger alongside any Siphoning witness; the pre-window canonical context chooses the higher Max Magicka/Stamina pool and the matching named Blood Magic resource buff is then rebuilt through CombatState.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_stamina",
            passive_name="Expert Summoner",
            skill_line="Daedric Summoning",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="SorcererPassiveInputResolver",
            condition="Standing U50 Max Stamina branch is applied when the selected route owns Daedric Summoning.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_stamina",
            passive_name="Magicka Flood",
            skill_line="Siphoning",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="NightbladePassiveInputResolver",
            condition="The reviewed Extreme active-bar reducer searches one legal Siphoning trigger because additional Siphoning slots cannot increase Magicka Flood; shared Nightblade passive math applies the 6% Max Stamina bonus.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_stamina",
            passive_name="Undaunted Mettle",
            skill_line="Undaunted",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="ExtremeHypotheticalUndauntedProgressionService",
            condition="Extreme canonical resource scoring grants reviewed max-rank Undaunted Mettle and applies its shared distinct-armor-weight max-resource bonus.",
        ),
        ExtremeResourceContextualPassiveReview(
            objective_key="max_stamina",
            passive_name="Emperor",
            skill_line="Emperor",
            status=ExtremeResourceContextualPassiveStatus.CANONICALLY_APPLIED,
            source="ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory + EmperorPassiveInputResolver",
            condition="The reviewed Extreme max-resource continuation uses the legal active-Emperor six-Home-Keep ceiling; CombatState carries campaign legality and the shared Emperor resolver applies the canonical U50 75% maximum-resource bonus.",
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
