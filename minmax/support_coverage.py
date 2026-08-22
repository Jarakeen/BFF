from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from .role import Role
from .support_effect import SupportEffect
from .support_effect_registry import SupportEffectRegistry
from .support_target_type import SupportTargetType


def _normalize(name: str) -> str:
    """
    Normalize a support-effect name into a comparison key.

    This is what makes "Major Breach" from Player A and "Major Breach"
    from Player B recognizable as the same logical effect, and what keeps
    "Chilled" and "Brittle" and plain "Frost" damage from ever being
    confused with each other - they simply normalize to different keys.
    """
    return name.strip().casefold()


@dataclass(frozen=True)
class EffectCoverage:
    """
    Every SupportEffect that shares one logical identity (name), together
    with who supplies each of them.

    This is how duplicate/overlapping coverage - e.g. two tanks both
    providing Major Breach - stays visible instead of collapsing into one
    anonymous effect. Both SupportEffect instances are retained; nothing
    here decides which provider is "better" or whether they stack - that
    is future optimizer/stacking-resolution logic and depends on each
    effect's own `stacking`/`exclusivity_group`.
    """

    name: str
    effects: tuple[SupportEffect, ...]

    @property
    def sources(self) -> tuple[str, ...]:
        return tuple(effect.source for effect in self.effects)

    @property
    def is_overlapping(self) -> bool:
        """More than one source currently supplies this logical effect."""
        return len(self.effects) > 1


class SupportCoverage:
    """
    The support coverage supplied by one or more SupportEffects, with
    player/build ownership preserved:

        Player Build -> SupportEffectRegistry -> SupportCoverage

    This wraps a SupportEffectRegistry rather than reimplementing its
    category/target/role filtering, and adds coverage-specific concerns
    on top of it: per-source ownership, duplicate/overlap detection
    across sources, and comparing supplied coverage against a list of
    required effect names.

    Nothing here calculates damage, healing, or real combat uptime from
    logs - it only reports the uptime/duration/stacking/exclusivity/role
    data already stored on each SupportEffect.
    """

    def __init__(self, registry: SupportEffectRegistry | None = None):
        self.registry = registry or SupportEffectRegistry()

    @classmethod
    def from_effects(
        cls,
        effects: Iterable[SupportEffect],
    ) -> "SupportCoverage":
        return cls(SupportEffectRegistry(effects))

    def __len__(self) -> int:
        return len(self.registry)

    def all(self) -> tuple[SupportEffect, ...]:
        return self.registry.all()

    # Category filtering - delegated to the registry.

    @property
    def buffs(self) -> tuple[SupportEffect, ...]:
        return self.registry.buffs()

    @property
    def debuffs(self) -> tuple[SupportEffect, ...]:
        return self.registry.debuffs()

    @property
    def statuses(self) -> tuple[SupportEffect, ...]:
        return self.registry.statuses()

    # Target filtering - delegated to the registry.

    def targeting_allies(self) -> tuple[SupportEffect, ...]:
        return self.registry.targeting_allies()

    def targeting_enemies(self) -> tuple[SupportEffect, ...]:
        return self.registry.targeting_enemies()

    def targeting_group(self) -> tuple[SupportEffect, ...]:
        return self.registry.targeting(SupportTargetType.GROUP)

    def for_role(self, role: Role) -> tuple[SupportEffect, ...]:
        return self.registry.for_role(role)

    def contributing_to_group(self) -> tuple[SupportEffect, ...]:
        return self.registry.contributing_to_group()

    # Ownership.

    def effects_for_source(self, source: str) -> tuple[SupportEffect, ...]:
        """Every support effect a specific player/build supplies."""
        return self.registry.for_source(source)

    def sources(self) -> tuple[str, ...]:
        """Every distinct player/build source represented in this coverage."""
        seen: dict[str, None] = {}
        for effect in self.registry:
            seen.setdefault(effect.source, None)
        return tuple(seen)

    # Logical identity / duplicates / overlap.

    def sources_for_effect(self, name: str) -> tuple[str, ...]:
        """Which sources currently supply a logical effect (matched by name)?"""
        identity = _normalize(name)
        return tuple(
            effect.source
            for effect in self.registry
            if _normalize(effect.name) == identity
        )

    def grouped_by_effect(self) -> tuple[EffectCoverage, ...]:
        """
        Group every supplied effect by logical identity (name), preserving
        every source that supplies it. This is the general-purpose view
        that both `overlapping()` and duplicate-detection are built on.
        """
        grouped: dict[str, list[SupportEffect]] = defaultdict(list)
        order: list[str] = []

        for effect in self.registry:
            identity = _normalize(effect.name)
            if identity not in grouped:
                order.append(identity)
            grouped[identity].append(effect)

        return tuple(
            EffectCoverage(
                name=grouped[identity][0].name,
                effects=tuple(grouped[identity]),
            )
            for identity in order
        )

    def overlapping(self) -> tuple[EffectCoverage, ...]:
        """Logical effects currently supplied by more than one source."""
        return tuple(
            group
            for group in self.grouped_by_effect()
            if group.is_overlapping
        )

    def missing_from(
        self,
        required_effect_names: Iterable[str],
    ) -> tuple[str, ...]:
        """
        Compare a list of required support-effect names against what this
        coverage currently supplies, and return the ones not currently
        covered by any source - preserving the original names/casing the
        caller passed in. Comparison is by logical effect identity (name,
        case-insensitive), not object identity.
        """
        supplied = {
            _normalize(effect.name) for effect in self.registry
        }

        return tuple(
            name
            for name in required_effect_names
            if _normalize(name) not in supplied
        )
