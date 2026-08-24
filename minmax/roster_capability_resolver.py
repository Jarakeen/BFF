from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .character_build.capability_resolver import CharacterCapabilityResolver
from .character_build.character_build import CharacterBuild
from .character_build.effect_layer import BarId
from .role import Role
from .support_effect import SupportEffect


@dataclass(frozen=True)
class RosterCapabilityProvider:
    """
    One character providing one concrete SupportEffect.

    The effect itself remains unchanged. This wrapper adds the roster-level
    identity needed to answer "who provides this capability?"
    """

    character_name: str
    role: Role
    effect: SupportEffect


class RosterCapabilityResolver:
    """
    Resolve the capabilities provided by an entire roster.

    Effects are indexed by their stable logical name, but individual
    providers are never merged or discarded.

    This layer answers:
        "Who can provide what?"

    It does NOT answer:
        "Does the group need it?"
        "Is the coverage sufficient?"
        "Which provider should be assigned?"
        "What happened in the actual encounter?"

    Those belong to later layers.
    """

    def __init__(
        self,
        character_capability_resolver: CharacterCapabilityResolver | None = None,
    ) -> None:
        self.character_capability_resolver = (
            character_capability_resolver
            or CharacterCapabilityResolver()
        )

    def resolve(
        self,
        characters: Iterable[CharacterBuild],
        active_bars: dict[str, BarId],
    ) -> dict[str, tuple[RosterCapabilityProvider, ...]]:
        """
        Resolve every character and index their capabilities by effect name.

        `active_bars` maps CharacterBuild.name -> currently active BarId.

        Every provider remains independently represented. Identical effects
        from multiple characters are never merged or summed.
        """
        providers: defaultdict[
            str, list[RosterCapabilityProvider]
        ] = defaultdict(list)

        for character in characters:
            try:
                active_bar = active_bars[character.name]
            except KeyError as exc:
                raise ValueError(
                    f"No active bar supplied for character "
                    f"{character.name!r}."
                ) from exc

            registry = self.character_capability_resolver.resolve(
                character,
                active_bar,
            )

            for effect in registry.all():
                providers[effect.name].append(
                    RosterCapabilityProvider(
                        character_name=character.name,
                        role=character.role,
                        effect=effect,
                    )
                )

        return {
            effect_name: tuple(effect_providers)
            for effect_name, effect_providers in providers.items()
        }

    @staticmethod
    def providers_for(
        capabilities: dict[str, tuple[RosterCapabilityProvider, ...]],
        effect_name: str,
    ) -> tuple[RosterCapabilityProvider, ...]:
        """Return every roster member capable of providing an effect."""
        return capabilities.get(effect_name, ())