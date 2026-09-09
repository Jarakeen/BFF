from __future__ import annotations

from dataclasses import dataclass

from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationService,
)
from services.extreme_healing_event_recipient_scope_service import (
    ExtremeHealingEventRecipientScopeService,
)


CoverageStatus = str


@dataclass(frozen=True)
class ExtremeActualHealCoverageItem:
    mechanic_id: str
    category: str
    status: CoverageStatus
    evidence: str
    detail: str

    @property
    def counts_toward_denominator(self) -> bool:
        return self.status != "irrelevant"

    @property
    def is_fully_covered(self) -> bool:
        return self.status == "implemented"


@dataclass(frozen=True)
class ExtremeActualHealCoverageSummary:
    implemented: int
    conditional: int
    unresolved: int
    irrelevant: int
    denominator: int
    covered: int
    blocker_ids: tuple[str, ...]

    @property
    def coverage_fraction(self) -> float:
        if self.denominator == 0:
            return 1.0
        return self.covered / self.denominator


class ExtremeActualHealCoverageAuditService:
    """Read-only H1 coverage audit for the MOST Actual Heal objective.

    The audit deliberately distinguishes mechanics that are fully modeled from
    mechanics that only become legal under explicit runtime/evidence state.
    Conditional mechanics remain visible in the denominator but do not count as
    fully covered. Unsupported recipient/group semantics are blockers rather than
    optimistic assumptions. Objective-irrelevant mechanics remain visible for
    auditability but are excluded from the denominator.

    The broad implemented/omitted boundaries are anchored to the optimizer's
    existing ``SEARCH_SCOPE`` and ``OMITTED_SCOPE`` contracts. Dragon Blood is
    counted as implemented only because the reviewed recipient resolver can prove
    the self component from the exact two-component 3:2 coefficient relationship
    and the healing-event evaluator consumes that selection. Malformed or missing
    coefficient evidence still blocks the individual event rather than being
    treated as covered by assumption.
    """

    REQUIRED_CATEGORIES = (
        "class_passives",
        "gear_bonuses",
        "champion_points",
        "conditional_stat_buffs",
        "heal_components",
        "coefficient_interpretation",
        "target_state_scaling",
        "self_vs_ally_components",
        "external_group_buffs",
        "race_bonuses",
        "shadow",
        "artifact_buffs",
    )

    _VALID_STATUSES = frozenset({"implemented", "conditional", "unresolved", "irrelevant"})

    @staticmethod
    def _scope_contains(values: tuple[str, ...], token: str) -> bool:
        needle = token.casefold()
        return any(needle in str(value).casefold() for value in values)

    def items(self) -> tuple[ExtremeActualHealCoverageItem, ...]:
        search_scope = tuple(ExtremeActualHealOptimizationService.SEARCH_SCOPE)
        omitted_scope = tuple(ExtremeActualHealOptimizationService.OMITTED_SCOPE)

        gear_status = (
            "implemented"
            if self._scope_contains(search_scope, "five-piece")
            and self._scope_contains(search_scope, "monster")
            and self._scope_contains(search_scope, "mythic")
            else "unresolved"
        )
        race_status = (
            "implemented" if self._scope_contains(search_scope, "race") else "unresolved"
        )
        shadow_status = (
            "implemented" if self._scope_contains(search_scope, "Mundus") else "unresolved"
        )
        coefficient_status = (
            "implemented"
            if self._scope_contains(search_scope, "canonical healing coefficient scaling")
            else "unresolved"
        )
        cp_status = (
            "implemented"
            if self._scope_contains(search_scope, "verified healing CP")
            else "unresolved"
        )
        runtime_omitted = self._scope_contains(omitted_scope, "runtime conditional stacks/procs")
        group_omitted = self._scope_contains(omitted_scope, "group-only buffs")
        unreviewed_passives_omitted = self._scope_contains(
            omitted_scope, "unreviewed skill-bar passive/proc families"
        )
        dragon_blood_guarded = {
            "blood of the elder dragon",
            "coagulating blood",
        }.issubset(
            name.casefold()
            for name in ExtremeHealingEventRecipientScopeService.MULTI_RECIPIENT_DISTINCT_SCALING
        )
        if not dragon_blood_guarded:
            raise ValueError(
                "Extreme Actual Heal coverage audit expected the Dragon Blood recipient guard to remain active"
            )

        rows = (
            ExtremeActualHealCoverageItem(
                "reviewed_class_passive_families",
                "class_passives",
                "conditional" if unreviewed_passives_omitted else "implemented",
                "ExtremeHealingEventService class-family resolvers + optimizer OMITTED_SCOPE",
                "Reviewed class passive families are modeled, but the optimizer still explicitly omits unreviewed skill-bar passive/proc families.",
            ),
            ExtremeActualHealCoverageItem(
                "reviewed_gear_packages_and_bonuses",
                "gear_bonuses",
                gear_status,
                "ExtremeActualHealOptimizationService.SEARCH_SCOPE",
                "Reviewed five-piece, monster, mythic, arena-weapon, trait, enchant, and weapon-package candidates rebuild through canonical whole-build math.",
            ),
            ExtremeActualHealCoverageItem(
                "verified_healing_champion_points",
                "champion_points",
                cp_status,
                "ExtremeActualHealOptimizationService.SEARCH_SCOPE",
                "Verified healing CP is routed through canonical actual-effect and Critical Healing math.",
            ),
            ExtremeActualHealCoverageItem(
                "runtime_stat_buff_windows",
                "conditional_stat_buffs",
                "conditional" if runtime_omitted else "implemented",
                "ExtremeRuntimeSnapshotCombatStateService + optimizer OMITTED_SCOPE",
                "Explicit runtime snapshots can prove modeled skill, gear, and potion windows; unproved runtime stacks/procs remain outside the standing optimizer.",
            ),
            ExtremeActualHealCoverageItem(
                "heal_component_classification_and_crit_eligibility",
                "heal_components",
                "implemented",
                "ExtremeHealingEventService",
                "HEAL components, actual-effect values, and per-component critical eligibility are evaluated explicitly; unknown eligibility blocks the result.",
            ),
            ExtremeActualHealCoverageItem(
                "canonical_heal_coefficient_scaling",
                "coefficient_interpretation",
                coefficient_status,
                "ExtremeActualHealOptimizationService.SEARCH_SCOPE + SavedBuildSkillTooltipService",
                "MOST Actual Heal reuses canonical coefficient scaling rather than rescoring tooltip proxies.",
            ),
            ExtremeActualHealCoverageItem(
                "explicit_target_health_conditionals",
                "target_state_scaling",
                "conditional",
                "ExtremeConditionalActualHealOptimizationService",
                "Target-health-dependent healing is legal only when the caller supplies an explicit target health fraction; no emergency-health assumption is invented.",
            ),
            ExtremeActualHealCoverageItem(
                "dragon_blood_component_recipient_identity",
                "self_vs_ally_components",
                "implemented",
                "ExtremeHealingEventRecipientScopeService + ExtremeHealingEventService",
                "Blood of the Elder Dragon uses the reviewed exact 3:2 coefficient relationship to identify and select the original/self HEAL component before one-recipient event scoring. Missing, malformed, or ambiguous coefficient evidence remains unresolved and cannot combine self plus ally healing.",
            ),
            ExtremeActualHealCoverageItem(
                "external_group_buff_provenance",
                "external_group_buffs",
                "unresolved" if group_omitted else "conditional",
                "ExtremeActualHealOptimizationService.OMITTED_SCOPE",
                "Group-only buffs are still explicitly omitted; H2 must prove source, recipient, legality, and snapshot timing before they can affect MOST Actual Heal.",
            ),
            ExtremeActualHealCoverageItem(
                "race_stat_and_healing_bonuses",
                "race_bonuses",
                race_status,
                "ExtremeActualHealOptimizationService.SEARCH_SCOPE + RaceRepository",
                "Race is rebuilt as a whole-build candidate and therefore carries canonical racial stat/healing effects into event scoring.",
            ),
            ExtremeActualHealCoverageItem(
                "shadow_critical_healing",
                "shadow",
                shadow_status,
                "Mundus search scope + canonical Critical Healing stat",
                "The Shadow is evaluated through the Mundus path and contributes to canonical Critical Healing before the reviewed cap is applied.",
            ),
            ExtremeActualHealCoverageItem(
                "artifact_max_magicka_bonuses",
                "artifact_buffs",
                "implemented",
                "canonical build stat pipeline",
                "Reviewed artifact Max Magicka bonuses are part of the canonical build state consumed by the healing coefficient pipeline.",
            ),
            ExtremeActualHealCoverageItem(
                "critical_chance_probability",
                "objective_semantics",
                "irrelevant",
                "ExtremeHealingEventService",
                "MOST Actual Heal asks how large the event can be when it crits; critical chance belongs to an expected-value objective, not this maximum-event objective.",
            ),
            ExtremeActualHealCoverageItem(
                "hps_cadence_and_average_healing",
                "objective_semantics",
                "irrelevant",
                "MOST Actual Heal objective contract",
                "HPS, cadence, and average healing do not change the size of one largest applied healing event.",
            ),
        )
        self._validate(rows)
        return rows

    def summary(self) -> ExtremeActualHealCoverageSummary:
        rows = self.items()
        counts = {
            status: sum(1 for row in rows if row.status == status)
            for status in self._VALID_STATUSES
        }
        denominator = sum(1 for row in rows if row.counts_toward_denominator)
        covered = sum(1 for row in rows if row.is_fully_covered)
        blockers = tuple(
            row.mechanic_id
            for row in rows
            if row.status in {"conditional", "unresolved"}
        )
        return ExtremeActualHealCoverageSummary(
            implemented=counts["implemented"],
            conditional=counts["conditional"],
            unresolved=counts["unresolved"],
            irrelevant=counts["irrelevant"],
            denominator=denominator,
            covered=covered,
            blocker_ids=blockers,
        )

    def _validate(self, rows: tuple[ExtremeActualHealCoverageItem, ...]) -> None:
        ids = tuple(row.mechanic_id for row in rows)
        if len(ids) != len(set(ids)):
            raise ValueError("Extreme Actual Heal coverage audit contains duplicate mechanic ids")
        invalid = tuple(row.status for row in rows if row.status not in self._VALID_STATUSES)
        if invalid:
            raise ValueError(f"Extreme Actual Heal coverage audit has invalid status: {invalid[0]}")
        categories = {row.category for row in rows}
        missing = tuple(category for category in self.REQUIRED_CATEGORIES if category not in categories)
        if missing:
            raise ValueError(
                "Extreme Actual Heal coverage audit is missing required categories: "
                + ", ".join(missing)
            )
