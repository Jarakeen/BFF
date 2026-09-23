from __future__ import annotations

from services.canonical_knowledge_gap import CanonicalKnowledgeDomain
from services.canonical_mechanics_coverage_audit import (
    CanonicalMechanicsCoverageEvidence,
    CanonicalMechanicsCoverageStatus,
)


ALL_THREE = ("comp_maker", "rotation_maker", "optimizer")
ROTATION_OPTIMIZER = ("rotation_maker", "optimizer")


def shared_canonical_mechanics_inventory() -> tuple[CanonicalMechanicsCoverageEvidence, ...]:
    """Conservative evidence-backed snapshot of current shared mechanics coverage.

    Rows describe what current canonical services can prove. They intentionally do
    not claim complete ESO coverage merely because a saved identity can be stored.
    Runtime/conditional semantics remain partial until their trigger, timing,
    stacking, targeting, resource, and suppression rules are explicitly modeled.
    """

    return (
        CanonicalMechanicsCoverageEvidence(
            domain=CanonicalKnowledgeDomain.SKILL_MECHANIC,
            key="saved_build:canonical_structure",
            status=CanonicalMechanicsCoverageStatus.CALCULATION_READY,
            capability=(
                "Saved build class/role/race, exact six-slot bars, skill eligibility, "
                "weapon type, set identity, mythic identity, weapon enchantment identity, "
                "and Champion Point allocations can be adapted into CharacterBuild with "
                "unresolved identities failing closed."
            ),
            evidence_source="minmax/character_build/saved_build_adapter.py",
            consumers=ALL_THREE,
        ),
        CanonicalMechanicsCoverageEvidence(
            domain=CanonicalKnowledgeDomain.EFFECT_DURATION,
            key="effect_duration:build_modifiers",
            status=CanonicalMechanicsCoverageStatus.PARTIAL,
            capability=(
                "Build-effective duration resolution exists and currently supports the "
                "verified status_effect_duration_increase semantic used by Serpent's Disdain."
            ),
            evidence_source="minmax/character_build/effect_duration_resolver.py",
            consumers=ALL_THREE,
            missing_evidence=(
                "Catalog and verify every other class passive, armor/set, mythic, Champion "
                "Point, potion, or other mechanic that changes effect duration, including "
                "applicability, additive/multiplicative behavior, stacking order, caps, "
                "bar/slot requirements, and refresh interaction."
            ),
        ),
        CanonicalMechanicsCoverageEvidence(
            domain=CanonicalKnowledgeDomain.RESOURCE_RECOVERY,
            key="heavy_attack:restoration",
            status=CanonicalMechanicsCoverageStatus.PARTIAL,
            capability=(
                "Scheduled heavy attacks can be mapped to active weapon/bar and converted "
                "to restoration events when completion, fully-charged state, successful-hit state, "
                "verified base restore, and modifiers are explicitly supplied. ESO Logs damage "
                "observations can promote reviewed completions to landed evidence one-to-one."
            ),
            evidence_source="services/rotation_heavy_attack_restoration_evidence_service.py",
            consumers=ROTATION_OPTIMIZER,
            missing_evidence=(
                "Update 35 now supplies authoritative base restoration for standard weapon families. "
                "Complete the exact passive/set/CP/modifier catalog that alters heavy restore, including "
                "current ownership/values for historical Tenacity, Ulfnor's Favor, Off Balance, "
                "Rampaging Slash, Arch-Mage, and block-reduction axes; verify Werewolf separately, "
                "complete blocked/dodged/missed outcome semantics beyond the current positive landed "
                "observation, and preserve channel/completion timing "
                "evidence rather than inferring it."
            ),
        ),
        CanonicalMechanicsCoverageEvidence(
            domain=CanonicalKnowledgeDomain.ASSIGNMENT_POLICY,
            key="assignment:rotation_fulfillment_catalog",
            status=CanonicalMechanicsCoverageStatus.PARTIAL,
            capability=(
                "Provider ownership can be translated into exact runtime effect obligations "
                "or explicit non-effect dispositions, with missing assignment semantics "
                "surfaced as shared knowledge gaps."
            ),
            evidence_source=(
                "services/rotation_assignment_policy_resolver.py; "
                "services/rotation_assignment_canonical_evidence_service.py"
            ),
            consumers=ALL_THREE,
            missing_evidence=(
                "Populate a provenance-backed production policy catalog for encounter/team "
                "assignments: exact effect/source/bar/uptime when effect-based, or the exact "
                "non-effect mechanic model responsible when not effect-based."
            ),
        ),
        CanonicalMechanicsCoverageEvidence(
            domain=CanonicalKnowledgeDomain.PASSIVE,
            key="passives:runtime_semantics",
            status=CanonicalMechanicsCoverageStatus.PARTIAL,
            capability=(
                "PassiveGrant evidence participates in build effect availability and duration "
                "evaluation when supplied explicitly. Rotation static evaluation reuses the "
                "rank-aware Phase5BuildCalculationContextFactory, which applies racial passives and "
                "reviewed Warden, "
                "Dragonknight, Necromancer, Nightblade, Sorcerer, Templar, armor, One Hand and "
                "Shield, Undaunted, guild, and Alliance Support passive resolvers."
            ),
            evidence_source=(
                "minmax/character_build/passive_grant.py; "
                "services/rotation_build_effect_duration_service.py; "
                "minmax/context_factory.py; minmax/phase5_context_factory.py; "
                "services/rotation_static_build_context_service.py; "
                "minmax/racial_passive_stat_repository.py; "
                "services/extreme_resource_racial_passive_ownership_service.py; "
                "services/extreme_passive_projection_service.py"
            ),
            consumers=ALL_THREE,
            missing_evidence=(
                "Expand the verified rotation-runtime passive catalog beyond the resolver families "
                "already owned by the Phase 5 context path. Racial passive ownership/stat parsing "
                "now reaches rotation static contexts; missing weapon/world/vampire/werewolf and "
                "other passives still require runtime ownership. ExtremePassiveProjectionService "
                "already classifies simple unconditional passive tooltip contributions and fails "
                "conditional/runtime clauses closed; those reviewed projections are not yet a shared "
                "rotation runtime source of truth. Remaining work includes "
                "rank, slot/bar/equipment prerequisites, trigger conditions, duration/resource/"
                "status/target effects, and stacking semantics."
            ),
        ),
        CanonicalMechanicsCoverageEvidence(
            domain=CanonicalKnowledgeDomain.PASSIVE,
            key="armor:weight_passive_semantics",
            status=CanonicalMechanicsCoverageStatus.PARTIAL,
            capability=(
                "Verified static armor math distinguishes exact Light/Medium/Heavy piece counts "
                "for armor-line effects and distinct equipped armor weights for Undaunted Mettle. "
                "Rotation static build evaluation already reuses BuildCalculationContextFactory, "
                "so verified armor and Undaunted passive ownership/ranks reach front/back rotation "
                "contexts instead of being recomputed by the optimizer."
            ),
            evidence_source=(
                "minmax/armor_passive_input_resolver.py; "
                "minmax/undaunted_passive_input_resolver.py; "
                "minmax/context_factory.py; services/rotation_static_build_context_service.py"
            ),
            consumers=ALL_THREE,
            missing_evidence=(
                "Expand the verified armor-passive catalog beyond the passives already owned by "
                "BuildCalculationContextFactory, preserve rank/prerequisite gates, and verify every "
                "Light/Medium/Heavy and composition-sensitive passive that can "
                "change resource costs/recovery, block behavior, damage/healing, penetration, "
                "critical stats, mitigation, movement, or other rotation-relevant state."
            ),
        ),
        CanonicalMechanicsCoverageEvidence(
            domain=CanonicalKnowledgeDomain.GEAR_EFFECT,
            key="gear:conditional_topology",
            status=CanonicalMechanicsCoverageStatus.PARTIAL,
            capability=(
                "Set and mythic identities are canonicalized and EffectVariant-capable gear "
                "effects can participate where verified, but identity alone is not treated "
                "as complete runtime proc semantics."
            ),
            evidence_source=(
                "minmax/character_build/saved_build_adapter.py; "
                "minmax/character_build/effect_availability.py"
            ),
            consumers=ALL_THREE,
            missing_evidence=(
                "For gear sets, arena weapons and mythics, verify trigger, prerequisites, "
                "proc chance, internal cooldown/lockout, duration/tick cadence, stacks, "
                "refresh rule, range, target cap/selection, bar state, resource thresholds, "
                "suppression/prevention and wearer/group/enemy tradeoffs."
            ),
        ),
        CanonicalMechanicsCoverageEvidence(
            domain=CanonicalKnowledgeDomain.SKILL_MECHANIC,
            key="skills:runtime_topology",
            status=CanonicalMechanicsCoverageStatus.PARTIAL,
            capability=(
                "Exact saved abilities, class eligibility, skill bars and verified skill "
                "effects can be canonicalized for rotation/build evaluation."
            ),
            evidence_source=(
                "minmax/character_build/saved_build_adapter.py; "
                "minmax/skill_effect_repository.py"
            ),
            consumers=ALL_THREE,
            missing_evidence=(
                "Verify comprehensive per-skill cost, cast/channel time, GCD occupancy, "
                "duration/tick cadence, range, target cap, targeting rule, buff/debuff/status "
                "effects, execute scaling, LA/HA interaction, proc conditions, passive slot "
                "effects, scribing/subclass dependencies and interrupt/channel behavior."
            ),
        ),
        CanonicalMechanicsCoverageEvidence(
            domain=CanonicalKnowledgeDomain.PROC_CONDITION,
            key="procs:conditional_topology",
            status=CanonicalMechanicsCoverageStatus.PARTIAL,
            capability=(
                "Some canonical effect variants and temporal services can model verified "
                "effects, durations and cooldown-like constraints, but there is not yet a "
                "single exhaustive proc-topology catalog."
            ),
            evidence_source=(
                "minmax/character_build/effect_instance.py; "
                "services/rotation_candidate_temporal_effect_service.py"
            ),
            consumers=ALL_THREE,
            missing_evidence=(
                "Normalize proc topology across skills/sets/mythics/enchants/CP: cause, "
                "prerequisites, deterministic vs stochastic trigger, proc chance, duration, "
                "ticks, ICD/target lockout, stacks, refresh, target selection, range, state "
                "thresholds, suppression and renewal action."
            ),
        ),
        CanonicalMechanicsCoverageEvidence(
            domain=CanonicalKnowledgeDomain.RESOURCE_RECOVERY,
            key="consumables:runtime_resource_and_buff_policy",
            status=CanonicalMechanicsCoverageStatus.PARTIAL,
            capability=(
                "Saved builds retain potion identity; scheduled POTION actions are resolved through "
                "canonical potion evidence into ordered CombatState buff windows, and Medicinal Use "
                "rank extends those source-backed durations through PotionCadence. The same scheduled "
                "uses can now project source-backed instant Health/Magicka/Stamina restoration events. "
                "Rotation requests "
                "also carry potion selection/on-cooldown policy, but this is not yet exhaustive "
                "runtime potion/poison mechanics."
            ),
            evidence_source=(
                "minmax/character_build/saved_build_adapter.py; "
                "minmax/potion_cadence.py; minmax/potion_use_event.py; "
                "services/rotation_plan_potion_combat_state_service.py; "
                "services/rotation_candidate_canonical_plan_evidence_service.py; "
                "ui/rotation_generation_support.py"
            ),
            consumers=ALL_THREE,
            missing_evidence=(
                "Scheduled potion instant-restoration events now feed canonical generated-candidate "
                "sustain evaluation; wire them into any remaining sustain/resource replay consumers "
                "that bypass that composition path and complete remaining potion runtime "
                "effects beyond scheduled buff windows, plus poison effects, poison "
                "trigger cadence, shared cooldowns, invisibility/detection/speed/Unstoppable "
                "effects and any suppression or replacement rules."
            ),
        ),
        CanonicalMechanicsCoverageEvidence(
            domain=CanonicalKnowledgeDomain.COOLDOWN,
            key="consumables:potion_cooldown_effective",
            status=CanonicalMechanicsCoverageStatus.PARTIAL,
            capability=(
                "Rotation Maker enforces one shared potion-cadence timeline when an effective "
                "cooldown is supplied. Saved-build jewelry Potion Speed reductions are resolved "
                "with CP160/Truly Superb and Infused provenance, canonical non-item "
                "potion_cooldown_reduction EffectVariants can be evaluated conservatively, "
                "and a dedicated aggregator emits a final effective cooldown only when the "
                "non-item effect inventory is explicitly complete."
            ),
            evidence_source=(
                "minmax/jewelry_potion_cooldown_repository.py; "
                "services/rotation_saved_build_potion_cooldown_item_service.py; "
                "services/rotation_potion_cooldown_effect_variant_service.py; "
                "services/rotation_effective_potion_cooldown_service.py; "
                "minmax/rotation_potion_cadence.py"
            ),
            consumers=ROTATION_OPTIMIZER,
            missing_evidence=(
                "Provide a complete build/context-wide canonical effect inventory that can "
                "prove all applicable non-item potion-cooldown channels are present or absent, "
                "including conditional skill/passive/set and scenario-specific modifiers, "
                "before automatically promoting the aggregated value into final candidate cadence."
            ),
        ),
        CanonicalMechanicsCoverageEvidence(
            domain=CanonicalKnowledgeDomain.COOLDOWN,
            key="weapon_enchantments:runtime_cadence",
            status=CanonicalMechanicsCoverageStatus.MISSING_CRITICAL,
            capability=(
                "Saved weapon enchantments can be resolved to canonical CombatEffects and "
                "target-debuff EffectVariants with active-bar ownership, duration, and "
                "trait-adjusted magnitude. Cooldown-modifier rules also exist independently. "
                "A fail-closed cadence evidence catalog now records community-observed "
                "activation causes, per-enchantment cooldown scope, off-bar source persistence, "
                "and provisional effect-family cooldown observations without promoting them "
                "to authoritative combat math."
            ),
            evidence_source=(
                "minmax/weapon_enchantment_repository.py; "
                "minmax/weapon_enchantment_effect_service.py; "
                "minmax/combat_cooldown_rules.py; "
                "minmax/weapon_enchantment_runtime_cadence.py; "
                "services/saved_build_capability_service.py"
            ),
            consumers=ROTATION_OPTIMIZER,
            missing_evidence=(
                "Promote the provisional cadence topology only after current-version authoritative "
                "evidence resolves exact base proc cooldown values and activation trigger semantics, including "
                "family), eligible periodic/direct weapon-skill trigger rules, off-bar source "
                "ownership, independent/shared cooldown and target-lockout behavior, and proc-"
                "damage exclusions. Only then may trait-adjusted cooldown rules be composed "
                "into exact runtime cadence."
            ),
        ),
        CanonicalMechanicsCoverageEvidence(
            domain=CanonicalKnowledgeDomain.SKILL_MECHANIC,
            key="weapons:bash_interrupt_poison_topology",
            status=CanonicalMechanicsCoverageStatus.PARTIAL,
            capability=(
                "Weapon type, bar ownership, traits, set identity and weapon-enchantment "
                "identity are canonicalized from saved builds."
            ),
            evidence_source="minmax/character_build/saved_build_adapter.py",
            consumers=ALL_THREE,
            missing_evidence=(
                "Verify weapon-specific light/heavy timing, bash cost/damage modifiers, "
                "interrupt legality/timing, enchant proc/cooldown behavior, poison cadence, "
                "dual-wield/two-hand legacy representation, arena weapon conditional rules "
                "and weapon/passive interactions."
            ),
        ),
        CanonicalMechanicsCoverageEvidence(
            domain=CanonicalKnowledgeDomain.TARGETING,
            key="encounter:target_range_movement_topology",
            status=CanonicalMechanicsCoverageStatus.PARTIAL,
            capability=(
                "Reviewed encounter facts can project timed demand windows and rotation "
                "services can enforce explicit demand/bar/temporal obligations."
            ),
            evidence_source=(
                "services/encounter_rotation_demand_service.py; "
                "services/rotation_plan_temporal_legality_service.py"
            ),
            consumers=ALL_THREE,
            missing_evidence=(
                "Expand reviewed encounter evidence for target swaps, immunity/downtime, "
                "range/positioning, movement time, add waves, execute/burst windows, target "
                "counts/caps, incoming-damage/heal-pressure windows, interrupts, blocking, "
                "synergies and phase-specific legal-action constraints."
            ),
        ),
        CanonicalMechanicsCoverageEvidence(
            domain=CanonicalKnowledgeDomain.OTHER,
            key="niche:stealth_thief_bash_objectives",
            status=CanonicalMechanicsCoverageStatus.NICHE,
            capability=(
                "Stealth/thief, unusual movement, bash-focused and other niche mechanics "
                "should remain canonical evidence even when ordinary raid objectives assign "
                "them zero or negligible relevance."
            ),
            evidence_source="shared optimization objective policy",
            consumers=ALL_THREE,
            research_context=(
                "Do not discard niche mechanics from canonical data merely because the "
                "standard trial candidate generator does not currently prefer them."
            ),
        ),
    )


__all__ = ["shared_canonical_mechanics_inventory"]
