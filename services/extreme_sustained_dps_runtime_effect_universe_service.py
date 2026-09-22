from __future__ import annotations

"""Resolve the candidate-scoped runtime EffectVariant universe for Objective #32."""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant
from models.build_model import PlayerBuild


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeEffectUniverse:
    effects: tuple[EffectVariant, ...]
    excluded_plan_owned: tuple[EffectVariant, ...]
    boundaries: tuple[str, ...]
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSRuntimeEffectUniverseService:
    """Filter canonical saved-build capability evidence to runtime-triggered effects.

    The supplied capability service remains authoritative for gear/skill/potion
    EffectVariant discovery through its capability-only resolve_effect_variants seam.
    This adapter owns only Objective #32 relevance:
    triggered variants are runtime-state candidates; potion_use is excluded because
    finalized plan potion state is evaluated by the dedicated potion bridge.
    """

    def __init__(self, *, capability_service: object) -> None:
        if capability_service is None:
            raise ValueError(
                "runtime effect universe requires canonical saved-build capability service"
            )
        self.capability_service = capability_service

    @staticmethod
    def _dedupe(
        effects: tuple[EffectVariant, ...],
    ) -> tuple[EffectVariant, ...]:
        rows: list[EffectVariant] = []
        seen: set[tuple[object, ...]] = set()
        for effect in effects:
            key = (
                str(effect.name or "").strip().casefold(),
                str(effect.source or "").strip().casefold(),
                str(effect.trigger or "").strip().casefold(),
                str(effect.condition or "").strip().casefold(),
                None if effect.chance is None else float(effect.chance),
                None if effect.duration is None else float(effect.duration),
                None if effect.cooldown is None else float(effect.cooldown),
                None if effect.damage_amplification is None else float(effect.damage_amplification),
                None if effect.resistance_reduction is None else float(effect.resistance_reduction),
                None if effect.penetration is None else float(effect.penetration),
                str(getattr(effect.active_bar, "value", effect.active_bar) or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            rows.append(effect)
        return tuple(rows)

    def resolve(
        self,
        build: PlayerBuild,
    ) -> ExtremeSustainedDPSRuntimeEffectUniverse:
        resolution = self.capability_service.resolve_effect_variants(build)

        unresolved = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in tuple(getattr(resolution, "unresolved", ()) or ())
                if str(item).strip()
            )
        )
        boundaries = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in tuple(getattr(resolution, "boundaries", ()) or ())
                if str(item).strip()
            )
        )
        runtime_boundary_gaps = tuple(
            item
            for item in boundaries
            if (
                "detailed scripted effect conversion deferred" in item.casefold()
                or "effect semantics unavailable" in item.casefold()
                or "runtime effect" in item.casefold()
                and "deferred" in item.casefold()
            )
        )
        unresolved = tuple(
            dict.fromkeys(
                (
                    *unresolved,
                    *runtime_boundary_gaps,
                )
            )
        )

        triggered: list[EffectVariant] = []
        excluded: list[EffectVariant] = []
        for effect in tuple(getattr(resolution, "effects", ()) or ()):
            trigger = str(effect.trigger or "").strip()
            if not trigger:
                continue
            if trigger == "potion_use":
                excluded.append(effect)
                continue
            triggered.append(effect)

        runtime_effects = self._dedupe(tuple(triggered))
        excluded_plan_owned = self._dedupe(tuple(excluded))

        return ExtremeSustainedDPSRuntimeEffectUniverse(
            effects=runtime_effects,
            excluded_plan_owned=excluded_plan_owned,
            boundaries=boundaries,
            evidence=(
                f"Canonical capability effects inspected: {len(tuple(getattr(resolution, 'effects', ()) or ())) }",
                f"Runtime-triggered effects admitted: {len(runtime_effects)}",
                f"Plan-owned potion-triggered effects excluded: {len(excluded_plan_owned)}",
                "Triggerless variants remain owned by static/conditional build mechanics rather than runtime event enumeration",
            ),
            unresolved=unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeEffectUniverse",
    "ExtremeSustainedDPSRuntimeEffectUniverseService",
]
