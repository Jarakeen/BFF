from __future__ import annotations

"""Canonical discovery catalog for BFF architectural services.

The catalog is intentionally read-only metadata. It does not import, instantiate,
select, or execute implementations by string identity. Application code should
continue using normal typed imports and explicit dependency wiring.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ServiceLifecycle(str, Enum):
    PLANNED = "planned"
    PARTIAL = "partial"
    IMPLEMENTED = "implemented"
    DISABLED = "disabled"


class ServiceAuthority(str, Enum):
    CANONICAL = "canonical"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


class ServiceBehavior(str, Enum):
    DETERMINISTIC = "deterministic"
    HEURISTIC = "heuristic"
    CALIBRATED = "calibrated"
    HYBRID = "hybrid"


class EvidenceClass(str, Enum):
    GAME_MECHANIC = "game_mechanic"
    OBSERVATIONAL = "observational"
    CALIBRATION = "calibration"
    POLICY = "policy"
    MIXED = "mixed"
    NONE = "none"


class CapabilityStatus(str, Enum):
    UNAVAILABLE = "unavailable"
    PLANNED = "planned"
    PARTIAL = "partial"
    IMPLEMENTED = "implemented"


class ServiceCatalogError(ValueError):
    """Base catalog metadata error."""


class ServiceCatalogAmbiguityError(ServiceCatalogError):
    """A supposedly unique service query matched more than one descriptor."""


@dataclass(frozen=True)
class ServiceDescriptor:
    """Stable architectural metadata for one BFF service responsibility."""

    service_id: str
    domain: str
    purpose: str
    implementation_path: str
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    lifecycle: ServiceLifecycle = ServiceLifecycle.IMPLEMENTED
    authority: ServiceAuthority = ServiceAuthority.CANONICAL
    behavior: ServiceBehavior = ServiceBehavior.DETERMINISTIC
    roles: tuple[str, ...] = ()
    responsibilities: tuple[str, ...] = ()
    ui_safe: bool = False
    encounter_aware: bool = False
    evidence_class: EvidenceClass = EvidenceClass.NONE
    provenance: tuple[str, ...] = ()
    supersedes: tuple[str, ...] = ()
    superseded_by: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        for field_name in ("service_id", "domain", "purpose", "implementation_path"):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ServiceCatalogError(f"{field_name} is required")
            object.__setattr__(self, field_name, value)

        object.__setattr__(self, "inputs", _clean_tuple(self.inputs))
        object.__setattr__(self, "outputs", _clean_tuple(self.outputs))
        object.__setattr__(self, "dependencies", _clean_tuple(self.dependencies))
        object.__setattr__(self, "roles", _clean_tuple(self.roles))
        object.__setattr__(self, "responsibilities", _clean_tuple(self.responsibilities))
        object.__setattr__(self, "provenance", _clean_tuple(self.provenance))
        object.__setattr__(self, "supersedes", _clean_tuple(self.supersedes))
        if self.superseded_by is not None:
            object.__setattr__(
                self,
                "superseded_by",
                str(self.superseded_by).strip() or None,
            )

    @property
    def available(self) -> bool:
        return (
            self.lifecycle in {ServiceLifecycle.PARTIAL, ServiceLifecycle.IMPLEMENTED}
            and self.authority is not ServiceAuthority.DEPRECATED
        )


def _clean_tuple(values: Iterable[str]) -> tuple[str, ...]:
    cleaned = tuple(str(value or "").strip() for value in values)
    if any(not value for value in cleaned):
        raise ServiceCatalogError("descriptor tuple values must be non-empty")
    return cleaned


class ServiceCatalog:
    """Read-only discovery and capability queries over explicit descriptors."""

    def __init__(self, descriptors: Iterable[ServiceDescriptor]) -> None:
        self._descriptors = tuple(descriptors)

    @property
    def descriptors(self) -> tuple[ServiceDescriptor, ...]:
        return self._descriptors

    def get(self, service_id: str) -> ServiceDescriptor | None:
        wanted = str(service_id or "").strip()
        matches = tuple(row for row in self._descriptors if row.service_id == wanted)
        if len(matches) > 1:
            raise ServiceCatalogAmbiguityError(f"duplicate service id: {wanted}")
        return matches[0] if matches else None

    def by_domain(
        self,
        domain: str,
        *,
        available_only: bool = False,
    ) -> tuple[ServiceDescriptor, ...]:
        wanted = str(domain or "").strip().casefold()
        rows = tuple(
            row for row in self._descriptors if row.domain.casefold() == wanted
        )
        if available_only:
            rows = tuple(row for row in rows if row.available)
        return rows

    def canonical_for(self, responsibility: str) -> ServiceDescriptor | None:
        wanted = str(responsibility or "").strip()
        matches = tuple(
            row
            for row in self._descriptors
            if wanted in row.responsibilities
            and row.authority is ServiceAuthority.CANONICAL
            and row.lifecycle is not ServiceLifecycle.DISABLED
        )
        if len(matches) > 1:
            ids = ", ".join(row.service_id for row in matches)
            raise ServiceCatalogAmbiguityError(
                f"multiple canonical services for {wanted}: {ids}"
            )
        return matches[0] if matches else None

    def capability_status(self, responsibility: str) -> CapabilityStatus:
        wanted = str(responsibility or "").strip()
        rows = tuple(
            row for row in self._descriptors if wanted in row.responsibilities
        )
        if not rows:
            return CapabilityStatus.UNAVAILABLE

        canonical = tuple(
            row
            for row in rows
            if row.authority is ServiceAuthority.CANONICAL
            and row.lifecycle is not ServiceLifecycle.DISABLED
        )
        considered = canonical or tuple(
            row for row in rows if row.authority is not ServiceAuthority.DEPRECATED
        )
        lifecycles = {row.lifecycle for row in considered}
        if ServiceLifecycle.IMPLEMENTED in lifecycles:
            return CapabilityStatus.IMPLEMENTED
        if ServiceLifecycle.PARTIAL in lifecycles:
            return CapabilityStatus.PARTIAL
        if ServiceLifecycle.PLANNED in lifecycles:
            return CapabilityStatus.PLANNED
        return CapabilityStatus.UNAVAILABLE

    def consuming(self, type_id: str) -> tuple[ServiceDescriptor, ...]:
        wanted = str(type_id or "").strip()
        return tuple(row for row in self._descriptors if wanted in row.inputs)

    def producing(self, type_id: str) -> tuple[ServiceDescriptor, ...]:
        wanted = str(type_id or "").strip()
        return tuple(row for row in self._descriptors if wanted in row.outputs)

    def dependencies_of(self, service_id: str) -> tuple[ServiceDescriptor, ...]:
        row = self.get(service_id)
        if row is None:
            return ()
        return tuple(
            dependency
            for dependency_id in row.dependencies
            if (dependency := self.get(dependency_id)) is not None
        )

    def dependents_of(self, service_id: str) -> tuple[ServiceDescriptor, ...]:
        wanted = str(service_id or "").strip()
        return tuple(row for row in self._descriptors if wanted in row.dependencies)


SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="encounter.projection",
        domain="encounter",
        purpose="Load and normalize canonical encounter definitions for deterministic consumers.",
        implementation_path="services.encounter_projection",
        inputs=("EncounterSource",),
        outputs=("EncounterDefinition",),
        responsibilities=("encounter_definition_projection",),
        encounter_aware=True,
        evidence_class=EvidenceClass.GAME_MECHANIC,
    ),
    ServiceDescriptor(
        service_id="encounter.repository",
        domain="encounter",
        purpose="Provide deterministic read-only access to canonical encounter records.",
        implementation_path="services.encounter_repository",
        inputs=("EncounterId", "CanonicalEncounterData"),
        outputs=("EncounterDefinition",),
        dependencies=("encounter.projection",),
        responsibilities=("canonical_encounter_access",),
        ui_safe=True,
        encounter_aware=True,
        evidence_class=EvidenceClass.GAME_MECHANIC,
    ),
    ServiceDescriptor(
        service_id="team.prescription.candidate_pool",
        domain="team",
        purpose="Group and gate pre-evaluated team prescription candidates by roster slot.",
        implementation_path="services.team_prescription_candidate_pool",
        inputs=("PrescribedRoster", "PrescribedCandidatePoolInput"),
        outputs=("PrescribedCandidatePoolResult",),
        responsibilities=("team_prescription_candidate_pooling",),
        evidence_class=EvidenceClass.POLICY,
    ),
    ServiceDescriptor(
        service_id="team.prescription.optimizer",
        domain="team",
        purpose="Select unique evidence-backed winners for prescribed roster slots.",
        implementation_path="services.team_prescription_optimizer",
        inputs=("PrescribedRoster", "PrescribedCandidatePoolResult"),
        outputs=("TeamPrescriptionOptimizationResult",),
        responsibilities=("team_prescription_candidate_optimization",),
        evidence_class=EvidenceClass.POLICY,
    ),
    ServiceDescriptor(
        service_id="team.prescription.candidate_source",
        domain="team",
        purpose="Evaluate explicit open-slot candidates into evidence used by prescription.",
        implementation_path="services.team_prescription_candidate_source",
        inputs=("PrescribedRoster", "PrescribedOpenSlotCandidate"),
        outputs=("PrescribedCandidateSourceResult",),
        responsibilities=("team_prescription_candidate_evidence",),
        evidence_class=EvidenceClass.MIXED,
    ),
    ServiceDescriptor(
        service_id="team.prescription.pipeline",
        domain="team",
        purpose="Run the canonical evidence-backed candidate portion of team prescription end to end.",
        implementation_path="services.team_prescription_pipeline",
        inputs=("PrescribedRoster", "PrescribedCandidatePoolInput"),
        outputs=("TeamPrescriptionPipelineResult",),
        dependencies=(
            "team.prescription.candidate_pool",
            "team.prescription.optimizer",
            "team.prescription.candidate_source",
        ),
        responsibilities=("team_prescription_pipeline",),
        ui_safe=True,
        encounter_aware=False,
        evidence_class=EvidenceClass.MIXED,
    ),
    ServiceDescriptor(
        service_id="rotation.duration_refinement",
        domain="rotation",
        purpose="Refine rotation plans using canonical duration and demand scheduling rules.",
        implementation_path="services.rotation_duration_refinement_service",
        inputs=("RotationPlan", "AbilityPriorityList", "RotationDemandWindow"),
        outputs=("RotationRefinementResult",),
        responsibilities=("rotation_duration_refinement",),
        encounter_aware=True,
        evidence_class=EvidenceClass.GAME_MECHANIC,
    ),
    ServiceDescriptor(
        service_id="rotation.candidate_generation",
        domain="rotation",
        purpose="Generate deterministic rotation-plan variants from explicit policy options.",
        implementation_path="services.rotation_candidate_generation_service",
        inputs=("RotationPlan", "AbilityPriorityList", "RotationDemandWindow"),
        outputs=("GeneratedRotationCandidate",),
        dependencies=("rotation.duration_refinement",),
        responsibilities=("rotation_candidate_generation",),
        encounter_aware=True,
        evidence_class=EvidenceClass.POLICY,
    ),
    ServiceDescriptor(
        service_id="extreme.healing_event",
        domain="extreme",
        purpose="Evaluate one healing event through canonical build and combat math.",
        implementation_path="services.extreme_healing_event_service",
        inputs=("PlayerBuild", "HealingEntityId"),
        outputs=("ExtremeHealingEventResult",),
        responsibilities=("extreme_healing_event_evaluation",),
        roles=("Healer",),
        encounter_aware=False,
        evidence_class=EvidenceClass.GAME_MECHANIC,
    ),
    ServiceDescriptor(
        service_id="extreme.actual_heal_optimization",
        domain="extreme",
        purpose="Maximize an identified healing event through canonical whole-build evaluation.",
        implementation_path="services.extreme_actual_heal_optimization_service",
        inputs=("PlayerBuild", "HealingEntityId"),
        outputs=("ExtremeActualHealOptimizationResult",),
        dependencies=("extreme.healing_event",),
        responsibilities=("extreme_actual_heal_optimization",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.GAME_MECHANIC,
        notes=(
            "Tooltip deltas may bound candidate discovery but are never final score. "
            "Observational calibration must remain distinct from canonical mechanics."
        ),
    ),
)


SERVICE_CATALOG = ServiceCatalog(SERVICE_DESCRIPTORS)


def get_service(service_id: str) -> ServiceDescriptor | None:
    return SERVICE_CATALOG.get(service_id)


def services_by_domain(
    domain: str,
    *,
    available_only: bool = False,
) -> tuple[ServiceDescriptor, ...]:
    return SERVICE_CATALOG.by_domain(domain, available_only=available_only)


def canonical_service_for(responsibility: str) -> ServiceDescriptor | None:
    return SERVICE_CATALOG.canonical_for(responsibility)


def capability_status(responsibility: str) -> CapabilityStatus:
    return SERVICE_CATALOG.capability_status(responsibility)


def services_consuming(type_id: str) -> tuple[ServiceDescriptor, ...]:
    return SERVICE_CATALOG.consuming(type_id)


def services_producing(type_id: str) -> tuple[ServiceDescriptor, ...]:
    return SERVICE_CATALOG.producing(type_id)
