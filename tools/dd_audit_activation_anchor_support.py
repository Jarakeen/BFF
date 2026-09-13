from __future__ import annotations

from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageActivationAnchor,
    PeriodicDamageActivationAnchorResolver,
)
from services.rotation_runtime_activation_anchor_evidence_service import (
    RotationRuntimeActivationAnchorEvidence,
    RotationRuntimeActivationAnchorEvidenceService,
)


def parse_explicit_impact_anchor(raw: str) -> RotationRuntimeActivationAnchorEvidence:
    """Parse exact caller-owned impact evidence for the standalone DD audit.

    Format: ``SKILL:ACTION_TIME:SEQUENCE:IMPACT_TIME``.
    The audit deliberately accepts exact evidence only. It never derives impact
    timing from log medians, tooltip travel time, or skill identity.
    """

    text = str(raw or "").strip()
    parts = text.rsplit(":", 3)
    if len(parts) != 4 or not parts[0].strip():
        raise ValueError(
            "impact anchor must use SKILL:ACTION_TIME:SEQUENCE:IMPACT_TIME"
        )
    skill, action_raw, sequence_raw, impact_raw = parts
    try:
        action_time = float(action_raw)
        sequence = int(sequence_raw)
        impact_time = float(impact_raw)
    except ValueError as exc:
        raise ValueError(
            "impact anchor ACTION_TIME, SEQUENCE, and IMPACT_TIME must be numeric"
        ) from exc

    return RotationRuntimeActivationAnchorEvidence(
        skill_entity_id=skill,
        action_time_seconds=action_time,
        action_sequence=sequence,
        activation_anchor=PeriodicDamageActivationAnchor.IMPACT,
        anchor_time_seconds=impact_time,
        source="explicit DD whole-plan audit caller evidence",
    )


def build_explicit_activation_anchor_resolver(
    *,
    plan: RotationPlan,
    evidence: tuple[RotationRuntimeActivationAnchorEvidence, ...],
) -> PeriodicDamageActivationAnchorResolver | None:
    """Bind exact audit evidence to the final plan through the production service."""

    if not evidence:
        return None
    factory = RotationRuntimeActivationAnchorEvidenceService().resolver_factory(evidence)
    return factory(plan)


__all__ = [
    "build_explicit_activation_anchor_resolver",
    "parse_explicit_impact_anchor",
]
