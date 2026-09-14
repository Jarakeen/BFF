from __future__ import annotations

"""Project canonical static glyph effects into Extreme objective units.

Armor and jewelry glyphs are deterministic equipment choices and are therefore
modeled here as static enchantment sources. Weapon enchantments are deliberately
excluded from this service because their value depends on proc/cooldown/combat
state and belongs in the runtime-proc layer.

An unmapped or non-additive relevant effect is never assigned zero. It remains
an explicit blocker so a generated lower bound cannot masquerade as complete.
"""

from dataclasses import dataclass

from minmax.armor_glyph_repository import ArmorGlyphEffectRepository
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.stat_ids import StatId


@dataclass(frozen=True)
class ExtremeEnchantmentObjectiveCandidate:
    enchantment_type: str
    glyph_name: str
    objective_key: str
    projected_delta: float | None
    source_effects: tuple[Effect, ...] = ()
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtremeJewelryEnchantmentLoadout:
    objective_key: str
    glyph_name: str
    slot_multipliers: tuple[float, float, float]
    projected_delta: float | None
    unresolved: tuple[str, ...] = ()


class ExtremeEnchantmentObjectiveService:
    """Enumerate canonical armor/jewelry glyph contributions."""

    REVIEWED_OBJECTIVES = (
        "critical_damage",
        "magicka_recovery",
        "stamina_recovery",
        "physical_resistance",
        "spell_resistance",
        "spell_damage",
        "weapon_damage",
        "spell_critical",
        "weapon_critical",
    )

    _STAT_BY_OBJECTIVE = {
        "magicka_recovery": StatId.MAGICKA_RECOVERY,
        "stamina_recovery": StatId.STAMINA_RECOVERY,
        "spell_damage": StatId.SPELL_DAMAGE,
        "weapon_damage": StatId.WEAPON_DAMAGE,
        "physical_resistance": StatId.PHYSICAL_RESISTANCE,
        "spell_resistance": StatId.SPELL_RESISTANCE,
        "critical_damage": StatId.CRITICAL_DAMAGE,
    }

    # Canonical jewelry semantic identities let objective searches prove that an
    # unmapped mechanic is irrelevant before forcing it through EffectMapper.
    # This is deliberately narrower than the engine StatId map: unsupported
    # relevant semantics still fail closed below.
    _JEWELRY_EFFECT_TYPES_BY_OBJECTIVE = {
        "magicka_recovery": frozenset({"magicka_recovery"}),
        "stamina_recovery": frozenset({"stamina_recovery"}),
        "physical_resistance": frozenset({"physical_resistance"}),
        "spell_resistance": frozenset({"spell_resistance"}),
        "spell_damage": frozenset({"spell_damage", "weapon_spell_damage"}),
        "weapon_damage": frozenset({"weapon_damage", "weapon_spell_damage"}),
        "critical_damage": frozenset({"critical_damage"}),
        "spell_critical": frozenset({"spell_critical", "critical_chance"}),
        "weapon_critical": frozenset({"weapon_critical", "critical_chance"}),
    }

    @classmethod
    def _objective(cls, objective_key: str) -> str:
        objective = str(objective_key).strip().casefold()
        if objective not in cls.REVIEWED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme enchantment objective: {objective_key!r}")
        return objective

    @staticmethod
    def _validate_multiplier(multiplier: float) -> None:
        if multiplier < 0.0:
            raise ValueError("enchantment multiplier must be non-negative")

    @classmethod
    def _project_effects(
        cls,
        *,
        glyph_name: str,
        objective_key: str,
        effects: tuple[Effect, ...],
        multiplier: float,
    ) -> tuple[float | None, tuple[str, ...]]:
        cls._validate_multiplier(multiplier)
        objective = cls._objective(objective_key)

        target_stat = cls._STAT_BY_OBJECTIVE.get(objective)
        if objective in {"spell_critical", "weapon_critical"}:
            target_stats = {StatId.CRITICAL_CHANCE, StatId.SPELL_CRITICAL, StatId.WEAPON_CRITICAL}
        elif target_stat is None:
            target_stats = set()
        else:
            target_stats = {target_stat}

        relevant = tuple(effect for effect in effects if effect.stat in target_stats)
        if not relevant:
            return 0.0, ()

        unresolved: list[str] = []
        delta = 0.0
        for effect in relevant:
            if effect.operation is not EffectOperation.ADD:
                if effect.operation is EffectOperation.ADD_PERCENT:
                    unresolved.append(
                        f"{glyph_name}: percent enchantment effect requires objective-specific stacking review "
                        f"(operation {effect.operation.value})"
                    )
                else:
                    unresolved.append(
                        f"{glyph_name}: relevant enchantment effect uses unsupported operation "
                        f"{effect.operation.value}; stacking review required"
                    )
                continue
            if effect.unit is EffectUnit.PERCENT:
                unresolved.append(
                    f"{glyph_name}: percent enchantment effect requires objective-specific stacking review"
                )
                continue
            delta += float(effect.value) * float(multiplier)

        if unresolved:
            return None, tuple(unresolved)
        return float(delta), ()

    @classmethod
    def jewelry_candidate(
        cls,
        repository: JewelryGlyphEffectRepository,
        glyph_name: str,
        objective_key: str,
        *,
        multiplier: float = 1.0,
    ) -> ExtremeEnchantmentObjectiveCandidate:
        cls._validate_multiplier(multiplier)
        objective = cls._objective(objective_key)

        semantic_loader = getattr(repository, "get_jewelry_glyph_effect_types_by_name", None)
        if callable(semantic_loader):
            semantic_types = frozenset(
                str(value or "").strip().casefold()
                for value in semantic_loader(glyph_name)
                if str(value or "").strip()
            )
            target_types = cls._JEWELRY_EFFECT_TYPES_BY_OBJECTIVE.get(objective, frozenset())
            if semantic_types and semantic_types.isdisjoint(target_types):
                return ExtremeEnchantmentObjectiveCandidate(
                    enchantment_type="jewelry",
                    glyph_name=str(glyph_name),
                    objective_key=objective,
                    projected_delta=0.0,
                )

        try:
            effects = tuple(repository.get_jewelry_glyph_effect_by_name(glyph_name, use_max_value=True))
        except ValueError as exc:
            # If semantic review says the glyph could affect this objective, an
            # unmapped engine mechanic is a proof blocker rather than a crash or
            # an invented zero. Irrelevant semantics were returned above.
            return ExtremeEnchantmentObjectiveCandidate(
                enchantment_type="jewelry",
                glyph_name=str(glyph_name),
                objective_key=objective,
                projected_delta=None,
                unresolved=(f"{glyph_name}: {exc}",),
            )

        delta, unresolved = cls._project_effects(
            glyph_name=glyph_name,
            objective_key=objective,
            effects=effects,
            multiplier=multiplier,
        )
        return ExtremeEnchantmentObjectiveCandidate(
            enchantment_type="jewelry",
            glyph_name=str(glyph_name),
            objective_key=objective,
            projected_delta=delta,
            source_effects=effects,
            unresolved=unresolved,
        )

    @classmethod
    def armor_candidate(
        cls,
        repository: ArmorGlyphEffectRepository,
        glyph_name: str,
        objective_key: str,
        *,
        multiplier: float = 1.0,
    ) -> ExtremeEnchantmentObjectiveCandidate:
        effects = tuple(repository.get_armor_glyph_effect_by_name(glyph_name, use_max_value=True))
        delta, unresolved = cls._project_effects(
            glyph_name=glyph_name,
            objective_key=objective_key,
            effects=effects,
            multiplier=multiplier,
        )
        return ExtremeEnchantmentObjectiveCandidate(
            enchantment_type="armor",
            glyph_name=str(glyph_name),
            objective_key=str(objective_key).strip().casefold(),
            projected_delta=delta,
            source_effects=effects,
            unresolved=unresolved,
        )

    @classmethod
    def jewelry_candidates_for_objective(
        cls,
        repository: JewelryGlyphEffectRepository,
        objective_key: str,
        *,
        multiplier: float = 1.0,
    ) -> tuple[ExtremeEnchantmentObjectiveCandidate, ...]:
        rows = tuple(
            cls.jewelry_candidate(repository, name, objective_key, multiplier=multiplier)
            for name in repository.list_names()
        )
        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    row.projected_delta is None,
                    -(row.projected_delta or 0.0),
                    row.glyph_name.casefold(),
                ),
            )
        )

    @classmethod
    def armor_candidates_for_objective(
        cls,
        repository: ArmorGlyphEffectRepository,
        objective_key: str,
        *,
        multiplier: float = 1.0,
    ) -> tuple[ExtremeEnchantmentObjectiveCandidate, ...]:
        rows = tuple(
            cls.armor_candidate(repository, name, objective_key, multiplier=multiplier)
            for name in repository.list_names()
        )
        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    row.projected_delta is None,
                    -(row.projected_delta or 0.0),
                    row.glyph_name.casefold(),
                ),
            )
        )

    @classmethod
    def best_jewelry_for_objective(
        cls,
        repository: JewelryGlyphEffectRepository,
        objective_key: str,
        *,
        multiplier: float = 1.0,
    ) -> ExtremeEnchantmentObjectiveCandidate | None:
        return next(
            (
                row
                for row in cls.jewelry_candidates_for_objective(
                    repository,
                    objective_key,
                    multiplier=multiplier,
                )
                if row.projected_delta is not None
            ),
            None,
        )

    @classmethod
    def best_three_jewelry_loadout(
        cls,
        repository: JewelryGlyphEffectRepository,
        objective_key: str,
        *,
        slot_multipliers: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> ExtremeJewelryEnchantmentLoadout | None:
        if len(slot_multipliers) != 3 or any(float(value) < 0.0 for value in slot_multipliers):
            raise ValueError("jewelry enchantment loadout requires three non-negative slot multipliers")

        names = repository.list_names()
        best: ExtremeJewelryEnchantmentLoadout | None = None
        for name in names:
            slot_rows = tuple(
                cls.jewelry_candidate(repository, name, objective_key, multiplier=float(multiplier))
                for multiplier in slot_multipliers
            )
            unresolved = tuple(item for row in slot_rows for item in row.unresolved)
            if unresolved or any(row.projected_delta is None for row in slot_rows):
                candidate = ExtremeJewelryEnchantmentLoadout(
                    objective_key=str(objective_key).strip().casefold(),
                    glyph_name=name,
                    slot_multipliers=tuple(float(value) for value in slot_multipliers),
                    projected_delta=None,
                    unresolved=unresolved,
                )
            else:
                candidate = ExtremeJewelryEnchantmentLoadout(
                    objective_key=str(objective_key).strip().casefold(),
                    glyph_name=name,
                    slot_multipliers=tuple(float(value) for value in slot_multipliers),
                    projected_delta=sum(float(row.projected_delta or 0.0) for row in slot_rows),
                )
            if candidate.projected_delta is None:
                continue
            if best is None or candidate.projected_delta > float(best.projected_delta or 0.0):
                best = candidate
        return best
