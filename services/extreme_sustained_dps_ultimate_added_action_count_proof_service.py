from __future__ import annotations

"""Promote one exact generated Ultimate policy into an added-action count proof.

Delayed-Ultimate integration now produces an exact scheduled RotationPlan for each
policy. The proof therefore counts scheduled Ultimate actions on the selected bar and
requires final canonical resource legality instead of relying on the older immediate-
affordability reservation projection.

This service owns no Ultimate generation, cost, scheduling, or damage mechanics.
"""

from dataclasses import dataclass

from minmax.rotation_plan import RotationActionKind
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

        assessment = policy.resource_legality
        legality = getattr(assessment, "is_legal", None)
        if not isinstance(legality, bool):
            unresolved.append(
                "Selected Ultimate policy final resource legality flag is not boolean"
            )
        elif not legality:
            unresolved.append(
                "Selected Ultimate policy failed final canonical resource legality"
            )
        legality_unresolved = getattr(assessment, "unresolved", ())
        if not isinstance(legality_unresolved, tuple):
            raise TypeError("Ultimate resource-legality unresolved evidence must be a tuple")
        unresolved.extend(
            str(item).strip()
            for item in legality_unresolved
            if str(item).strip()
        )

        scheduled = tuple(
            action
            for action in tuple(getattr(policy.plan, "actions", ()) or ())
            if action.kind is RotationActionKind.ULTIMATE
            and str(action.bar or "").strip().casefold() == option
        )
        maximum = len(scheduled)

        deduped = tuple(dict.fromkeys(item for item in unresolved if item))
        proof = ExtremeSustainedDPSAdditionalDamageActionCountProof(
            maximum_additional_damage_actions=maximum,
            proven_safe=bool(maximum is not None and not deduped),
            source=(
                "exact scheduled Ultimate-action count for canonically legal "
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
                f"Scheduled selected-bar Ultimate actions: {maximum}",
                "Final resource legality is required before the exact scheduled count is promoted",
                "For one fully materialized generated policy, the scheduled Ultimate count is both exact and a safe maximum additional-action count for that policy",
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSUltimateAddedActionCountProofService",
    "ExtremeSustainedDPSUltimateAddedActionCountResult",
]
