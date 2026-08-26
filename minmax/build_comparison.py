from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .character_build.character_build import CharacterBuild
from .character_build.capability_resolver import CharacterCapabilityResolver
from .character_build.effect_layer import BarId
from .character_build.effect_relationship import ConditionContext, EffectRelationship
from .character_build.passive_grant import PassiveGrant
from .support_effect import SupportEffect


@dataclass(frozen=True)
class BuildComparisonResult:
    """Mechanical capability delta between two resolved builds."""

    left_build_name: str
    right_build_name: str
    shared_effects: tuple[str, ...]
    added_effects: tuple[str, ...]
    removed_effects: tuple[str, ...]
    changed_effects: tuple[str, ...]

    @property
    def changed(self) -> bool:
        """Whether the two builds differ in capability output."""
        return bool(
            self.added_effects
            or self.removed_effects
            or self.changed_effects
        )

    @property
    def net_effect_delta(self) -> int:
        """Simple count of capability names gained minus lost."""
        return len(self.added_effects) - len(self.removed_effects)


class BuildComparison:
    """
    Compare the capabilities exposed by two real CharacterBuild objects.

    This deliberately compares resolved capability output, not raw UI fields.
    Two builds can therefore be considered equivalent even when they use
    different underlying sources that produce the same mechanical output.

    The comparison is descriptive only. It does not score DPS/HPS or decide
    which build is better for a particular encounter.
    """

    def __init__(
        self,
        resolver: CharacterCapabilityResolver | None = None,
    ) -> None:
        self.resolver = resolver or CharacterCapabilityResolver()

    def compare(
        self,
        left: CharacterBuild,
        left_active_bar: BarId,
        right: CharacterBuild,
        right_active_bar: BarId,
        *,
        left_passives: Iterable[PassiveGrant] = (),
        right_passives: Iterable[PassiveGrant] = (),
        relationships: Iterable[EffectRelationship] = (),
        left_condition_context: ConditionContext | None = None,
        right_condition_context: ConditionContext | None = None,
    ) -> BuildComparisonResult:
        """Resolve and compare both builds under their supplied contexts."""
        left_registry = self.resolver.resolve(
            left,
            left_active_bar,
            passives=left_passives,
            relationships=relationships,
            condition_context=left_condition_context,
        )
        right_registry = self.resolver.resolve(
            right,
            right_active_bar,
            passives=right_passives,
            relationships=relationships,
            condition_context=right_condition_context,
        )

        left_by_name = self._fingerprints_by_name(left_registry.all())
        right_by_name = self._fingerprints_by_name(right_registry.all())

        left_names = set(left_by_name)
        right_names = set(right_by_name)
        shared_names = left_names & right_names

        changed = tuple(
            sorted(
                name
                for name in shared_names
                if left_by_name[name] != right_by_name[name]
            )
        )

        return BuildComparisonResult(
            left_build_name=left.name,
            right_build_name=right.name,
            shared_effects=tuple(sorted(shared_names)),
            added_effects=tuple(sorted(right_names - left_names)),
            removed_effects=tuple(sorted(left_names - right_names)),
            changed_effects=changed,
        )

    @staticmethod
    def _fingerprints_by_name(
        effects: Iterable[SupportEffect],
    ) -> dict[str, tuple[tuple[object, ...], ...]]:
        grouped: dict[str, list[tuple[object, ...]]] = {}

        for effect in effects:
            fingerprint = (
                effect.source,
                effect.category,
                effect.effect_type,
                effect.target_type,
                effect.magnitude,
                effect.unit,
                effect.target_count,
                effect.range,
                effect.duration,
                effect.uptime,
                effect.stacking,
                effect.exclusivity_group,
                effect.conditions,
                effect.damage_amplification,
                effect.resistance_reduction,
                effect.penetration,
                effect.healing_contribution,
                effect.resource_type,
                effect.resource_value,
                effect.applies_status,
                effect.requires_status,
                tuple(sorted(role.value for role in effect.role_relevance)),
            )
            grouped.setdefault(effect.name, []).append(fingerprint)

        return {
            name: tuple(sorted(fingerprints, key=repr))
            for name, fingerprints in grouped.items()
        }
