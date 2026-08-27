from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .support_effect import SupportEffect
from .support_effect_category import SupportEffectCategory
from .support_effect_registry import SupportEffectRegistry
from .support_stacking import StackingBehavior
from .support_target_type import SupportTargetType


@dataclass(frozen=True)
class EffectEvidence:
    """One resolved provider of a logical effect."""

    name: str
    source: str
    category: SupportEffectCategory
    target_type: SupportTargetType
    magnitude: float
    unit: object
    duration: float | None
    uptime: float
    conditions: tuple[str, ...]
    trigger: object | None
    stacking: StackingBehavior
    exclusivity_group: str | None
    scaling: str | None
    target_count: int | None
    range: float | None
    damage_amplification: float | None
    resistance_reduction: float | None
    penetration: float | None
    resource_type: str | None
    resource_value: float | None

    @property
    def conditional(self) -> bool:
        return bool(self.conditions or self.trigger is not None)

    @classmethod
    def from_effect(cls, effect: SupportEffect) -> "EffectEvidence":
        return cls(
            name=effect.name,
            source=effect.source,
            category=effect.category,
            target_type=effect.target_type,
            magnitude=effect.magnitude,
            unit=effect.unit,
            duration=effect.duration,
            uptime=effect.uptime,
            conditions=effect.conditions,
            trigger=effect.trigger,
            stacking=effect.stacking,
            exclusivity_group=effect.exclusivity_group,
            scaling=effect.scaling,
            target_count=effect.target_count,
            range=effect.range,
            damage_amplification=effect.damage_amplification,
            resistance_reduction=effect.resistance_reduction,
            penetration=effect.penetration,
            resource_type=effect.resource_type,
            resource_value=effect.resource_value,
        )


@dataclass(frozen=True)
class EffectCoverage:
    """Normalized coverage for one logical effect identity."""

    name: str
    category: SupportEffectCategory
    covered: bool
    conditional: bool
    redundant: bool
    providers: tuple[EffectEvidence, ...]
    target_types: tuple[SupportTargetType, ...]
    max_magnitude: float | None
    max_duration: float | None
    max_uptime: float

    @property
    def source_names(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(provider.source for provider in self.providers))


@dataclass(frozen=True)
class EffectCoverageReport:
    """Build-level effect coverage, preserving provider evidence."""

    effects: tuple[EffectCoverage, ...]

    @property
    def covered(self) -> tuple[EffectCoverage, ...]:
        return tuple(effect for effect in self.effects if effect.covered)

    @property
    def conditional(self) -> tuple[EffectCoverage, ...]:
        return tuple(effect for effect in self.effects if effect.conditional)

    @property
    def redundant(self) -> tuple[EffectCoverage, ...]:
        return tuple(effect for effect in self.effects if effect.redundant)

    def by_name(self, name: str) -> EffectCoverage | None:
        key = name.strip().casefold()
        return next((effect for effect in self.effects if effect.name.casefold() == key), None)

    def missing_from(self, effect_names: Iterable[str]) -> tuple[str, ...]:
        """Return requested logical effects not provided by the build."""
        known = {effect.name.casefold() for effect in self.covered}
        return tuple(name for name in effect_names if name.casefold() not in known)


def analyze_effect_coverage(
    effects: Iterable[SupportEffect] | SupportEffectRegistry,
) -> EffectCoverageReport:
    """Normalize resolved build effects into coverage/redundancy evidence.

    Effect identity comes exclusively from ``SupportEffect.name``. Providers
    are never merged, so the report can explain exactly which skill, set,
    mythic, weapon, passive, or other source supplied an effect.

    This function deliberately does not contain ESO effect-name dictionaries
    or rules. It analyzes whatever the existing effect-resolution layer gives
    it.
    """
    source = effects.all() if isinstance(effects, SupportEffectRegistry) else tuple(effects)
    grouped: dict[str, list[SupportEffect]] = defaultdict(list)
    for effect in source:
        grouped[effect.name.casefold()].append(effect)

    reports: list[EffectCoverage] = []
    for logical_name, providers in grouped.items():
        evidence = tuple(EffectEvidence.from_effect(provider) for provider in providers)
        active = tuple(provider for provider in evidence if provider.uptime > 0.0)
        conditional = any(provider.conditional for provider in active)
        target_types = tuple(dict.fromkeys(provider.target_type for provider in active))
        magnitudes = [provider.magnitude for provider in active]
        durations = [provider.duration for provider in active if provider.duration is not None]
        uptimes = [provider.uptime for provider in active]

        # Multiple providers of the same logical effect are potential
        # redundancy, but only when their stacking/exclusivity semantics say
        # that the additional provider cannot combine meaningfully.
        redundant = _is_redundant(active)
        category = _dominant_category(active or evidence)

        reports.append(
            EffectCoverage(
                name=_display_name(logical_name, evidence),
                category=category,
                covered=bool(active),
                conditional=conditional,
                redundant=redundant,
                providers=evidence,
                target_types=target_types,
                max_magnitude=max(magnitudes) if magnitudes else None,
                max_duration=max(durations) if durations else None,
                max_uptime=max(uptimes) if uptimes else 0.0,
            )
        )

    reports.sort(key=lambda effect: effect.name.casefold())
    return EffectCoverageReport(tuple(reports))


def _is_redundant(providers: tuple[EffectEvidence, ...]) -> bool:
    if len(providers) < 2:
        return False

    groups = {provider.exclusivity_group for provider in providers if provider.exclusivity_group}
    if groups:
        return True

    behaviors = {provider.stacking for provider in providers}
    return behaviors != {StackingBehavior.STACKS}


def _dominant_category(providers: tuple[EffectEvidence, ...]) -> SupportEffectCategory:
    for category in (
        SupportEffectCategory.BUFF,
        SupportEffectCategory.DEBUFF,
        SupportEffectCategory.STATUS,
        SupportEffectCategory.OTHER,
    ):
        if any(provider.category == category for provider in providers):
            return category
    return SupportEffectCategory.OTHER


def _display_name(logical_name: str, providers: tuple[EffectEvidence, ...]) -> str:
    """Prefer a source's display spelling while keeping logical identity stable."""
    for provider in providers:
        if provider.name and provider.name != logical_name:
            return provider.name
    return logical_name
