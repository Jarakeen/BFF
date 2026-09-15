from __future__ import annotations

"""Validate physical armor-weight legality for Extreme MOST Actual Heal builds.

Actual-heal gear builders materialize canonical set identity onto explicit armor
slots before whole-build scoring. Slot identity alone is not enough to prove a
wearable build: a named set piece may exist only in Light, Medium, Heavy, or a
specific subset of those weights.

This service reads canonical ``gear_set_piece.armor_type`` evidence and reports
that physical boundary without changing combat math. Unset armor slots may use
any of ESO's three armor weights. Named-set slots must have direct canonical
piece evidence for the exact slot and current weight.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from minmax.gear_set_repository import GearSetRepository
from models.build_model import ARMOR_SLOTS, PlayerBuild
from services.stickerbook_service import EQUIP_TYPES


_ARMOR_TYPE_LABELS = {
    1: "Light",
    2: "Medium",
    3: "Heavy",
}
_ALL_WEIGHTS = tuple(_ARMOR_TYPE_LABELS.values())


@dataclass(frozen=True)
class ExtremeActualHealArmorWeightSlotEvidence:
    slot: str
    set_name: str
    current_weight: str
    allowed_weights: tuple[str, ...]
    legal: bool
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtremeActualHealArmorWeightLegalityResult:
    slots: tuple[ExtremeActualHealArmorWeightSlotEvidence, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def physically_legal(self) -> bool:
        return bool(self.slots) and all(row.legal for row in self.slots) and not self.unresolved

    @property
    def legal_weight_options(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        return tuple((row.slot, row.allowed_weights) for row in self.slots)


class ExtremeActualHealArmorWeightLegalityService:
    """Resolve exact armor-slot weight options from canonical set-piece evidence."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        repository: GearSetRepository | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.repository = repository or GearSetRepository(self.database_path)
        self._equip_type_by_slot = {
            str(label).strip().casefold(): int(equip_type)
            for equip_type, label in EQUIP_TYPES.items()
            if str(label or "").strip()
        }

    def _set_for_name(self, set_name: str):
        direct = self.repository.get_set(set_name)
        if direct is not None:
            return direct
        wanted = str(set_name or "").strip().casefold()
        matches = tuple(
            row
            for row in self.repository.list_sets()
            if str(row.name or "").strip().casefold() == wanted
        )
        return matches[0] if len(matches) == 1 else None

    def _allowed_set_weights(
        self,
        *,
        set_id: int,
        slot: str,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        equip_type = self._equip_type_by_slot.get(str(slot).strip().casefold())
        if equip_type is None:
            return (), (f"Canonical equip_type is unavailable for armor slot: {slot}",)
        if not self.database_path.is_file():
            return (), (f"Armor-weight database missing: {self.database_path}",)

        try:
            connection = sqlite3.connect(
                f"file:{self.database_path.resolve()}?mode=ro",
                uri=True,
            )
        except sqlite3.Error as exc:
            return (), (f"Armor-weight database unreadable: {exc}",)

        with connection:
            rows = connection.execute(
                """
                SELECT DISTINCT COALESCE(armor_type, 0)
                FROM gear_set_piece
                WHERE set_id = ?
                  AND equip_type = ?
                  AND COALESCE(weapon_type, 0) = 0
                ORDER BY armor_type
                """,
                (int(set_id), int(equip_type)),
            ).fetchall()

        unresolved: list[str] = []
        weights: list[str] = []
        for (armor_type_raw,) in rows:
            armor_type = int(armor_type_raw or 0)
            label = _ARMOR_TYPE_LABELS.get(armor_type)
            if label is None:
                if armor_type > 0:
                    unresolved.append(
                        f"Set {set_id} slot {slot} uses unknown armor_type {armor_type}"
                    )
                continue
            if label not in weights:
                weights.append(label)
        return tuple(weights), tuple(dict.fromkeys(unresolved))

    def evaluate(self, build: PlayerBuild) -> ExtremeActualHealArmorWeightLegalityResult:
        rows: list[ExtremeActualHealArmorWeightSlotEvidence] = []
        unresolved: list[str] = []

        for slot in ARMOR_SLOTS:
            entry = build.Armor.get(slot)
            if entry is None:
                message = f"Build is missing canonical armor slot: {slot}"
                unresolved.append(message)
                rows.append(
                    ExtremeActualHealArmorWeightSlotEvidence(
                        slot=slot,
                        set_name="",
                        current_weight="",
                        allowed_weights=(),
                        legal=False,
                        unresolved=(message,),
                    )
                )
                continue

            set_name = str(entry.get("Set", "") or "").strip()
            current_weight = str(entry.get("Weight", "") or "").strip().title()
            slot_unresolved: list[str] = []

            if not set_name:
                allowed = _ALL_WEIGHTS
            else:
                gear_set = self._set_for_name(set_name)
                if gear_set is None:
                    allowed = ()
                    slot_unresolved.append(
                        f"Named armor set is not uniquely resolved canonically: {set_name!r}"
                    )
                else:
                    allowed, problems = self._allowed_set_weights(
                        set_id=int(gear_set.id),
                        slot=slot,
                    )
                    slot_unresolved.extend(problems)
                    if not allowed and not problems:
                        slot_unresolved.append(
                            f"Set {set_name!r} has no canonical armor-weight piece for slot {slot}"
                        )

            if current_weight not in _ALL_WEIGHTS:
                slot_unresolved.append(
                    f"Armor slot {slot} has no canonical Light/Medium/Heavy weight: {current_weight!r}"
                )

            legal = bool(
                current_weight in allowed
                and current_weight in _ALL_WEIGHTS
                and not slot_unresolved
            )
            row = ExtremeActualHealArmorWeightSlotEvidence(
                slot=slot,
                set_name=set_name,
                current_weight=current_weight,
                allowed_weights=tuple(allowed),
                legal=legal,
                unresolved=tuple(dict.fromkeys(slot_unresolved)),
            )
            rows.append(row)
            unresolved.extend(row.unresolved)
            if (
                set_name
                and current_weight in _ALL_WEIGHTS
                and allowed
                and current_weight not in allowed
            ):
                unresolved.append(
                    f"Illegal armor weight for {set_name!r} on {slot}: "
                    f"current={current_weight}; allowed={','.join(allowed)}"
                )

        return ExtremeActualHealArmorWeightLegalityResult(
            slots=tuple(rows),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeActualHealArmorWeightLegalityResult",
    "ExtremeActualHealArmorWeightLegalityService",
    "ExtremeActualHealArmorWeightSlotEvidence",
]
