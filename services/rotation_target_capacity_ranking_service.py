from __future__ import annotations

from services.rotation_candidate_ranking_service import RotationCandidateRankingService


class RotationTargetCapacityRankingService(RotationCandidateRankingService):
    """Extend canonical ranking with explicit target-capacity hard failures.

    The base ranking service remains authoritative for all existing hard and soft
    evidence. This subclass only inserts target-capacity violation count alongside
    the existing target/range legality dimensions and adds explainable reasons.
    """

    @classmethod
    def _sort_key(cls, item):
        base = super()._sort_key(item)
        capacity_violations = tuple(
            getattr(item.scorecard, "target_capacity_violations", ())
        )
        capacity_count = len(capacity_violations)

        # Base tuple positions are stable hard-obligation dimensions. Increase the
        # aggregate hard-failure count, then insert capacity immediately after
        # target-identity violations and before slot legality.
        return (
            base[0],
            int(base[1]) + capacity_count,
            *base[2:9],
            capacity_count,
            *base[9:],
        )

    @staticmethod
    def _reasons(scorecard):
        reasons = list(RotationCandidateRankingService._reasons(scorecard))
        violations = tuple(getattr(scorecard, "target_capacity_violations", ()))
        if not violations:
            return tuple(reasons)

        capacity_reasons: list[str] = [
            f"{len(violations)} target-capacity violation(s)"
        ]
        for violation in violations:
            requirement = violation.requirement
            label = requirement.action_name or requirement.action_kind.value
            scope = f" on {requirement.bar} bar" if requirement.bar else ""
            capacity_reasons.append(
                f"target capacity for {label!r}{scope} at "
                f"{violation.time_seconds:g}s in {violation.demand.name!r}: "
                f"cap {requirement.maximum_targets}, demand "
                f"{violation.demand.target_count}, shortfall {violation.shortfall}; "
                f"{violation.reason}"
            )
        return tuple(capacity_reasons + reasons)


__all__ = ["RotationTargetCapacityRankingService"]
