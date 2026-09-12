from __future__ import annotations

"""Compose canonical healer role evidence at Generate time."""

from collections.abc import Callable
from pathlib import Path

from engine.config import get_data_dir
from minmax.rotation_demand_window import RotationDemandKind
from models.build_model import PlayerBuild
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateCanonicalPlanEvidenceService,
)
from services.rotation_healer_canonical_role_output_factory_service import (
    RotationHealerCanonicalRoleOutputFactoryService,
)
from services.rotation_healer_channel_runtime_evidence_service import (
    RotationHealerReviewedChannelObservation,
)
from services.rotation_healer_channel_runtime_service import (
    RotationHealerChannelRuntimeEvidence,
)
from services.rotation_healer_delayed_runtime_service import (
    RotationHealerDelayedRuntimeEvidence,
)
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerExternalConditionalDemandAssumption,
)
from services.rotation_healer_periodic_runtime_evidence_service import (
    RotationHealerReviewedRuntimeObservation,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalRoleEvidence
from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle


PlanEvidenceFactory = Callable[..., object]


def _canonical_role(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


class RotationGenerateHealerRoleEvidenceSupport:
    """Join a selected healer build to explicit canonical healing demands.

    Encounter thresholds and windows remain owned by the evidence bundle. Reviewed
    runtime observations and external-conditional assumptions remain explicit caller
    inputs. This composer does not infer group-healing reliability, assignments,
    target counts, phase names, or encounter policy from display text.
    """

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        role_output_factory: RotationHealerCanonicalRoleOutputFactoryService | None = None,
        plan_evidence_factory: PlanEvidenceFactory | None = None,
        reviewed_runtime_observations: tuple[
            RotationHealerReviewedRuntimeObservation, ...
        ] = (),
        delayed_runtime_evidence: tuple[
            RotationHealerDelayedRuntimeEvidence, ...
        ] = (),
        channel_runtime_evidence: tuple[
            RotationHealerChannelRuntimeEvidence, ...
        ] = (),
        reviewed_channel_observations: tuple[
            RotationHealerReviewedChannelObservation, ...
        ] = (),
        external_conditional_assumptions: tuple[
            RotationHealerExternalConditionalDemandAssumption, ...
        ] = (),
        reliable_group_healing: bool | None = None,
        exception_contexts: tuple[str, ...] = (),
        role_output_label: str = "healing demand coverage",
        assigned_support_label: str = "assigned support coverage",
    ) -> None:
        database = (
            Path(database_path)
            if database_path is not None
            else get_data_dir() / "eso.db"
        )
        self.role_output_factory = (
            role_output_factory
            or RotationHealerCanonicalRoleOutputFactoryService(
                database_path=database,
            )
        )
        self.plan_evidence_factory = (
            plan_evidence_factory or RotationCandidateCanonicalPlanEvidenceService
        )
        self.reviewed_runtime_observations = tuple(reviewed_runtime_observations)
        self.delayed_runtime_evidence = tuple(delayed_runtime_evidence)
        self.channel_runtime_evidence = tuple(channel_runtime_evidence)
        self.reviewed_channel_observations = tuple(reviewed_channel_observations)
        self.external_conditional_assumptions = tuple(
            external_conditional_assumptions
        )
        self.reliable_group_healing = reliable_group_healing
        self.exception_contexts = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in exception_contexts
                if str(item).strip()
            )
        )
        self.role_output_label = self._required_label(
            role_output_label,
            "role_output_label",
        )
        self.assigned_support_label = self._required_label(
            assigned_support_label,
            "assigned_support_label",
        )

    def compose(
        self,
        *,
        player_build: PlayerBuild,
        evidence_bundle: RotationCanonicalEvidenceBundle,
    ) -> RotationCanonicalRoleEvidence:
        role_key = _canonical_role(getattr(player_build, "Role", ""))
        if role_key not in {"heal", "healer"}:
            raise ValueError(
                "automatic healer role evidence requires an explicit healer saved-build role"
            )

        healing_demands = tuple(
            demand
            for demand in evidence_bundle.demands
            if demand.kind is RotationDemandKind.HEALING
        )
        if not healing_demands:
            raise ValueError(
                "automatic healer role evidence requires at least one canonical healing demand"
            )

        role_output = self.role_output_factory.build(
            build=player_build,
            demands=healing_demands,
            reviewed_runtime_observations=self.reviewed_runtime_observations,
            delayed_runtime_evidence=self.delayed_runtime_evidence,
            channel_runtime_evidence=self.channel_runtime_evidence,
            reviewed_channel_observations=self.reviewed_channel_observations,
            external_conditional_assumptions=self.external_conditional_assumptions,
        )
        if role_output.role_output_provider is None:
            detail = "; ".join(role_output.unresolved) or "role-output provider unavailable"
            raise ValueError("canonical healer role output is unavailable: " + detail)

        plan_evidence = self.plan_evidence_factory(
            build=player_build,
            resource=evidence_bundle.resource,
            role_output_evidence_provider=role_output,
        )
        return RotationCanonicalRoleEvidence(
            plan_evidence_provider=plan_evidence,
            role_output_label=self.role_output_label,
            assigned_support_label=self.assigned_support_label,
            content_type=str(evidence_bundle.content_type or "").strip(),
            reliable_group_healing=self.reliable_group_healing,
            exception_contexts=self.exception_contexts,
            role_key=role_key,
        )

    @staticmethod
    def _required_label(value: object, field_name: str) -> str:
        label = str(value or "").strip()
        if not label:
            raise ValueError(f"{field_name} must be non-empty")
        return label


__all__ = ["RotationGenerateHealerRoleEvidenceSupport"]
