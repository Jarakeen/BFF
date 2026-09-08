from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtremeHealingEventRecipientScopeResult:
    """Recipient-scope boundary for one reviewed healing ability.

    ``single_recipient_safe`` answers whether BFF may safely treat all reviewed
    HEAL coefficient components as belonging to one recipient for the Extreme
    Actual Heal objective.  A false result does not mean the skill is invalid;
    it means coefficient-recipient identity must be resolved before the skill can
    compete for a one-recipient maximum.
    """

    single_recipient_safe: bool
    recipient_selection_required: bool
    unresolved: tuple[str, ...]


class ExtremeHealingEventRecipientScopeService:
    """Block known multi-recipient coefficient aggregation from becoming one heal.

    U50 ``Blood of the Elder Dragon`` (legacy name ``Coagulating Blood``) has a
    self heal and a differently-scaled nearby-ally heal in the same cast.  The
    current canonical HEAL-component classification does not retain recipient
    identity, so summing every HEAL component can incorrectly turn distinct
    recipients into one enormous fictional heal.

    This service is intentionally a reviewed guard, not a universal recipient
    classifier.  Skills not listed here continue through the existing pipeline;
    additional multi-recipient families should be added as their evidence is
    reviewed.
    """

    MULTI_RECIPIENT_DISTINCT_SCALING = frozenset(
        {
            "blood of the elder dragon",
            "coagulating blood",
        }
    )

    @staticmethod
    def _normalized(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    def resolve(self, *, ability_name: str) -> ExtremeHealingEventRecipientScopeResult:
        normalized = self._normalized(ability_name)
        if normalized not in self.MULTI_RECIPIENT_DISTINCT_SCALING:
            return ExtremeHealingEventRecipientScopeResult(
                single_recipient_safe=True,
                recipient_selection_required=False,
                unresolved=(),
            )

        return ExtremeHealingEventRecipientScopeResult(
            single_recipient_safe=False,
            recipient_selection_required=True,
            unresolved=(
                f"{ability_name}: one-recipient Extreme heal is unresolved because "
                "the reviewed cast contains distinct self and nearby-ally healing "
                "components while canonical coefficient metadata does not identify "
                "which HEAL component belongs to which recipient",
            ),
        )
