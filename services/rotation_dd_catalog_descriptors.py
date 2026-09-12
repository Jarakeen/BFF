from __future__ import annotations

"""Whole-plan DD Rotation Builder service catalog metadata."""

from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


ROTATION_DD_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="rotation.dd.saved_build_damage_done",
        domain="rotation",
        purpose=(
            "Resolve reviewed unconditional saved-build DD Damage Done Champion Point "
            "categories from canonical Champion Point records without promoting conditional stars."
        ),
        implementation_path="services.rotation_saved_build_dd_damage_done_service",
        inputs=("PlayerBuild", "ChampionPointRecord"),
        outputs=("RotationSavedBuildDDDamageDoneResolution", "DamageDoneModifiers"),
        responsibilities=("rotation_dd_saved_build_damage_done",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Currently owns reviewed unconditional Master-at-Arms, Biting Aura, and "
            "Thaumaturge event-category modifiers. Stage thresholds and per-stage values come "
            "from canonical Champion Point records."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.dd.saved_build_conditional_damage_done",
        domain="rotation",
        purpose=(
            "Resolve reviewed saved-build DD Damage Done magnitudes whose application depends "
            "on exact target runtime state, without inventing that state."
        ),
        implementation_path=(
            "services.rotation_saved_build_dd_conditional_damage_done_service"
        ),
        inputs=("PlayerBuild", "ChampionPointRecord", "CombatState"),
        outputs=("RotationSavedBuildDDConditionalDamageDoneResolution",),
        responsibilities=("rotation_dd_saved_build_conditional_damage_done",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Currently resolves Exploiter magnitude and explicit Off Balance applicability. "
            "Direct skills and Ultimates, snapshot and dynamic DoT ticks, light attacks, and "
            "heavy-attack completion all consume exact target CombatState and fail closed when "
            "that state is unavailable."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.dd.plan_potion_combat_state",
        domain="rotation",
        purpose=(
            "Project source-backed potion buffs into attacker CombatState only after an "
            "explicit POTION action in the exact final plan."
        ),
        implementation_path="services.rotation_plan_potion_combat_state_service",
        inputs=("PlayerBuild", "CharacterProgression", "RotationPlan", "CombatState"),
        outputs=("RotationPlanPotionCombatStateResult",),
        responsibilities=("rotation_plan_potion_combat_state",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Potion selection proves availability only. Buff activation requires an explicit "
            "scheduled potion action; durations come from source-backed potion evidence and "
            "recorded Medicinal Use rank. Scheduling and cooldown legality remain separate."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.dd.output_context_relevance",
        domain="rotation",
        purpose=(
            "Classify broad static build-context diagnostics by whether they can invalidate "
            "modeled DD damage output, preserving unknown offensive diagnostics fail-closed."
        ),
        implementation_path="services.rotation_dd_output_context_relevance_service",
        inputs=("BuildCalculationContextUnresolved",),
        outputs=("RotationDDOutputContextRelevance",),
        responsibilities=("rotation_dd_output_context_relevance",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Only diagnostics already proven irrelevant to current DD damage math are ambient. "
            "Bloodthirsty, potion uptime outside explicit scheduled activations, Charged/status "
            "chance, and unknown mechanics remain blocking until their canonical runtime math exists."
        ),
    ),
    ServiceDescriptor(
        service_id="rotation.dd.whole_plan_damage_coverage_audit",
        domain="rotation",
        purpose=(
            "Count resolved and unresolved scheduled DD damage consequences for one exact "
            "candidate and group repeated canonical blockers without reinterpreting them."
        ),
        implementation_path=(
            "services.rotation_dd_whole_plan_damage_coverage_audit_service"
        ),
        inputs=(
            "GeneratedRotationCandidate",
            "RotationActionDamageEvidenceProvider",
        ),
        outputs=("RotationDDWholePlanDamageCoverageAudit",),
        responsibilities=("rotation_dd_whole_plan_damage_coverage_audit",),
        roles=("DD", "DPS"),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
        notes=(
            "Audit only. The existing action-damage provider remains authoritative for "
            "damage consequences. Missing mechanics stay unresolved; blocker grouping "
            "preserves every exact time/sequence occurrence for countable closeout work."
        ),
    ),
)


__all__ = ["ROTATION_DD_SERVICE_DESCRIPTORS"]