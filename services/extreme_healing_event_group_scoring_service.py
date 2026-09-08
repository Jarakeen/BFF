from __future__ import annotations

from dataclasses import dataclass

from services.extreme_healing_component_identity_service import (
    ExtremeHealingComponentIdentityService,
)


@dataclass(frozen=True)
class ExtremeHealingEventGroupScore:
    coefficient_numbers: tuple[int, ...]
    normal_heal: float | None
    critical_heal: float | None
    unresolved: tuple[str, ...]


@dataclass(frozen=True)
class ExtremeHealingEventGroupScoringResult:
    groups: tuple[ExtremeHealingEventGroupScore, ...]
    largest_normal_heal: float | None
    largest_critical_heal: float | None
    normal_winner_coefficients: tuple[int, ...]
    critical_winner_coefficients: tuple[int, ...]
    unresolved: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return (
            self.largest_normal_heal is not None
            and self.largest_critical_heal is not None
            and not self.unresolved
        )


class ExtremeHealingEventGroupScoringService:
    """Score one-recipient, one-time heal groups without cross-event summation."""

    def __init__(
        self,
        identity_service: ExtremeHealingComponentIdentityService | None = None,
    ) -> None:
        self.identity_service = identity_service or ExtremeHealingComponentIdentityService()

    def score(
        self,
        *,
        components,
        value_by_coefficient: dict[int, float],
        critical_multiplier: float,
    ) -> ExtremeHealingEventGroupScoringResult:
        identity = self.identity_service.resolve(components)
        if not identity.complete:
            return ExtremeHealingEventGroupScoringResult(
                groups=(),
                largest_normal_heal=None,
                largest_critical_heal=None,
                normal_winner_coefficients=(),
                critical_winner_coefficients=(),
                unresolved=identity.unresolved,
            )

        by_number = {
            int(getattr(component, "coefficient_number")): component
            for component in tuple(components or ())
        }
        group_scores: list[ExtremeHealingEventGroupScore] = []
        unresolved: list[str] = []

        for group in identity.groups:
            missing_values = tuple(
                number
                for number in group.coefficient_numbers
                if number not in value_by_coefficient
            )
            if missing_values:
                message = (
                    "HEAL coefficient values unavailable for event group: "
                    + ", ".join(str(number) for number in missing_values)
                )
                unresolved.append(message)
                group_scores.append(
                    ExtremeHealingEventGroupScore(
                        coefficient_numbers=group.coefficient_numbers,
                        normal_heal=None,
                        critical_heal=None,
                        unresolved=(message,),
                    )
                )
                continue

            unknown_crit = tuple(
                number
                for number in group.coefficient_numbers
                if getattr(by_number[number], "can_crit", None) is None
            )
            normal = sum(
                float(value_by_coefficient[number])
                for number in group.coefficient_numbers
            )
            if unknown_crit:
                message = (
                    "HEAL critical eligibility unresolved for event-group coefficient(s): "
                    + ", ".join(str(number) for number in unknown_crit)
                )
                unresolved.append(message)
                critical = None
                group_unresolved = (message,)
            else:
                critical = sum(
                    float(value_by_coefficient[number]) * float(critical_multiplier)
                    if getattr(by_number[number], "can_crit", None) is True
                    else float(value_by_coefficient[number])
                    for number in group.coefficient_numbers
                )
                group_unresolved = ()

            group_scores.append(
                ExtremeHealingEventGroupScore(
                    coefficient_numbers=group.coefficient_numbers,
                    normal_heal=normal,
                    critical_heal=critical,
                    unresolved=group_unresolved,
                )
            )

        normal_candidates = tuple(
            score for score in group_scores if score.normal_heal is not None
        )
        critical_candidates = tuple(
            score for score in group_scores if score.critical_heal is not None
        )
        normal_winner = (
            max(normal_candidates, key=lambda score: float(score.normal_heal))
            if normal_candidates
            else None
        )
        critical_winner = (
            max(critical_candidates, key=lambda score: float(score.critical_heal))
            if critical_candidates
            else None
        )

        return ExtremeHealingEventGroupScoringResult(
            groups=tuple(group_scores),
            largest_normal_heal=(
                None if normal_winner is None else float(normal_winner.normal_heal)
            ),
            largest_critical_heal=(
                None if critical_winner is None else float(critical_winner.critical_heal)
            ),
            normal_winner_coefficients=(
                () if normal_winner is None else normal_winner.coefficient_numbers
            ),
            critical_winner_coefficients=(
                () if critical_winner is None else critical_winner.coefficient_numbers
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
