from __future__ import annotations

from dataclasses import dataclass

from minmax.skill_component_classification import SkillEffectKind


@dataclass(frozen=True)
class ExtremeHealingComponentEventGroup:
    """One proven one-recipient, one-time healing event.

    Multiple coefficient rows may legitimately belong to the same event. They may
    only be summed when reviewed component identity proves both the recipient and
    event keys match.
    """

    recipient_key: str
    event_key: str
    coefficient_numbers: tuple[int, ...]


@dataclass(frozen=True)
class ExtremeHealingComponentIdentityResult:
    groups: tuple[ExtremeHealingComponentEventGroup, ...]
    complete: bool
    unresolved: tuple[str, ...]


class ExtremeHealingComponentIdentityService:
    """Resolve canonical HEAL components into independently scoreable events.

    This service does not infer recipient or timing from an ability name, tooltip
    wording, coefficient order, or duration. It consumes only reviewed fields
    already attached to the per-coefficient classification. Missing identity is
    explicit and prevents this resolver from claiming a complete event grouping.

    Older Extreme scope guards may remain as compatibility fallbacks while the
    canonical corpus is enriched. Once a skill's HEAL rows all carry identity,
    callers can score each returned group separately instead of accidentally
    summing healing delivered to different recipients or at different times.
    """

    @staticmethod
    def _key(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    def resolve(self, components) -> ExtremeHealingComponentIdentityResult:
        heals = tuple(
            component
            for component in tuple(components or ())
            if getattr(component, "effect_kind", None) is SkillEffectKind.HEAL
        )
        if not heals:
            return ExtremeHealingComponentIdentityResult(
                groups=(),
                complete=True,
                unresolved=(),
            )

        missing: list[int] = []
        grouped: dict[tuple[str, str], list[int]] = {}
        for component in heals:
            number = int(getattr(component, "coefficient_number"))
            recipient_key = self._key(getattr(component, "heal_recipient_key", None))
            event_key = self._key(getattr(component, "heal_event_key", None))
            recipient_scope = getattr(component, "heal_recipient_scope", None)
            temporal_scope = getattr(component, "heal_temporal_scope", None)

            if not recipient_key or not event_key or recipient_scope is None or temporal_scope is None:
                missing.append(number)
                continue

            grouped.setdefault((recipient_key, event_key), []).append(number)

        if missing:
            return ExtremeHealingComponentIdentityResult(
                groups=(),
                complete=False,
                unresolved=(
                    "HEAL component event identity is unresolved for coefficient(s): "
                    + ", ".join(str(number) for number in sorted(missing)),
                ),
            )

        groups = tuple(
            ExtremeHealingComponentEventGroup(
                recipient_key=recipient_key,
                event_key=event_key,
                coefficient_numbers=tuple(sorted(numbers)),
            )
            for (recipient_key, event_key), numbers in sorted(grouped.items())
        )
        return ExtremeHealingComponentIdentityResult(
            groups=groups,
            complete=True,
            unresolved=(),
        )
