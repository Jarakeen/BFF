from __future__ import annotations

from dataclasses import dataclass

from minmax.damage_done import DamageDoneModifiers
from services.scribing_catalog import result_identity


@dataclass(frozen=True)
class RotationScribedSkillDamageSemantics:
    """Reviewed DD-facing semantics for one verified scribed result name."""

    result_name: str
    grimoire: str
    focus: str
    deals_direct_damage_on_activation: bool
    persistent_toggle: bool
    active_damage_done: DamageDoneModifiers
    source: str


class RotationScribedSkillDamageSemanticsService:
    """Resolve only explicitly reviewed scribed DD semantics.

    Result-name identity remains owned by ``services.scribing_catalog``. This service
    does not infer scripts from display text and does not claim Signature/Affix
    behavior. Unknown or unreviewed scribed results return ``None`` and remain
    fail-closed in their ordinary canonical skill path.
    """

    _MAGICAL_BANNER = RotationScribedSkillDamageSemantics(
        result_name="Magical Banner",
        grimoire="Banner Bearer",
        focus="Magic Damage",
        deals_direct_damage_on_activation=False,
        persistent_toggle=True,
        active_damage_done=DamageDoneModifiers(magic=0.06),
        source=(
            "reviewed Banner Bearer + Magic Damage focus semantics: activation is a "
            "persistent toggle and grants 6% Magical Damage Done while active"
        ),
    )

    def resolve(self, result_name: str) -> RotationScribedSkillDamageSemantics | None:
        identity = result_identity(result_name)
        if identity == (self._MAGICAL_BANNER.grimoire, self._MAGICAL_BANNER.focus):
            return self._MAGICAL_BANNER
        return None


__all__ = [
    "RotationScribedSkillDamageSemantics",
    "RotationScribedSkillDamageSemanticsService",
]
