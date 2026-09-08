from __future__ import annotations

from dataclasses import dataclass
import math
import re

from services.rotation_healer_action_healing_service import (
    RotationHealerDelayedHealSeed,
    RotationHealerResolvedHealEvent,
)


_AFTER_SECONDS_RE = re.compile(
    r"\bafter\s+(?P<delay>\d+(?:\.\d+)?)\s+seconds?\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RotationHealerDelayedRuntimeEvidence:
    source_name: str
    coefficient_number: int
    delay_seconds: float
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        name = str(self.source_name or "").strip()
        if not name:
            raise ValueError("delayed healer runtime evidence requires source_name")
        object.__setattr__(self, "source_name", name)
        object.__setattr__(self, "coefficient_number", int(self.coefficient_number))
        delay = float(self.delay_seconds)
        if not math.isfinite(delay) or delay < 0:
            raise ValueError("delayed healer runtime delay must be finite and non-negative")
        object.__setattr__(self, "delay_seconds", delay)
        provenance = tuple(
            dict.fromkeys(str(item).strip() for item in self.provenance if str(item).strip())
        )
        object.__setattr__(self, "provenance", provenance)


@dataclass(frozen=True)
class RotationHealerDelayedRuntimeProjection:
    events: tuple[RotationHealerResolvedHealEvent, ...]
    unresolved: tuple[str, ...] = ()


class RotationHealerDelayedRuntimeService:
    """Schedule delayed healer consequences only from explicit delay evidence.

    This service intentionally models one delayed consequence per activation.
    Reapplication topology such as Budding Seeds' second-activation bloom remains
    a separate concern because a second button press may terminate or transform
    the original pending/periodic state rather than create another ordinary copy.
    """

    def project(
        self,
        *,
        seeds: tuple[RotationHealerDelayedHealSeed, ...],
        evidence: tuple[RotationHealerDelayedRuntimeEvidence, ...],
        horizon_seconds: float,
    ) -> RotationHealerDelayedRuntimeProjection:
        horizon = float(horizon_seconds)
        if not math.isfinite(horizon) or horizon < 0:
            raise ValueError("delayed healer horizon must be finite and non-negative")

        evidence_by_key = {
            (item.source_name.casefold(), item.coefficient_number): item
            for item in evidence
        }
        events: list[RotationHealerResolvedHealEvent] = []
        unresolved: list[str] = []

        for seed in seeds:
            key = (seed.source_name.casefold(), int(seed.coefficient_number))
            runtime = evidence_by_key.get(key)
            if runtime is None:
                unresolved.append(
                    f"{seed.source_name} coefficient {seed.coefficient_number}: "
                    "delayed healing runtime evidence unavailable"
                )
                continue
            event_time = float(seed.time_seconds) + runtime.delay_seconds
            if event_time > horizon:
                continue
            events.append(
                RotationHealerResolvedHealEvent(
                    time_seconds=event_time,
                    sequence=int(seed.sequence),
                    source_name=seed.source_name,
                    coefficient_number=int(seed.coefficient_number),
                    modeled_heal=float(seed.modeled_heal),
                )
            )

        return RotationHealerDelayedRuntimeProjection(
            events=tuple(
                sorted(
                    events,
                    key=lambda item: (
                        item.time_seconds,
                        item.sequence,
                        item.source_name.casefold(),
                        item.coefficient_number,
                    ),
                )
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


def extract_delayed_heal_runtime_evidence(
    *,
    source_name: str,
    coefficient_number: int,
    component_fragment: str,
) -> RotationHealerDelayedRuntimeEvidence | None:
    """Extract an explicit ``after N seconds`` delay from coefficient-local text."""

    text = " ".join(str(component_fragment or "").split())
    match = _AFTER_SECONDS_RE.search(text)
    if match is None:
        return None
    return RotationHealerDelayedRuntimeEvidence(
        source_name=source_name,
        coefficient_number=coefficient_number,
        delay_seconds=float(match.group("delay")),
        provenance=(f"coefficient-local wording: {match.group(0)}",),
    )
