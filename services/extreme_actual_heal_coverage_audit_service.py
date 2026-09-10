from __future__ import annotations

from minmax.mechanic_coverage import (
    MechanicCoverageItem,
    MechanicCoverageSummary,
    VALID_COVERAGE_STATUSES,
    summarize_mechanic_coverage,
    validate_mechanic_coverage,
)
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationService,
)
from services.extreme_healing_class_passive_coverage_inventory import (
    ExtremeHealingClassPassiveCoverageInventory,
    ExtremeHealingClassPassiveCoverageSummary,
)
from services.extreme_healing_event_recipient_scope_service import (
    ExtremeHealingEventRecipientScopeService,
)


CoverageStatus = str
ExtremeActualHealCoverageItem = MechanicCoverageItem
ExtremeActualHealCoverageSummary = MechanicCoverageSummary


class ExtremeActualHealCoverageAuditService:
    """Read-only H1 coverage audit for the MOST Actual Heal objective.

    The audit distinguishes fully standing mechanics from mechanics that are
    supported only when explicit runtime/scenario evidence is supplied.
    ``conditional`` therefore means supported-but-scenario-bound and counts as
    covered. ``unresolved`` is the fail-closed state that blocks an exhaustive
    completeness claim. Objective-irrelevant mechanics stay visible but remain
    outside the denominator.

    This service uses the shared BFF mechanic-coverage contract so Extreme,
    Comp Maker, Team Optimization, Rotation, provider/coverage, and later
    consumers do not invent conflicting meanings for coverage status.

    Class-passive coverage is derived from a canonical family inventory that
    must exactly match ``CLASS_SKILL_LINES``. This keeps unreviewed class
    families measurable instead of allowing them to disappear inside prose.
    Dragon Blood is counted as implemented only because the reviewed recipient
    resolver can prove the self component from the exact two-component 3:2
    coefficient relationship and the healing-event evaluator consumes that
    selection. Malformed or missing coefficient evidence still blocks the
    individual event rather than being treated as covered by assumption.
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

    _VALID_STATUSES = VALID_COVERAGE_STATUSES

    @staticmethod
    def _scope_contains(values: tuple[str, ...], token: str) -> bool:
        needle = token.casefold()
        return any(needle in str(value).casefold() for value in values)

    def class_passive_summary(self) -> ExtremeHealingClassPassiveCoverageSummary:
        return ExtremeHealingClassPassiveCoverageInventory().summary()

    def items(self) -> tuple[ExtremeActualHealCoverageItem, ...]:
        search_scope = tuple(ExtremeActualHealOptimizationService.SEARCH_SCOPE)
        omitted_scope = tuple(ExtremeActualHealOptimizationService.OMITTED_SCOPE)
        class_passives = self.class_passive_summary()

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
                "implemented" if class_passives.complete else "unresolved",
                "ExtremeHealingClassPassiveCoverageInventory",
                (
                    "Canonical class-passive review denominator: "
                    f"reviewed {class_passives.reviewed_families}/{class_passives.total_families}; "
                    f"healing-relevant {class_passives.healing_relevant_families}; "
                    f"implemented {class_passives.implemented}; "
                    f"explicitly unsupported {class_passives.explicitly_unsupported}; "
                    f"healing-relevant unreviewed {class_passives.healing_relevant_unreviewed}; "
                    f"families awaiting relevance review {class_passives.unreviewed_families}."
                ),
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
                "ExtremeRuntimeSnapshotCombatStateService + ExtremeConditionalActualHealOptimizationService",
                "Explicit runtime snapshots prove modeled skill, gear, and potion windows. Runtime state is supported when supplied explicitly; the standing optimizer intentionally does not invent those conditions.",
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
                "Target-health-dependent healing is supported when the caller supplies an explicit target health fraction; no emergency-health assumption is invented.",
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
                "conditional",
                "ExternalGroupBuffProvenanceResolver + ExtremeRuntimeSnapshot + ExtremeRuntimeSnapshotCombatStateService",
                "External group buffs are supported only through explicit provenance: canonical buff identity, proven source and recipient group membership, legal target semantics, source evidence, and an active snapshot window. The standing optimizer still omits group-only buffs rather than inventing raid support.",
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
        return summarize_mechanic_coverage(
            self.items(),
            required_categories=self.REQUIRED_CATEGORIES,
        )

    def _validate(self, rows: tuple[ExtremeActualHealCoverageItem, ...]) -> None:
        try:
            validate_mechanic_coverage(
                rows,
                required_categories=self.REQUIRED_CATEGORIES,
            )
        except ValueError as exc:
            raise ValueError(f"Extreme Actual Heal coverage audit: {exc}") from exc
