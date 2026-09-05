from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CompCompositionStyle(str, Enum):
    PROVEN = "proven"
    PERFORMANCE = "performance"
    EXPERIMENTAL = "experimental"
    OFF_META = "off_meta"


@dataclass(frozen=True)
class CompCompositionStylePolicy:
    style: CompCompositionStyle
    label: str
    description: str
    prefer_saved_builds: bool
    novelty_weight: float
    relevance_weight: float


_POLICIES = {
    CompCompositionStyle.PROVEN: CompCompositionStylePolicy(
        style=CompCompositionStyle.PROVEN,
        label="Proven / Standard",
        description=(
            "Prefer established saved builds and relevance after all hard raid requirements are satisfied."
        ),
        prefer_saved_builds=True,
        novelty_weight=0.0,
        relevance_weight=1.0,
    ),
    CompCompositionStyle.PERFORMANCE: CompCompositionStylePolicy(
        style=CompCompositionStyle.PERFORMANCE,
        label="Performance First",
        description=(
            "Prefer the strongest available modeled/relevance evidence after all hard raid requirements are satisfied."
        ),
        prefer_saved_builds=False,
        novelty_weight=0.0,
        relevance_weight=1.0,
    ),
    CompCompositionStyle.EXPERIMENTAL: CompCompositionStylePolicy(
        style=CompCompositionStyle.EXPERIMENTAL,
        label="Experimental",
        description=(
            "Prefer uncommon but evidence-backed options when they preserve every hard raid requirement."
        ),
        prefer_saved_builds=False,
        novelty_weight=0.75,
        relevance_weight=1.0,
    ),
    CompCompositionStyle.OFF_META: CompCompositionStylePolicy(
        style=CompCompositionStyle.OFF_META,
        label="Off-Meta Discovery",
        description=(
            "Actively surface unusual evidence-backed options while keeping required providers, build ingredients, chair fill, and mechanic obligations intact."
        ),
        prefer_saved_builds=False,
        novelty_weight=1.5,
        relevance_weight=0.75,
    ),
}


def composition_style_policy(
    value: CompCompositionStyle | str | None,
) -> CompCompositionStylePolicy:
    if value is None:
        style = CompCompositionStyle.PROVEN
    elif isinstance(value, CompCompositionStyle):
        style = value
    else:
        style = CompCompositionStyle(str(value))
    return _POLICIES[style]


def composition_style_options() -> tuple[CompCompositionStylePolicy, ...]:
    return tuple(_POLICIES[style] for style in CompCompositionStyle)
