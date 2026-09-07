from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar


class NamedBuffEffect(Protocol):
    """Minimal contract for effects that participate in ESO named-buff stacking."""

    stacking_key: str
    objective_key: str
    projected_delta: float
    source: str


TNamedBuffEffect = TypeVar("TNamedBuffEffect", bound=NamedBuffEffect)


@dataclass(frozen=True)
class NamedBuffContribution:
    """Source-neutral named buff contribution.

    The source may be a skill, potion, set, passive, group provider, or another
    reviewed mechanic. Stacking is determined by the canonical named buff and
    affected objective, never by source type.
    """

    stacking_key: str
    objective_key: str
    projected_delta: float
    source: str
    source_kind: str = "other"


@dataclass(frozen=True)
class NamedBuffSuppression:
    """Auditable explanation for one reviewed contribution that did not stack."""

    stacking_key: str
    objective_key: str
    suppressed_source: str
    retained_source: str
    reason: str


@dataclass(frozen=True)
class NamedBuffResolution:
    selected: tuple[NamedBuffEffect, ...]
    suppressed: tuple[NamedBuffSuppression, ...]


class NamedBuffResolutionService:
    """Resolve reviewed named buffs across heterogeneous ESO sources.

    Duplicate copies of the same named Major/Minor buff do not stack even when
    they come from different source systems. Major and Minor variants remain
    different named buffs and therefore stack. The objective is part of the
    identity because one named buff can legitimately contribute to more than one
    modeled stat.
    """

    @staticmethod
    def canonical_key(value: object) -> str:
        return "_".join(str(value or "").strip().casefold().replace("-", " ").split())

    @classmethod
    def explain(
        cls,
        effects: tuple[TNamedBuffEffect, ...],
        *,
        objective_key: str | None = None,
    ) -> NamedBuffResolution:
        objective = str(objective_key or "").strip()
        grouped: dict[tuple[str, str], list[TNamedBuffEffect]] = {}

        for effect in effects:
            effect_objective = str(effect.objective_key or "").strip()
            if objective and effect_objective != objective:
                continue
            buff_key = cls.canonical_key(effect.stacking_key)
            if not buff_key or not effect_objective:
                continue
            grouped.setdefault((buff_key, effect_objective), []).append(effect)

        selected: list[TNamedBuffEffect] = []
        suppressed: list[NamedBuffSuppression] = []
        for identity in sorted(grouped):
            rows = grouped[identity]
            retained = min(
                rows,
                key=lambda effect: (-float(effect.projected_delta), str(effect.source)),
            )
            selected.append(retained)
            for effect in rows:
                if effect is retained:
                    continue
                suppressed.append(
                    NamedBuffSuppression(
                        stacking_key=identity[0],
                        objective_key=identity[1],
                        suppressed_source=str(effect.source),
                        retained_source=str(retained.source),
                        reason=(
                            f"{identity[0].replace('_', ' ')} does not stack with another "
                            "copy of the same named buff"
                        ),
                    )
                )

        return NamedBuffResolution(
            selected=tuple(selected),
            suppressed=tuple(suppressed),
        )

    @classmethod
    def resolve(
        cls,
        effects: tuple[TNamedBuffEffect, ...],
        *,
        objective_key: str | None = None,
    ) -> tuple[TNamedBuffEffect, ...]:
        return tuple(cls.explain(effects, objective_key=objective_key).selected)

    @classmethod
    def score(
        cls,
        effects: tuple[TNamedBuffEffect, ...],
        *,
        objective_key: str,
    ) -> tuple[float, tuple[str, ...]]:
        selected = cls.resolve(effects, objective_key=objective_key)
        return (
            sum(float(effect.projected_delta) for effect in selected),
            tuple(str(effect.source) for effect in selected),
        )
