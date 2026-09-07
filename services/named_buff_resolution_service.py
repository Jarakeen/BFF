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
    def resolve(
        cls,
        effects: tuple[TNamedBuffEffect, ...],
        *,
        objective_key: str | None = None,
    ) -> tuple[TNamedBuffEffect, ...]:
        objective = str(objective_key or "").strip()
        selected: dict[tuple[str, str], TNamedBuffEffect] = {}

        for effect in effects:
            effect_objective = str(effect.objective_key or "").strip()
            if objective and effect_objective != objective:
                continue
            buff_key = cls.canonical_key(effect.stacking_key)
            if not buff_key or not effect_objective:
                continue

            identity = (buff_key, effect_objective)
            existing = selected.get(identity)
            if existing is None or float(effect.projected_delta) > float(existing.projected_delta):
                selected[identity] = effect
            elif (
                float(effect.projected_delta) == float(existing.projected_delta)
                and str(effect.source) < str(existing.source)
            ):
                selected[identity] = effect

        return tuple(selected[key] for key in sorted(selected))

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
