from dataclasses import dataclass
from .group_evaluation import GroupEvaluation


@dataclass(frozen=True)
class TeamComparison:
    """Compares two roster evaluations to determine a preferred team."""
    baseline_name: str
    candidate_name: str
    baseline_evaluation: GroupEvaluation
    candidate_evaluation: GroupEvaluation

    @property
    def modeled_damage_delta(self) -> float:
        """Difference in modeled composition damage: candidate minus baseline."""
        return (
            self.candidate_evaluation.group_damage
            - self.baseline_evaluation.group_damage
        )

    @property
    def rankable(self) -> bool:
        """False if either evaluation has unresolved effects."""
        return (
            not self.baseline_evaluation.unresolved_effects
            and not self.candidate_evaluation.unresolved_effects
        )

    @property
    def preferred_team_name(self) -> str | None:
        """
        Returns the name of the preferred team, or None if no clear winner.
        - Returns candidate_name only when rankable and delta > 0.
        - Returns baseline_name only when rankable and delta < 0.
        - Returns None otherwise (not rankable or delta == 0).
        """
        if not self.rankable:
            return None

        if self.modeled_damage_delta > 0:
            return self.candidate_name
        elif self.modeled_damage_delta < 0:
            return self.baseline_name
        else:
            return None

    @property
    def explanation(self) -> str:
        """Short explanation of the comparison result."""
        if not self.rankable:
            baseline_unresolved = self.baseline_evaluation.unresolved_effects
            candidate_unresolved = self.candidate_evaluation.unresolved_effects

            if baseline_unresolved or candidate_unresolved:
                if baseline_unresolved and candidate_unresolved:
                    return (
                        f"Cannot rank: both rosters have unresolved effects. "
                        f"Baseline: {baseline_unresolved}; "
                        f"Candidate: {candidate_unresolved}"
                    )
                elif baseline_unresolved:
                    return f"Cannot rank: baseline has unresolved effects {baseline_unresolved}"
                else:
                    return f"Cannot rank: candidate has unresolved effects {candidate_unresolved}"
        
        delta = self.modeled_damage_delta
        if delta > 0:
            return (
                f"{self.candidate_name} wins: "
                f"+{delta:.1f} modeled composition damage vs {self.baseline_name}"
            )
        elif delta < 0:
            return (
                f"{self.baseline_name} wins: "
                f"+{abs(delta):.1f} modeled composition damage vs {self.candidate_name}"
            )
        else:
            return f"Tied: both rosters have same modeled composition damage ({delta:.1f})"
