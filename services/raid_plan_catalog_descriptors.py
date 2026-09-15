from services.service_catalog import (
    EvidenceClass,
    ServiceBehavior,
    ServiceDescriptor,
)


RAID_PLAN_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="raid_plan.repository",
        domain="raid_plan",
        purpose=(
            "Persist and retrieve versioned RaidPlan snapshots without taking ownership "
            "of global Personnel, Character, Saved Build, Team, or encounter identity."
        ),
        implementation_path="services.raid_plan_repository",
        inputs=("RaidPlan", "RaidPlanId"),
        outputs=("PersistedRaidPlan", "RaidPlanCollection"),
        responsibilities=("raid_plan_persistence",),
        behavior=ServiceBehavior.DETERMINISTIC,
        ui_safe=True,
        encounter_aware=True,
        evidence_class=EvidenceClass.NONE,
        notes=(
            "The repository stores trial-specific planning snapshots only. Runtime state, "
            "ESO Logs evidence, and optimization state are not persistence dependencies."
        ),
    ),
)


__all__ = ["RAID_PLAN_SERVICE_DESCRIPTORS"]
