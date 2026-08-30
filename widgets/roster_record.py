# ==================================================
# Black Feather Foundry
#
# File:
# widgets/roster_record.py
#
# Purpose:
# Editable personnel record for a single roster member.
#
# ==================================================

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QComboBox,
    QLineEdit,
)

from models.roster_model import (
    RosterMember,
    ROLES,
    STATUSES,
    ESO_CLASSES,
)


class RosterRecord(QWidget):
    """Editable identity, role, team membership, and status for one roster member."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.member_id: int | None = None

        self.player_name = QLineEdit()
        self.character_name = QLineEdit()

        self.eso_class = QComboBox()
        self.eso_class.addItems(ESO_CLASSES)

        self.primary_role = QComboBox()
        self.primary_role.addItems(ROLES)

        self.secondary_role = QComboBox()
        self.secondary_role.addItems(ROLES)

        self.team = QComboBox()
        self.team.setEditable(True)
        self.team.setToolTip(
            "A player can belong to multiple teams. Separate team names with commas."
        )
        self.team.lineEdit().setPlaceholderText(
            "Team 1, Team 2, ..."
        )

        self.status = QComboBox()
        self.status.addItems(STATUSES)

        form = QFormLayout(self)
        form.addRow("Player Name", self.player_name)
        form.addRow("Character Name", self.character_name)
        form.addRow("ESO Class", self.eso_class)
        form.addRow("Primary Role", self.primary_role)
        form.addRow("Secondary Role", self.secondary_role)
        form.addRow("Teams", self.team)
        form.addRow("Status", self.status)

    def set_team_choices(self, team_names: list[str]):
        current = self.team.currentText()
        self.team.blockSignals(True)
        self.team.clear()
        self.team.addItem("")
        self.team.addItems(team_names)
        self.team.setCurrentText(current)
        self.team.blockSignals(False)

    @staticmethod
    def _normalize_teams(value: str) -> str:
        result: list[str] = []
        seen: set[str] = set()
        for raw in (value or "").split(","):
            name = raw.strip()
            key = name.casefold()
            if not name or key in seen:
                continue
            seen.add(key)
            result.append(name)
        return ", ".join(result)

    @property
    def model(self) -> RosterMember:
        return RosterMember(
            Id=self.member_id,
            PlayerName=self.player_name.text().strip(),
            CharacterName=self.character_name.text().strip(),
            EsoClass=self.eso_class.currentText(),
            PrimaryRole=self.primary_role.currentText(),
            SecondaryRole=self.secondary_role.currentText(),
            Team=self._normalize_teams(self.team.currentText()),
            Status=self.status.currentText(),
        )

    def load(self, member: RosterMember):
        self.member_id = member.Id
        self.player_name.setText(member.PlayerName)
        self.character_name.setText(member.CharacterName)
        self.eso_class.setCurrentText(member.EsoClass)
        self.primary_role.setCurrentText(member.PrimaryRole)
        self.secondary_role.setCurrentText(member.SecondaryRole)
        self.team.setCurrentText(member.Team)
        self.status.setCurrentText(member.Status or "Active")

    def clear(self):
        self.member_id = None
        self.player_name.clear()
        self.character_name.clear()
        self.eso_class.setCurrentIndex(0)
        self.primary_role.setCurrentIndex(0)
        self.secondary_role.setCurrentIndex(0)
        self.team.setCurrentText("")
        self.status.setCurrentIndex(0)
