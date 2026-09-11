from __future__ import annotations

"""Joint proof-safe armor trait + glyph states for Extreme max-resource records.

For max Health/Magicka/Stamina, the relevant armor-trait tradeoff is between
Divines (which can amplify the matching Mundus outside this layer) and Infused
(which amplifies the equipped armor glyph). This service keeps that interaction
joint without duplicating final stat arithmetic: it uses the canonical armor glyph
repository and ``GearStatInputResolver`` slot/Infused multipliers to reduce the
finite armor source family to the strongest concrete witness for each possible
Divines count. Final scoring still runs through the canonical build pipeline.

Armor weight is intentionally untouched here. Weight-dependent passives and
Undaunted-style interactions remain separate denominator work.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.armor_glyph_repository import ArmorGlyphEffectRepository
from minmax.effects import EffectOperation
from minmax.gear_stat_inputs import ARMOR_ENCHANT_TO_GLYPH, GearStatInputResolver
from minmax.stat_ids import StatId
from models.build_model import ARMOR_SLOTS, PlayerBuild
from services.extreme_armor_glyph_state_service import ExtremeArmorGlyphStateService


_OBJECTIVE_STATS = {
    "max_health": StatId.MAX_HEALTH,
    "max_magicka": StatId.MAX_MAGICKA,
    "max_stamina": StatId.MAX_STAMINA,
}


@dataclass(frozen=True)
class ExtremeArmorResourceTraitGlyphPieceChoice:
    slot: str
    trait: str
    enchant: str
    direct_delta: float


@dataclass(frozen=True)
class ExtremeArmorResourceTraitGlyphState:
    objective_key: str
    pieces: tuple[ExtremeArmorResourceTraitGlyphPieceChoice, ...]
    direct_glyph_delta: float

    @property
    def divines_count(self) -> int:
        return sum(1 for piece in self.pieces if piece.trait == "Divines")

    @property
    def infused_count(self) -> int:
        return sum(1 for piece in self.pieces if piece.trait == "Infused")

    @property
    def identity(self) -> tuple[tuple[str, str, str], ...]:
        return tuple((piece.slot, piece.trait, piece.enchant) for piece in self.pieces)


@dataclass(frozen=True)
class ExtremeArmorResourceTraitGlyphStateCatalog:
    objective_key: str
    states: tuple[ExtremeArmorResourceTraitGlyphState, ...]
    glyph_choices_reviewed: int
    raw_piece_choices_reviewed: int
    dominated_states_pruned: int
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        return bool(self.states) and not self.unresolved


@dataclass(frozen=True)
class _Partial:
    pieces: tuple[ExtremeArmorResourceTraitGlyphPieceChoice, ...]
    direct_delta: float


class ExtremeArmorResourceTraitGlyphStateService:
    """Reduce joint Divines/Infused + armor-glyph states by Divines count."""

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

    def _base_value(self, glyph_name: str, target: StatId, unresolved: list[str]) -> float | None:
        try:
            effects = tuple(
                self.repository.get_armor_glyph_effect_by_name(
                    glyph_name,
                    use_max_value=True,
                )
            )
        except Exception as exc:
            unresolved.append(f"{glyph_name}: canonical armor glyph resolution failed: {exc}")
            return None

        matching = [effect for effect in effects if effect.stat is target]
        if not matching:
            unresolved.append(f"{glyph_name}: no canonical {target.value} effect found")
            return None
        if any(effect.operation is not EffectOperation.ADD for effect in matching):
            unresolved.append(
                f"{glyph_name}: unsupported non-additive {target.value} armor glyph effect"
            )
            return None
        return sum(float(effect.value) for effect in matching)

    @staticmethod
    def _multiplier(slot: str, trait: str, unresolved: list[str]) -> float:
        entry = {"Trait": trait, "Quality": "Gold"}
        multiplier, _ = GearStatInputResolver._armor_glyph_multiplier(slot, entry, unresolved)
        return float(multiplier)

    def build(self, objective_key: str) -> ExtremeArmorResourceTraitGlyphStateCatalog:
        key = str(objective_key or "").strip().casefold()
        target = _OBJECTIVE_STATS.get(key)
        if target is None:
            raise KeyError(f"unreviewed Extreme armor resource trait/glyph objective: {objective_key!r}")

        glyph_catalog = ExtremeArmorGlyphStateService(repository=self.repository).build(key)
        unresolved = list(glyph_catalog.unresolved)

        glyph_values: list[tuple[str, float]] = []
        for choice in glyph_catalog.choices:
            value = self._base_value(choice.glyph_name, target, unresolved)
            if value is not None and value > 0.0:
                glyph_values.append((choice.enchant_label, float(value)))
            elif value is not None:
                unresolved.append(
                    f"{choice.glyph_name}: non-positive {target.value} value cannot prove dominance"
                )

        # DP invariant: later interaction with Mundus depends on armor state only
        # through Divines count. For a fixed Divines count, the larger flat glyph
        # contribution is therefore never worse in the canonical max-resource
        # pipeline. Keep one deterministic concrete witness per count.
        states: dict[int, _Partial] = {0: _Partial((), 0.0)}
        raw_piece_choices_reviewed = 0
        total_generated = 0

        for slot in ARMOR_SLOTS:
            piece_choices: list[ExtremeArmorResourceTraitGlyphPieceChoice] = [
                # Empty + Divines is the only no-glyph state needed: empty/None
                # and empty/Infused cannot improve this objective, while Divines
                # preserves or improves every matching-Mundus continuation.
                ExtremeArmorResourceTraitGlyphPieceChoice(
                    slot=slot,
                    trait="Divines",
                    enchant="",
                    direct_delta=0.0,
                )
            ]
            for enchant_label, base_value in glyph_values:
                for trait in ("Divines", "Infused"):
                    local_unresolved: list[str] = []
                    multiplier = self._multiplier(slot, trait, local_unresolved)
                    unresolved.extend(local_unresolved)
                    if multiplier <= 0.0:
                        continue
                    piece_choices.append(
                        ExtremeArmorResourceTraitGlyphPieceChoice(
                            slot=slot,
                            trait=trait,
                            enchant=enchant_label,
                            direct_delta=float(base_value) * multiplier,
                        )
                    )
            raw_piece_choices_reviewed += len(piece_choices)

            next_states: dict[int, _Partial] = {}
            for partial in states.values():
                for piece in piece_choices:
                    total_generated += 1
                    divines = sum(1 for row in partial.pieces if row.trait == "Divines")
                    divines += int(piece.trait == "Divines")
                    candidate = _Partial(
                        pieces=partial.pieces + (piece,),
                        direct_delta=partial.direct_delta + float(piece.direct_delta),
                    )
                    incumbent = next_states.get(divines)
                    if (
                        incumbent is None
                        or candidate.direct_delta > incumbent.direct_delta
                        or (
                            candidate.direct_delta == incumbent.direct_delta
                            and tuple((row.slot, row.trait, row.enchant) for row in candidate.pieces)
                            < tuple((row.slot, row.trait, row.enchant) for row in incumbent.pieces)
                        )
                    ):
                        next_states[divines] = candidate
            states = next_states

        final_states = tuple(
            ExtremeArmorResourceTraitGlyphState(
                objective_key=key,
                pieces=partial.pieces,
                direct_glyph_delta=float(partial.direct_delta),
            )
            for _, partial in sorted(states.items())
        )
        if not final_states:
            unresolved.append(f"No joint armor trait/glyph states were produced for {key}")

        return ExtremeArmorResourceTraitGlyphStateCatalog(
            objective_key=key,
            states=final_states,
            glyph_choices_reviewed=len(glyph_values),
            raw_piece_choices_reviewed=raw_piece_choices_reviewed,
            dominated_states_pruned=max(0, total_generated - len(final_states)),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )

    @staticmethod
    def materialize(
        build: PlayerBuild,
        state: ExtremeArmorResourceTraitGlyphState,
    ) -> PlayerBuild:
        candidate = PlayerBuild.from_dict(build.to_dict())
        seen: set[str] = set()
        for piece in state.pieces:
            slot = str(piece.slot or "").strip()
            if slot not in candidate.Armor:
                raise ValueError(f"unknown Extreme armor resource trait/glyph slot: {slot!r}")
            if slot in seen:
                raise ValueError(f"duplicate Extreme armor resource trait/glyph slot: {slot!r}")
            seen.add(slot)
            target = candidate.Armor[slot]
            target["Trait"] = str(piece.trait or "").strip()
            target["Quality"] = "Gold"
            target["Enchant"] = str(piece.enchant or "").strip()
            target["Level"] = "CP160" if piece.enchant else ""
            target["EnchantTier"] = "Truly Superb" if piece.enchant else ""

        if seen != set(candidate.Armor):
            missing = ", ".join(sorted(set(candidate.Armor) - seen))
            raise ValueError(
                f"Extreme armor resource trait/glyph state does not cover all armor slots: {missing}"
            )
        return candidate
