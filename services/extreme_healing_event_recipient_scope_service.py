from __future__ import annotations

from dataclasses import dataclass
from math import isclose

from minmax.skill_coefficients import SkillCoefficientTrace


@dataclass(frozen=True)
class ExtremeHealingEventRecipientScopeResult:
    """Recipient-scope boundary for one reviewed healing ability.

    ``single_recipient_safe`` answers whether BFF may safely treat the selected
    HEAL coefficient components as belonging to one recipient for the Extreme
    Actual Heal objective. ``selected_coefficient_numbers`` is populated only
    when reviewed coefficient evidence proves which component belongs to the
    winning recipient; ``None`` means the caller should retain every HEAL
    component.
    """

    single_recipient_safe: bool
    recipient_selection_required: bool
    unresolved: tuple[str, ...]
    selected_coefficient_numbers: tuple[int, ...] | None = None


class ExtremeHealingEventRecipientScopeService:
    """Prevent multi-recipient coefficient aggregation from becoming one heal.

    U51 ``Blood of the Elder Dragon`` (legacy name ``Coagulating Blood``) heals
    the caster with the original offensive-stat scaling and nearby allies with
    two-thirds of that scaling. Canonical coefficient metadata does not carry a
    recipient label, so this resolver uses the reviewed scaling relationship
    itself as evidence instead of numeric ability IDs or coefficient ordering.

    The Dragon Blood selection is intentionally strict: there must be exactly two
    HEAL coefficient traces and one complete type-8 ``a/b/c`` scaling vector must
    be two-thirds of the other. If that invariant is absent or ambiguous, the
    skill remains unresolved rather than guessing which component is self.
    """

    MULTI_RECIPIENT_DISTINCT_SCALING = frozenset(
        {
            "blood of the elder dragon",
            "coagulating blood",
        }
    )
    ALLY_SCALING = 2.0 / 3.0
    _REL_TOLERANCE = 1e-6
    _ABS_TOLERANCE = 1e-9

    @staticmethod
    def _normalized(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @classmethod
    def _scaled_term(cls, *, original: float, candidate: float) -> bool:
        return isclose(
            float(candidate),
            float(original) * cls.ALLY_SCALING,
            rel_tol=cls._REL_TOLERANCE,
            abs_tol=cls._ABS_TOLERANCE,
        )

    @classmethod
    def _is_two_thirds_scaling(
        cls,
        *,
        original: SkillCoefficientTrace,
        candidate: SkillCoefficientTrace,
    ) -> bool:
        if str(original.coefficient_type) != "8" or str(candidate.coefficient_type) != "8":
            return False
        return all(
            (
                cls._scaled_term(original=original.a, candidate=candidate.a),
                cls._scaled_term(original=original.b, candidate=candidate.b),
                cls._scaled_term(original=original.c, candidate=candidate.c),
            )
        )

    def resolve(
        self,
        *,
        ability_name: str,
        heal_coefficient_numbers: tuple[int, ...] = (),
        coefficient_traces: tuple[SkillCoefficientTrace, ...] = (),
    ) -> ExtremeHealingEventRecipientScopeResult:
        normalized = self._normalized(ability_name)
        if normalized not in self.MULTI_RECIPIENT_DISTINCT_SCALING:
            return ExtremeHealingEventRecipientScopeResult(
                single_recipient_safe=True,
                recipient_selection_required=False,
                unresolved=(),
            )

        numbers = tuple(dict.fromkeys(int(number) for number in heal_coefficient_numbers))
        traces = {
            int(trace.coefficient_number): trace
            for trace in coefficient_traces
            if int(trace.coefficient_number) in numbers
        }
        if len(numbers) == 2 and len(traces) == 2:
            first, second = numbers
            first_trace = traces[first]
            second_trace = traces[second]
            if self._is_two_thirds_scaling(original=first_trace, candidate=second_trace):
                return ExtremeHealingEventRecipientScopeResult(
                    single_recipient_safe=True,
                    recipient_selection_required=False,
                    unresolved=(),
                    selected_coefficient_numbers=(first,),
                )
            if self._is_two_thirds_scaling(original=second_trace, candidate=first_trace):
                return ExtremeHealingEventRecipientScopeResult(
                    single_recipient_safe=True,
                    recipient_selection_required=False,
                    unresolved=(),
                    selected_coefficient_numbers=(second,),
                )

        return ExtremeHealingEventRecipientScopeResult(
            single_recipient_safe=False,
            recipient_selection_required=True,
            unresolved=(
                f"{ability_name}: one-recipient Extreme heal is unresolved because "
                "the reviewed cast contains distinct self and nearby-ally healing "
                "components and canonical coefficient traces do not prove an exact "
                "original-versus-two-thirds recipient scaling pair",
            ),
        )
