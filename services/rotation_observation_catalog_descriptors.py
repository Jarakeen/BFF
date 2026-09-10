from __future__ import annotations

"""Discovery metadata for Rotation Builder observation/review responsibilities."""

from services.service_catalog import EvidenceClass, ServiceBehavior, ServiceDescriptor


ROTATION_OBSERVATION_SERVICE_DESCRIPTORS: tuple[ServiceDescriptor, ...] = (
    ServiceDescriptor(
        service_id="rotation.healer.periodic_observation_review",
        domain="rotation",
        purpose=(
            "Promote only explicitly selected human-reviewed healer periodic runtime "
            "observation candidates into a separate reviewed fixture."
        ),
        implementation_path="services.rotation_healer_periodic_observation_review_service",
        inputs=("CandidateObservationFixture", "ApprovedSampleIndex", "ReviewNote"),
        outputs=("ReviewedObservationFixture",),
        responsibilities=("rotation_healer_periodic_observation_review_promotion",),
        roles=("Healer",),
        behavior=ServiceBehavior.DETERMINISTIC,
        encounter_aware=False,
        evidence_class=EvidenceClass.OBSERVATIONAL,
        notes=(
            "Extraction success never implies approval. Candidate fixtures remain unchanged; "
            "promotion requires explicit sample indices and review provenance. Refresh/recast "
            "semantics remain a separate evidence responsibility."
        ),
    ),
)


__all__ = ["ROTATION_OBSERVATION_SERVICE_DESCRIPTORS"]
