from __future__ import annotations

"""Objective-aware finite armor-glyph states for Extreme resource records.

This layer owns no glyph arithmetic.  It asks the canonical armor glyph repository
which stat each supported armor glyph changes, keeps only glyph identities that can
affect the requested resource objective, and materializes those identities onto a
PlayerBuild.  Slot scaling and Infused amplification remain owned by
``GearStatInputResolver`` when the completed build is canonically scored.
"""

from dataclasses import dataclass
from itertools import product
from pathlib import Path

from minmax.armor_glyph_repository import ArmorGlyphEffectRepository
from minmax.gear_stat_inputs import ARMOR_ENCHANT_TO_GLYPH
from minmax.stat_ids import StatId
from models.build_model import ARMOR_SLOTS, PlayerBuild


_OBJECTIVE_STATS = {
    "max_health": StatId.MAX_HEALTH,
    "max_magicka": StatId.MAX_MAGICKA,
    "max_stamina": StatId.MAX_STAMINA,
}

# ``ARMOR_ENCHANT_TO_GLYPH`` intentionally uses normalized lowercase keys for
# canonical lookup.  Extreme build state and UI-facing evidence keep the build
# model's canonical display labels instead of leaking those lookup keys.
_ENCHANT_DISPLAY_LABELS = {
    "max health": "Max Health",
    "max magicka": "Max Magicka",
    "max stamina": "Max Stamina",
    "prismatic defense": "Prismatic Defense",
}


@dataclass(frozen=True)
class ExtremeArmorGlyphChoice:
    enchant_label: str
    glyph_name: str
    affected_stats: tuple[str, ...]


@dataclass(frozen=True)
class ExtremeArmorGlyphState:
    objective_key: str
    enchants: tuple[tuple[str, str], ...]

    @property
    def identity(self) -> tuple[tuple[str, str], ...]:
        return self.enchants


@dataclass(frozen=True)
class ExtremeArmorGlyphStateCatalog:
    objective_key: str
    choices: tuple[ExtremeArmorGlyphChoice, ...]
    states: tuple[ExtremeArmorGlyphState, ...]
    pruned_irrelevant_glyphs: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        return bool(self.states) and not self.unresolved


class ExtremeArmorGlyphStateService:
    """Enumerate objective-relevant CP160 Truly Superb armor-glyph loadouts."""

    SUPPORTED_OBJECTIVES = tuple(_OBJECTIVE_STATS)

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        repository: ArmorGlyphEffectRepository | None = None,
    ) -> None:
        if repository is None and database_path is None:
            raise ValueError("database_path is required when no armor glyph repository is supplied")
        self.repository = repository or ArmorGlyphEffectRepository(database_path)  # type: ignore[arg-type]

    def build(self, objective_key: str) -> ExtremeArmorGlyphStateCatalog:
        key = str(objective_key or "").strip().casefold()
        target = _OBJECTIVE_STATS.get(key)
        if target is None:
            raise KeyError(f"unreviewed Extreme armor glyph objective: {objective_key!r}")

        unresolved: list[str] = []
        relevant: list[ExtremeArmorGlyphChoice] = []
        pruned: list[str] = []

        supported_glyph_names = {
            str(name).strip().casefold()
            for name in ARMOR_ENCHANT_TO_GLYPH.values()
            if str(name).strip()
        }
        try:
            repository_names = tuple(self.repository.list_names())
        except Exception as exc:
            repository_names = ()
            unresolved.append(f"Armor glyph catalog could not be enumerated: {exc}")

        for raw_name in repository_names:
            name = str(raw_name or "").strip()
            if name and name.casefold() not in supported_glyph_names:
                unresolved.append(
                    f"Canonical armor glyph is not covered by Extreme armor-glyph mapping: {name}"
                )

        for enchant_key, glyph_name in ARMOR_ENCHANT_TO_GLYPH.items():
            normalized_enchant_key = str(enchant_key or "").strip().casefold()
            enchant_label = _ENCHANT_DISPLAY_LABELS.get(normalized_enchant_key)
            if enchant_label is None:
                unresolved.append(
                    f"Armor enchant lookup key has no canonical display label: {enchant_key}"
                )
                continue

            try:
                effects = tuple(
                    self.repository.get_armor_glyph_effect_by_name(
                        glyph_name,
                        use_max_value=True,
                    )
                )
            except Exception as exc:
                unresolved.append(f"{glyph_name}: canonical armor glyph resolution failed: {exc}")
                continue

            if not effects:
                unresolved.append(f"{glyph_name}: no canonical armor glyph effects found")
                continue

            stats = tuple(
                sorted(
                    {
                        effect.stat.value
                        for effect in effects
                        if effect.stat is not None
                    }
                )
            )
            if not stats:
                unresolved.append(f"{glyph_name}: canonical armor glyph effects have no stat identity")
                continue

            choice = ExtremeArmorGlyphChoice(
                enchant_label=enchant_label,
                glyph_name=str(glyph_name),
                affected_stats=stats,
            )
            if any(effect.stat is target for effect in effects):
                relevant.append(choice)
            else:
                pruned.append(str(glyph_name))

        relevant.sort(key=lambda row: (row.enchant_label.casefold(), row.glyph_name.casefold()))

        # Empty enchant is legal and remains in the finite denominator.  We do not
        # declare it dominated here because later trait/glyph composition owns the
        # proof that an occupied enchant slot has no opportunity cost.
        labels = ("", *(row.enchant_label for row in relevant))
        states = tuple(
            ExtremeArmorGlyphState(
                objective_key=key,
                enchants=tuple(zip(ARMOR_SLOTS, values)),
            )
            for values in product(labels, repeat=len(ARMOR_SLOTS))
        )

        if not relevant:
            unresolved.append(f"No canonical armor glyph affects Extreme objective {key}")

        return ExtremeArmorGlyphStateCatalog(
            objective_key=key,
            choices=tuple(relevant),
            states=states,
            pruned_irrelevant_glyphs=tuple(sorted(set(pruned), key=str.casefold)),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )

    @staticmethod
    def materialize(build: PlayerBuild, state: ExtremeArmorGlyphState) -> PlayerBuild:
        candidate = PlayerBuild.from_dict(build.to_dict())
        seen: set[str] = set()
        for slot, enchant in state.enchants:
            if slot not in candidate.Armor:
                raise ValueError(f"unknown Extreme armor glyph slot: {slot!r}")
            if slot in seen:
                raise ValueError(f"duplicate Extreme armor glyph slot: {slot!r}")
            seen.add(slot)
            target = candidate.Armor[slot]
            target["Enchant"] = str(enchant or "").strip()
            target["Level"] = "CP160" if enchant else ""
            target["EnchantTier"] = "Truly Superb" if enchant else ""

        if seen != set(candidate.Armor):
            missing = ", ".join(sorted(set(candidate.Armor) - seen))
            raise ValueError(f"Extreme armor glyph state does not cover all armor slots: {missing}")
        return candidate
