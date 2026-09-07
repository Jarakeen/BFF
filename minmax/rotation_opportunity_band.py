from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Hashable, Iterable, TypeVar


T = TypeVar("T")
S = TypeVar("S", bound=Hashable)


@dataclass(frozen=True)
class RotationOpportunitySample(Generic[T, S]):
    """One ordered projection sample and its discrete scheduling behavior."""

    value: T
    signature: S


@dataclass(frozen=True)
class RotationOpportunityBand(Generic[T, S]):
    """One contiguous run of samples with the same discrete behavior signature."""

    start_value: T
    end_value: T
    signature: S
    sample_count: int


def classify_rotation_opportunity_bands(
    samples: Iterable[RotationOpportunitySample[T, S]],
) -> tuple[RotationOpportunityBand[T, S], ...]:
    """Collapse adjacent equal signatures while preserving caller sample order.

    The caller owns both the sampled axis and the behavior signature. This helper
    deliberately does not merge separated ranges with the same signature because
    the intervening behavior is the useful evidence that a scheduling boundary was
    crossed.
    """

    ordered = tuple(samples)
    if not ordered:
        return ()

    bands: list[RotationOpportunityBand[T, S]] = []
    start = ordered[0]
    previous = ordered[0]
    count = 1

    for sample in ordered[1:]:
        if sample.signature == previous.signature:
            previous = sample
            count += 1
            continue
        bands.append(
            RotationOpportunityBand(
                start_value=start.value,
                end_value=previous.value,
                signature=start.signature,
                sample_count=count,
            )
        )
        start = sample
        previous = sample
        count = 1

    bands.append(
        RotationOpportunityBand(
            start_value=start.value,
            end_value=previous.value,
            signature=start.signature,
            sample_count=count,
        )
    )
    return tuple(bands)
