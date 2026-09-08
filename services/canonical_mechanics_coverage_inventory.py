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
                "to restoration events when completion, fully-charged state, verified base "
                "restore, and modifiers are explicitly supplied."
            ),
            evidence_source="services/rotation_heavy_attack_restoration_evidence_service.py",
            consumers=ROTATION_OPTIMIZER,
            missing_evidence=(
                "Provide verified base restoration by supported weapon/resource context and "
                "the exact passive/set/CP/modifier rules that alter completed heavy restore; "
                "also preserve channel/completion timing evidence rather than inferring it."
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
                "PassiveGrant evidence can participate in build effect availability and "
                "duration evaluation when supplied explicitly."
            ),
            evidence_source=(
                "minmax/character_build/passive_grant.py; "
                "services/rotation_build_effect_duration_service.py"
            ),
            consumers=ALL_THREE,
            missing_evidence=(
                "Build a comprehensive verified passive catalog covering class, weapon, "
                "armor, guild/world, race, vampire/werewolf and other relevant passives, "
                "including rank, slot/bar/equipment prerequisites, trigger conditions, "
                "duration/resource/status/target effects, and stacking semantics."
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
                "Saved builds retain potion identity and the rotation request carries potion "
                "selection/on-cooldown policy, but identity is not equivalent to exhaustive "
                "runtime potion/poison mechanics."
            ),
            evidence_source=(
                "minmax/character_build/saved_build_adapter.py; "
                "ui/rotation_generation_support.py"
            ),
            consumers=ALL_THREE,
            missing_evidence=(
                "Verify potion and poison effects, resource restore amounts, buff/debuff "
                "durations, cooldown, potion-duration/cooldown jewelry modifiers, poison "
                "trigger cadence, shared cooldowns, invisibility/detection/speed/Unstoppable "
                "effects and any suppression or replacement rules."
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
