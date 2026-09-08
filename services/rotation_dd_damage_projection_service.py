from __future__ import annotations

from dataclasses import dataclass
import math

from minmax.rotation_plan import RotationPlan


@dataclass(frozen=True)
class RotationDDDamageInstance:
    """One time-resolved DD damage contribution within a rotation plan.

    Damage must already be resolved by the canonical DD/effect/runtime engines.
    This contract deliberately does not infer skill coefficients, tick counts,
    proc chances, hit success, execute scaling, or target state from an action
    name. A missing value therefore remains unresolved instead of becoming zero.
    """

    time_seconds: float
    source_name: str
    expected_damage: float | None
    event_id: str | None = None
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        time_seconds = float(self.time_seconds)
        if not math.isfinite(time_seconds) or time_seconds < 0:
            raise ValueError("DD damage instance time must be finite and non-negative")
        object.__setattr__(self, "time_seconds", time_seconds)

        source_name = str(self.source_name or "").strip()
        if not source_name:
            raise ValueError("DD damage instance requires source_name")
        object.__setattr__(self, "source_name", source_name)

        if self.expected_damage is not None:
            damage = float(self.expected_damage)
            if not math.isfinite(damage) or damage < 0:
                raise ValueError(
                    "DD damage instance expected_damage must be finite and non-negative"
                )
            object.__setattr__(self, "expected_damage", damage)

        event_id = str(self.event_id or "").strip()
        object.__setattr__(self, "event_id", event_id or None)
        object.__setattr__(
            self,
            "unresolved",
            tuple(str(value).strip() for value in self.unresolved if str(value).strip()),
        )


@dataclass(frozen=True)
class RotationDDDamageSourceBreakdown:
    source_name: str
    known_damage: float
    instance_count: int


@dataclass(frozen=True)
class RotationDDDamageProjection:
    """Auditable damage total for one exact rotation-plan horizon."""

    duration_seconds: float
    known_damage: float
    total_damage: float | None
    projected_dps: float | None
    instances: tuple[RotationDDDamageInstance, ...]
    by_source: tuple[RotationDDDamageSourceBreakdown, ...]
    unresolved: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return self.total_damage is not None and not self.unresolved


class RotationDDDamageProjectionService:
    """Aggregate canonical time-resolved DD damage without inventing missing events."""

    def project(
        self,
        *,
        plan: RotationPlan,
        instances: tuple[RotationDDDamageInstance, ...],
    ) -> RotationDDDamageProjection:
        if plan.duration_seconds <= 0:
            raise ValueError("DD damage projection requires a positive plan duration")

        ordered = tuple(
            sorted(
                tuple(instances),
                key=lambda item: (
                    item.time_seconds,
                    item.source_name.casefold(),
                    item.event_id or "",
                ),
            )
        )
        if any(item.time_seconds > plan.duration_seconds for item in ordered):
            raise ValueError("DD damage instance cannot occur after rotation plan duration")

        seen_ids: set[str] = set()
        unresolved: list[str] = []
        known_damage = 0.0
        source_damage: dict[str, float] = {}
        source_counts: dict[str, int] = {}
        source_labels: dict[str, str] = {}

        for item in ordered:
            if item.event_id is not None:
                key = item.event_id.casefold()
                if key in seen_ids:
                    raise ValueError(f"duplicate DD damage event_id: {item.event_id!r}")
                seen_ids.add(key)

            source_key = item.source_name.casefold()
            source_labels.setdefault(source_key, item.source_name)
            source_counts[source_key] = source_counts.get(source_key, 0) + 1

            if item.expected_damage is None:
                if not item.unresolved:
                    unresolved.append(
                        f"{item.source_name} at {item.time_seconds:g}s has unresolved damage"
                    )
            else:
                known_damage += item.expected_damage
                source_damage[source_key] = (
                    source_damage.get(source_key, 0.0) + item.expected_damage
                )

            unresolved.extend(item.unresolved)

        deduped_unresolved = tuple(dict.fromkeys(unresolved))
        total_damage = None if deduped_unresolved else known_damage
        projected_dps = (
            None
            if total_damage is None
            else total_damage / float(plan.duration_seconds)
        )
        breakdown = tuple(
            RotationDDDamageSourceBreakdown(
                source_name=source_labels[key],
                known_damage=source_damage.get(key, 0.0),
                instance_count=source_counts[key],
            )
            for key in sorted(source_counts, key=lambda value: source_labels[value].casefold())
        )

        return RotationDDDamageProjection(
            duration_seconds=float(plan.duration_seconds),
            known_damage=known_damage,
            total_damage=total_damage,
            projected_dps=projected_dps,
            instances=ordered,
            by_source=breakdown,
            unresolved=deduped_unresolved,
        )
