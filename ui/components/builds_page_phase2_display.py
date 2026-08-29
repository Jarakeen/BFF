from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem

from minmax.gear_stat_inputs import GearStatInputResolver
from models.build_model import GearSlot, PlayerBuild
from ui.components.foundry_card import FoundryCard


_ONE_HANDED_TYPES = {"sword", "axe", "mace", "dagger"}


def _needs_explicit_offhand(main: GearSlot, offhand: GearSlot) -> bool:
    """Return whether the saved bar should expose a separate off-hand row.

    Legacy aggregate Dual Wield / One Hand and Shield saves intentionally remain
    one-row representations until the user edits them into explicit hands.
    Individual one-handed weapon types, however, require an off-hand entry.
    """

    if not offhand.is_empty:
        return True
    return str(main.WeaponType or "").strip().casefold() in _ONE_HANDED_TYPES


def weapon_rows(build: PlayerBuild) -> list[tuple[str, GearSlot]]:
    rows: list[tuple[str, GearSlot]] = []
    for bar_name, main, offhand in (
        ("Front", build.FrontBarWeapon, build.FrontBarOffHand),
        ("Back", build.BackBarWeapon, build.BackBarOffHand),
    ):
        rows.append((f"{bar_name} Main Hand", main))
        if _needs_explicit_offhand(main, offhand):
            rows.append((f"{bar_name} Off Hand", offhand))
    return rows


def readiness_gear(build: PlayerBuild) -> list:
    return list(build.Armor.values()) + [
        build.Necklace,
        build.Ring1,
        build.Ring2,
        *(slot for _label, slot in weapon_rows(build)),
    ]


def _gear_filled(slot) -> bool:
    if hasattr(slot, "Set"):
        return bool(str(slot.Set or "").strip())
    return bool(str(slot.get("Set", "") or "").strip())


def _gear_trait(slot) -> bool:
    if hasattr(slot, "Trait"):
        return bool(str(slot.Trait or "").strip())
    return bool(str(slot.get("Trait", "") or "").strip())


def build_status_rows(build: PlayerBuild) -> list[tuple[str, str]]:
    gear = readiness_gear(build)
    gear_total = len(gear) or 1
    gear_complete = sum(1 for slot in gear if _gear_filled(slot))
    traits = sum(1 for slot in gear if _gear_trait(slot))
    skills = sum(1 for skill in (build.FrontBarSkills + build.BackBarSkills) if str(skill).strip())
    cp = len([entry for entry in build.ChampionPoints if str(entry.Name or "").strip()])
    readiness = round(
        ((gear_complete / gear_total) + (traits / gear_total) + (skills / 12) + (1 if cp else 0))
        / 4
        * 100
    )
    return [
        ("Readiness", f"{readiness}%"),
        ("Gear Complete", f"{gear_complete}/{gear_total}"),
        ("Traits", f"{traits}/{gear_total}"),
        ("Champion Points", "Configured" if cp else "Missing"),
        ("Skills", f"{skills}/12"),
    ]


def gear_card(_page, build: PlayerBuild):
    card = FoundryCard("Gear")
    table = QTableWidget(0, 5)
    table.setHorizontalHeaderLabels(["Slot", "Set", "Trait", "Enchant", "Status"])
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
    table.setMinimumHeight(330)
    table.horizontalHeader().setStretchLastSection(True)

    rows = list(build.Armor.items()) + [
        ("Neck", build.Necklace),
        ("Ring 1", build.Ring1),
        ("Ring 2", build.Ring2),
        *weapon_rows(build),
    ]
    for slot, value in rows:
        if hasattr(value, "Set"):
            set_name, trait, enchant = value.Set, value.Trait, value.Enchant
        else:
            set_name = value.get("Set", "")
            trait = value.get("Trait", "")
            enchant = value.get("Enchant", "")
        row = table.rowCount()
        table.insertRow(row)
        status = "✓ Complete" if set_name and trait else ("⚠ Partial" if set_name else "Missing")
        for column, text in enumerate([slot, set_name or "—", trait or "—", enchant or "—", status]):
            table.setItem(row, column, QTableWidgetItem(str(text)))

    card.addWidget(table)
    return card


def _add_set_counts(card: FoundryCard, title: str, counts) -> None:
    card.addWidget(QLabel(title))
    if not counts:
        card.addWidget(QLabel("No equipped sets recorded."))
        return
    for name, count in counts.most_common():
        row = QHBoxLayout()
        row.addWidget(QLabel(name))
        row.addStretch()
        row.addWidget(QLabel(f"{count}/5"))
        card.addLayout(row)


def set_bonus_card(_page, build: PlayerBuild):
    """Show canonical equipped-set counts for each weapon bar."""

    card = FoundryCard("Set Bonuses")
    front = GearStatInputResolver.equipped_set_counts(build, active_bar="front")
    back = GearStatInputResolver.equipped_set_counts(build, active_bar="back")

    if front == back:
        _add_set_counts(card, "Both Bars", front)
    else:
        _add_set_counts(card, "Front Bar", front)
        _add_set_counts(card, "Back Bar", back)
    return card
