from collections.abc import Iterable, Iterator

from .role import Role
from .support_effect import SupportEffect
from .support_effect_category import SupportEffectCategory
from .support_target_type import SupportTargetType


class SupportEffectRegistry:
    """
    A queryable container of SupportEffect instances.

    This is the foundation future code will use to answer questions like
    "what buffs does this build provide" or "which effects target enemies",
    without needing to know anything about how the effects were populated
    (fixtures today, ESO database / ESO Logs data later).
    """

    def __init__(self, effects: Iterable[SupportEffect] = ()) -> None:
        self._effects: list[SupportEffect] = list(effects)

    def __len__(self) -> int:
        return len(self._effects)

    def __iter__(self) -> Iterator[SupportEffect]:
        return iter(self._effects)

    def add(self, effect: SupportEffect) -> None:
        self._effects.append(effect)

    def all(self) -> tuple[SupportEffect, ...]:
        return tuple(self._effects)

    def for_source(self, source: str) -> tuple[SupportEffect, ...]:
        """What support effects does this source (build/player) provide?"""
        return tuple(
            effect
            for effect in self._effects
            if effect.source == source
        )

    def by_category(
        self,
        category: SupportEffectCategory,
    ) -> tuple[SupportEffect, ...]:
        return tuple(
            effect
            for effect in self._effects
            if effect.category == category
        )

    def buffs(self) -> tuple[SupportEffect, ...]:
        return self.by_category(SupportEffectCategory.BUFF)

    def debuffs(self) -> tuple[SupportEffect, ...]:
        return self.by_category(SupportEffectCategory.DEBUFF)

    def statuses(self) -> tuple[SupportEffect, ...]:
        return self.by_category(SupportEffectCategory.STATUS)

    def targeting(
        self,
        target_type: SupportTargetType,
    ) -> tuple[SupportEffect, ...]:
        """Which effects land on a given target type (self/ally/group/enemy)?"""
        return tuple(
            effect
            for effect in self._effects
            if effect.target_type == target_type
        )

    def targeting_enemies(self) -> tuple[SupportEffect, ...]:
        return self.targeting(SupportTargetType.ENEMY)

    def targeting_allies(self) -> tuple[SupportEffect, ...]:
        """Effects that reach other players: allies or the whole group."""
        return tuple(
            effect
            for effect in self._effects
            if effect.target_type
            in (SupportTargetType.ALLY, SupportTargetType.GROUP)
        )

    def for_role(self, role: Role) -> tuple[SupportEffect, ...]:
        """Which effects are relevant to a given role (DD/healer/tank)?"""
        return tuple(
            effect
            for effect in self._effects
            if role in effect.role_relevance
        )

    def contributing_to_group(self) -> tuple[SupportEffect, ...]:
        """Effects that at least have a chance to matter beyond their source."""
        return tuple(
            effect
            for effect in self._effects
            if effect.contributes_to_group()
        )
