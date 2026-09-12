from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from minmax.effects import EffectUnit
from minmax.item_base_stats import TWO_SLOT_WEAPON_TYPES
from minmax.rule_repository import RuleRepository
from models.build_model import GearSlot, PlayerBuild


@dataclass(frozen=True)
class RotationChargedStatusChanceSource:
    bar: str
    slot_name: str
    weapon_type: str
    bonus_percent: float
    source: str


@dataclass(frozen=True)
class RotationSavedBuildChargedStatusChanceResolution:
    sources: tuple[RotationChargedStatusChanceSource, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved

    def bonus_percent_for(self, bar: str) -> float:
        key = str(bar or "").strip().casefold()
        matches = tuple(source for source in self.sources if source.bar == key)
        if len(matches) > 1:
            raise ValueError(
                f"multiple Charged sources on {key} require verified stacking semantics"
            )
        return matches[0].bonus_percent if matches else 0.0


class RotationSavedBuildChargedStatusChanceService:
    """Resolve source-backed Charged magnitude without inventing proc consequences.

    The weapon-trait table owns the imported ``status_effect_chance`` percentage.
    This service binds that reviewed trait rule to the exact active weapon slot in a
    saved build. It deliberately stops before deciding which scheduled damage event
    can proc which status; that belongs to the status-effect runtime/consequence layer.

    Multiple Charged weapons on one bar fail closed until their stacking semantics are
    explicitly reviewed. A two-slot weapon uses the same 2x trait scaling already used
    by the canonical CP160 Gold item-stat path.
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        rule_repository: RuleRepository | None = None,
    ) -> None:
        database = Path(database_path) if database_path is not None else get_data_dir() / "eso.db"
        self.rule_repository = rule_repository or RuleRepository(database)

    def _canonical_rule(self) -> tuple[float | None, str | None, tuple[str, ...]]:
        rules = tuple(
            rule
            for rule in self.rule_repository.get_weapon_trait_rules("Charged")
            if str(rule.rule_type or "").strip().casefold() == "status_effect_chance"
        )
        if len(rules) != 1:
            return None, None, (
                f"Charged status-effect chance expected one canonical rule, found {len(rules)}",
            )
        rule = rules[0]
        if rule.unit is not EffectUnit.PERCENT:
            return None, None, (
                f"Charged status-effect chance has unsupported unit: {rule.unit.value}",
            )
        value = float(rule.value)
        if value < 0.0:
            return None, None, ("Charged status-effect chance cannot be negative",)
        return value, str(rule.source or "Charged"), ()

    @staticmethod
    def _equipped_charged_slots(
        build: PlayerBuild,
        bar: str,
    ) -> tuple[tuple[str, GearSlot], ...]:
        key = str(bar or "").strip().casefold()
        main, offhand = build.active_weapon_slots(key)
        bar_label = "Front Bar" if key == "front" else "Back Bar"
        rows: list[tuple[str, GearSlot]] = []
        if str(main.Trait or "").strip().casefold() == "charged":
            rows.append((bar_label, main))
        if not offhand.is_empty and str(offhand.Trait or "").strip().casefold() == "charged":
            rows.append((f"{bar_label} Off Hand", offhand))
        return tuple(rows)

    def resolve(
        self,
        build: PlayerBuild,
        *,
        bars: tuple[str, ...] = ("front", "back"),
    ) -> RotationSavedBuildChargedStatusChanceResolution:
        normalized_bars: list[str] = []
        seen_bars: set[str] = set()
        unresolved: list[str] = []
        slots_by_bar: dict[str, tuple[tuple[str, GearSlot], ...]] = {}
        for raw_bar in bars:
            bar = str(raw_bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                unresolved.append(f"Charged status-effect chance received invalid bar: {raw_bar!r}")
                continue
            if bar in seen_bars:
                continue
            seen_bars.add(bar)
            normalized_bars.append(bar)
            slots_by_bar[bar] = self._equipped_charged_slots(build, bar)

        if unresolved:
            return RotationSavedBuildChargedStatusChanceResolution(
                unresolved=tuple(dict.fromkeys(unresolved))
            )
        if not any(slots_by_bar.values()):
            return RotationSavedBuildChargedStatusChanceResolution()

        value, rule_source, rule_unresolved = self._canonical_rule()
        if rule_unresolved:
            return RotationSavedBuildChargedStatusChanceResolution(unresolved=rule_unresolved)
        assert value is not None and rule_source is not None

        sources: list[RotationChargedStatusChanceSource] = []
        for bar in normalized_bars:
            charged_slots = slots_by_bar[bar]
            if len(charged_slots) > 1:
                unresolved.append(
                    f"{bar} bar has multiple Charged weapons; stacking semantics are not yet reviewed"
                )
                continue
            if not charged_slots:
                continue

            slot_name, slot = charged_slots[0]
            level = str(slot.Level or "").strip().casefold()
            quality = str(slot.Quality or "").strip().casefold()
            if level != "cp160" or quality != "gold":
                unresolved.append(
                    f"{slot_name} Charged magnitude requires CP160 Gold evidence "
                    f"({slot.Level or 'level unset'}, {slot.Quality or 'quality unset'})"
                )
                continue

            weapon_type = str(slot.WeaponType or "").strip()
            if not weapon_type:
                unresolved.append(f"{slot_name} Charged weapon type is unresolved")
                continue
            multiplier = 2.0 if weapon_type in TWO_SLOT_WEAPON_TYPES else 1.0
            sources.append(
                RotationChargedStatusChanceSource(
                    bar=bar,
                    slot_name=slot_name,
                    weapon_type=weapon_type,
                    bonus_percent=value * multiplier,
                    source=rule_source,
                )
            )

        return RotationSavedBuildChargedStatusChanceResolution(
            sources=tuple(sources),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "RotationChargedStatusChanceSource",
    "RotationSavedBuildChargedStatusChanceResolution",
    "RotationSavedBuildChargedStatusChanceService",
]
