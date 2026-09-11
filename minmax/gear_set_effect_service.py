from __future__ import annotations

from collections.abc import Mapping

from .effects import Effect
from .gear_set_activation_rules import active_item_set_bonus_counts
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
        condition_context: frozenset[str] | None = None,
    ) -> list[Effect]:
        """Resolve active effects for set-name -> equipped-piece counts.

        Unknown set names contribute no effects. This keeps the gear input layer
        tolerant of incomplete or synthetic build data while centralizing the
        name-to-ID lookup inside the set service.

        Canonical activation rules are applied before effect resolution. In
        particular, Torc of the Last Ayleid King suppresses every other item-set
        bonus while leaving the physical equipped-set counts unchanged elsewhere.

        ``condition_context`` is opt-in so legacy static callers retain their
        existing behavior. When supplied, conditional effects are returned only
        when their exact canonical condition marker is present. An explicit empty
        context therefore means that no conditional set effect is active.
        """

        effects: list[Effect] = []
        active_sets = active_item_set_bonus_counts(equipped_sets)
        for set_name, equipped_piece_count in active_sets.items():
            if equipped_piece_count <= 0:
                continue

            gear_set = self.repository.get_set(str(set_name))
            if gear_set is None:
                continue

            resolved = self.resolve_effects(
                gear_set.id,
                equipped_piece_count,
                use_max_value=use_max_value,
            )
            if condition_context is not None:
                resolved = [
                    effect
                    for effect in resolved
                    if not effect.condition or str(effect.condition).strip() in condition_context
                ]
            effects.extend(resolved)

        return effects
