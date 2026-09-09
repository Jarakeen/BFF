from __future__ import annotations

from dataclasses import dataclass

from minmax.skill_component_classification import HealRecipientScope
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
    """Score one-recipient, one-time heal groups without cross-event summation.

    Callers may optionally restrict eligible recipient scopes for a concrete
    objective. The default remains unrestricted so other Extreme objectives keep
    their existing behavior. A group whose reviewed coefficients disagree about
    recipient scope fails closed rather than being partially scored.
    """

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
        allowed_recipient_scopes: tuple[HealRecipientScope, ...] | None = None,
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
        allowed = None if allowed_recipient_scopes is None else set(allowed_recipient_scopes)
        group_scores: list[ExtremeHealingEventGroupScore] = []
        unresolved: list[str] = []

        for group in identity.groups:
            group_scopes = {
                getattr(by_number[number], "heal_recipient_scope", None)
                for number in group.coefficient_numbers
            }
            if len(group_scopes) != 1 or None in group_scopes:
                message = (
                    "HEAL event group has mixed or unresolved recipient scope for coefficient(s): "
                    + ", ".join(str(number) for number in group.coefficient_numbers)
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
            group_scope = next(iter(group_scopes))
            if allowed is not None and group_scope not in allowed:
                # Ineligible recipient groups are not unresolved mechanics. They
                # are simply outside the requested objective (for example, PET
                # healing during a player-recipient maximum-heal search).
                continue

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
