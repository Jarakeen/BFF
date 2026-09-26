from __future__ import annotations

"""Resolve the candidate-scoped runtime EffectVariant universe for Objective #32."""

from dataclasses import dataclass

from minmax.character_build.effect_instance import EffectVariant
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_weapon_enchantment_activation_event_service import (
    WEAPON_ENCHANTMENT_ACTIVATION_TRIGGER,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeEffectUniverse:
    effects: tuple[EffectVariant, ...]
    excluded_plan_owned: tuple[EffectVariant, ...]
    boundaries: tuple[str, ...]
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]
    weapon_enchantment_sources: tuple[object, ...] = ()

    def __post_init__(self) -> None:
        for field in (
            "effects",
            "excluded_plan_owned",
            "boundaries",
            "evidence",
            "unresolved",
            "weapon_enchantment_sources",
        ):
            if not isinstance(getattr(self, field), tuple):
                raise TypeError(f"runtime effect universe {field} must be a tuple")
        if any(not isinstance(row, EffectVariant) for row in self.effects):
            raise TypeError("runtime effect universe effects must contain EffectVariant records")
        if any(
            not isinstance(row, EffectVariant)
            for row in self.excluded_plan_owned
        ):
            raise TypeError(
                "runtime effect universe excluded_plan_owned must contain EffectVariant records"
            )
        if set(self.effects).intersection(self.excluded_plan_owned):
            raise ValueError(
                "runtime effect universe effect cannot be both active and plan-owned excluded"
            )

        def _strings(values: tuple[str, ...]) -> tuple[str, ...]:
            return tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in values
                    if str(item).strip()
                )
            )

        object.__setattr__(self, "effects", tuple(self.effects))
        object.__setattr__(self, "excluded_plan_owned", tuple(self.excluded_plan_owned))
        object.__setattr__(self, "boundaries", _strings(self.boundaries))
        object.__setattr__(self, "evidence", _strings(self.evidence))
        object.__setattr__(self, "unresolved", _strings(self.unresolved))
        object.__setattr__(
            self,
            "weapon_enchantment_sources",
            tuple(self.weapon_enchantment_sources),
        )

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

    def __init__(
        self,
        *,
        capability_service: object,
        weapon_enchantment_runtime_source_service: object | None = None,
        weapon_enchantment_runtime_variant_service: object | None = None,
    ) -> None:
        if capability_service is None:
            raise ValueError(
                "runtime effect universe requires canonical saved-build capability service"
            )
        if (weapon_enchantment_runtime_source_service is None) != (
            weapon_enchantment_runtime_variant_service is None
        ):
            raise ValueError(
                "dedicated weapon-enchantment runtime universe requires both source and variant services"
            )
        self.capability_service = capability_service
        self.weapon_enchantment_runtime_source_service = weapon_enchantment_runtime_source_service
        self.weapon_enchantment_runtime_variant_service = weapon_enchantment_runtime_variant_service

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
                str(getattr(effect, "source_slot", "") or ""),
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
        for field in ("unresolved", "boundaries", "effects"):
            value = getattr(resolution, field, ())
            if not isinstance(value, tuple):
                raise TypeError(f"runtime capability resolution {field} must be a tuple")

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
        dedicated_weapon_runtime = self.weapon_enchantment_runtime_source_service is not None
        runtime_boundary_gaps = tuple(
            item
            for item in boundaries
            if (
                "detailed scripted effect conversion deferred" in item.casefold()
                or "effect semantics unavailable" in item.casefold()
                or (
                    "runtime effect" in item.casefold()
                    and "deferred" in item.casefold()
                    and not (
                        dedicated_weapon_runtime
                        and "weapon enchantment runtime effect timing deferred" in item.casefold()
                    )
                )
            )
        )

        weapon_sources: tuple[object, ...] = ()
        dedicated_weapon_effects: tuple[EffectVariant, ...] = ()
        dedicated_weapon_evidence: tuple[str, ...] = ()
        dedicated_weapon_unresolved: tuple[str, ...] = ()
        if dedicated_weapon_runtime:
            source_resolution = self.weapon_enchantment_runtime_source_service.resolve(build)
            for field in ("sources", "evidence", "unresolved"):
                value = getattr(source_resolution, field, ())
                if not isinstance(value, tuple):
                    raise TypeError(
                        f"weapon-enchantment runtime source resolution {field} must be a tuple"
                    )
            weapon_sources = source_resolution.sources
            variant_resolution = self.weapon_enchantment_runtime_variant_service.resolve(
                weapon_sources
            )
            for field in ("effects", "evidence", "unresolved"):
                value = getattr(variant_resolution, field, ())
                if not isinstance(value, tuple):
                    raise TypeError(
                        f"weapon-enchantment runtime variant resolution {field} must be a tuple"
                    )
            dedicated_weapon_effects = variant_resolution.effects
            dedicated_weapon_evidence = tuple(
                dict.fromkeys(
                    (
                        *tuple(getattr(source_resolution, "evidence", ()) or ()),
                        *tuple(getattr(variant_resolution, "evidence", ()) or ()),
                    )
                )
            )
            dedicated_weapon_unresolved = tuple(
                dict.fromkeys(
                    (
                        *tuple(getattr(source_resolution, "unresolved", ()) or ()),
                        *tuple(getattr(variant_resolution, "unresolved", ()) or ()),
                    )
                )
            )

        if dedicated_weapon_runtime and not weapon_sources:
            runtime_boundary_gaps = tuple(
                dict.fromkeys(
                    (
                        *runtime_boundary_gaps,
                        *(
                            item
                            for item in boundaries
                            if "weapon enchantment runtime effect timing deferred"
                            in item.casefold()
                        ),
                    )
                )
            )

        unresolved = tuple(
            dict.fromkeys(
                (
                    *unresolved,
                    *runtime_boundary_gaps,
                    *dedicated_weapon_unresolved,
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

        triggered.extend(dedicated_weapon_effects)
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
                "Weapon-enchantment variants remain distinct in the runtime universe; per-opportunity source/cooldown binding is owned by runtime scenario construction",
                *dedicated_weapon_evidence,
                (
                    f"Dedicated canonical weapon-enchantment runtime sources admitted: {len(weapon_sources)}"
                    if dedicated_weapon_runtime
                    else "Dedicated canonical weapon-enchantment runtime source projection was not supplied"
                ),
            ),
            unresolved=unresolved,
            weapon_enchantment_sources=weapon_sources,
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeEffectUniverse",
    "ExtremeSustainedDPSRuntimeEffectUniverseService",
]
