from __future__ import annotations

from collections.abc import Mapping

from .effects import Effect
from .gear_set_effect_resolver import GearSetEffectResolver
from .gear_set_repository import GearSetRepository


class GearSetEffectService:
    """Resolve the active, stat-resolvable effects contributed by a gear set."""

    def __init__(
        self,
        repository: GearSetRepository,
        resolver: GearSetEffectResolver | None = None,
    ):
        self.repository = repository
        self.resolver = resolver or GearSetEffectResolver()

    def resolve_effects(
        self,
        set_id: int,
        equipped_piece_count: int,
        *,
        use_max_value: bool = True,
    ) -> list[Effect]:
        """Resolve all active bonuses for an equipped gear set.

        Bonuses requiring more pieces than are equipped are ignored.
        Bonuses that the resolver does not understand contribute no effects.
        """

        if equipped_piece_count <= 0:
            return []

        bonuses = self.repository.get_bonuses(set_id)

        effects: list[Effect] = []

        gear_set = self.repository.get_set_by_id(set_id)
        set_name = gear_set.name if gear_set is not None else f"Set {set_id}"

        for bonus in bonuses:
            if bonus.piece_count > equipped_piece_count:
                continue

            effects.extend(
                self.resolver.resolve(
                    bonus,
                    use_max_value=use_max_value,
                    source=f"{set_name} ({bonus.piece_count})",
                )
            )

        return effects

    def active_static_effects(
        self,
        equipped_sets: Mapping[str, int],
        *,
        use_max_value: bool = True,
    ) -> list[Effect]:
        """Resolve active static effects for set-name -> equipped-piece counts.

        Unknown set names contribute no effects. This keeps the gear input layer
        tolerant of incomplete or synthetic build data while centralizing the
        name-to-ID lookup inside the set service.
        """

        effects: list[Effect] = []
        for set_name, equipped_piece_count in equipped_sets.items():
            if equipped_piece_count <= 0:
                continue

            gear_set = self.repository.get_set(str(set_name))
            if gear_set is None:
                continue

            effects.extend(
                self.resolve_effects(
                    gear_set.id,
                    equipped_piece_count,
                    use_max_value=use_max_value,
                )
            )

        return effects
