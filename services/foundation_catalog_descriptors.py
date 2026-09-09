from __future__ import annotations

"""Shared foundational service catalog descriptors.

Metadata only. These descriptors document cross-cutting ownership boundaries used by
multiple BFF workstreams; runtime code continues to use typed imports and explicit
wiring rather than resolving services dynamically from catalog strings.
"""

from services.reference_catalog_descriptors import REFERENCE_SERVICE_DESCRIPTORS
from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


FOUNDATION_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="logs.capability.uptime_analysis",
        domain="logs",
        purpose="Compute observed ESO Logs buff/debuff/skill uptime against both full-pull and damageable-boss time.",
        implementation_path="services.capability_service",
        inputs=("EsoLogsReport", "FightId", "WatchEntry", "BossActiveSeconds"),
        outputs=("UptimeResult", "FightSummary"),
        responsibilities=("esologs_capability_uptime_analysis",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=True,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        provenance=("ESO Logs observed aura tables",),
        notes="This service measures observed fight uptime. It is distinct from saved-build static capability analysis and must not be treated as canonical build mechanics.",
    ),
    ServiceDescriptor(
        service_id="character.progression.persistence",
        domain="character",
        purpose="Persist character-owned skill-line, passive-rank, and Champion Point progression independently from reusable builds.",
        implementation_path="services.character_progression_service",
        inputs=("CanonicalCharacterRecord", "OwnedSkillLines", "PassiveRanks", "PassiveChampionPoints"),
        outputs=("CharacterProgression",),
        dependencies=("build.catalog.persistence",),
        responsibilities=("character_progression_persistence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        evidence_class=EvidenceClass.NONE,
        notes="An explicit zero is a known unpurchased value; a missing key is unknown/unrecorded and must never be silently coerced to zero by calculators.",
    ),
    ServiceDescriptor(
        service_id="mechanics.named_buff_resolution",
        domain="mechanics",
        purpose="Resolve canonical ESO named-buff stacking across heterogeneous reviewed sources and explain suppressed duplicate contributions.",
        implementation_path="services.named_buff_resolution_service",
        inputs=("NamedBuffEffect",),
        outputs=("NamedBuffResolution", "NamedBuffSuppression"),
        responsibilities=("canonical_named_buff_stacking_resolution",),
        behavior=ServiceBehavior.DETERMINISTIC,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes="Duplicate copies of the same named buff and objective do not stack regardless of source type; Major and Minor variants remain distinct named buffs and may stack.",
    ),
    *REFERENCE_SERVICE_DESCRIPTORS,
)


__all__ = ["FOUNDATION_SERVICE_DESCRIPTORS"]
