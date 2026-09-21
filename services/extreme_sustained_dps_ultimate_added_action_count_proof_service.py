from __future__ import annotations

"""Promote canonical Ultimate affordability capacity into an added-action count proof.

For one explicit generated Ultimate policy, RotationUltimateService already resolves the
selected slot-6 identity/cost and projects the shared Ultimate resource timeline. Its
availability_times are emitted by repeatedly reserving/spending the selected cost as soon
as the explicit resource pool can afford another activation. The number of such times is
therefore a safe maximum on how many Ultimate damage actions that policy can add during
the exact horizon.

This service owns no Ultimate generation, cost, scheduling, or damage mechanics.
"""

from dataclasses import dataclass

from services.extreme_sustained_dps_rotation_family_action_count_proof_service import (
    ExtremeSustainedDPSAdditionalDamageActionCountProof,
)
from services.extreme_sustained_dps_rotation_policy_frontier_service import (
    ExtremeSustainedDPSRotationPolicyCandidate,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSUltimateAddedActionCountResult:
    ultimate_option: str
    maximum_additional_damage_actions: int | None
    proof: ExtremeSustainedDPSAdditionalDamageActionCountProof
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSUltimateAddedActionCountProofService:
    """Count maximum policy-added Ultimate actions from canonical resource evidence."""

    _CHOICE_DIAGNOSTIC = "choice policy is unresolved"

    @classmethod
    def prove(
        cls,
        policy: ExtremeSustainedDPSRotationPolicyCandidate,
    ) -> ExtremeSustainedDPSUltimateAddedActionCountResult:
        option = str(policy.ultimate_option or "").strip().casefold()
        unresolved = [
            str(item).strip()
            for item in policy.unresolved
            if str(item).strip()
        ]

        if option == "none":
            proof = ExtremeSustainedDPSAdditionalDamageActionCountProof(
                maximum_additional_damage_actions=0,
                proven_safe=not unresolved,
                source="explicit no-Ultimate generated policy",
                unresolved=tuple(dict.fromkeys(unresolved)),
            )
            return ExtremeSustainedDPSUltimateAddedActionCountResult(
                ultimate_option=option,
                maximum_additional_damage_actions=0,
                proof=proof,
                evidence=(
                    "Generated Ultimate policy: none",
                    "Maximum additional Ultimate damage actions: 0",
                ),
                unresolved=proof.unresolved,
            )

        if option not in {"front", "back"}:
            unresolved.append(
                f"Unsupported generated Ultimate policy option: {policy.ultimate_option!r}"
            )

        projection = policy.ultimate_projection
        if projection is None:
            unresolved.append(
                "Selected Ultimate policy has no canonical Ultimate resource projection"
            )
            maximum = None
        else:
            projection_unresolved = tuple(
                str(item).strip()
                for item in projection.unresolved
                if str(item).strip()
                and cls._CHOICE_DIAGNOSTIC not in str(item).casefold()
            )
            unresolved.extend(projection_unresolved)

            resources = tuple(projection.resource_projections)
            if len(resources) != 1:
                unresolved.append(
                    "Selected Ultimate policy must expose exactly one canonical resource projection"
                )
                maximum = None
            else:
                projected_bar, resource_projection = resources[0]
                if str(projected_bar or "").strip().casefold() != option:
                    unresolved.append(
                        "Ultimate resource projection bar does not match selected policy"
                    )
                maximum = len(tuple(resource_projection.availability_times))

            if len(tuple(projection.spend_rules)) != 1:
                unresolved.append(
                    "Selected Ultimate policy must expose exactly one canonical spend rule"
                )

        deduped = tuple(dict.fromkeys(item for item in unresolved if item))
        proof = ExtremeSustainedDPSAdditionalDamageActionCountProof(
            maximum_additional_damage_actions=maximum,
            proven_safe=bool(maximum is not None and not deduped),
            source=(
                "canonical UltimateResourceTimeline affordability capacity for "
                f"explicit {option or 'unknown'}-bar Ultimate policy"
            ),
            unresolved=deduped,
        )

        return ExtremeSustainedDPSUltimateAddedActionCountResult(
            ultimate_option=option,
            maximum_additional_damage_actions=maximum,
            proof=proof,
            evidence=(
                f"Generated Ultimate policy: {option or '(unknown)'}",
                (
                    f"Canonical affordability/reservation opportunities: {maximum}"
                    if maximum is not None
                    else "Canonical affordability/reservation opportunities: unresolved"
                ),
                "Each availability reserves the selected canonical Ultimate cost from the shared pool",
                "The availability count is used only as a maximum added-action count, not as a claim that every cast is scheduled or optimal",
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSUltimateAddedActionCountProofService",
    "ExtremeSustainedDPSUltimateAddedActionCountResult",
]
