from pathlib import Path
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit
from widgets import build_editor
from services.skill_bar_eligibility import filter_skill_choices

ASSET_ROOT = Path(__file__).resolve().parents[2] / "assets" / "AbilityIcons" / "icons" / "128"


def _icon_for_skill(skill: dict) -> QIcon:
    texture = str(skill.get("texture", "") or "").strip()
    if not texture:
        return QIcon()
    filename = Path(texture.replace("\\", "/")).name
    local = ASSET_ROOT / Path(filename).with_suffix(".png")
    return QIcon(str(local)) if local.exists() else QIcon()


class EligibleSkillBarRow(build_editor.SkillBarRow):
    """Build-editor skill bar using the centralized combat eligibility rules."""

    def __init__(self, skill_choices, parent=None):
        self.vampire = False
        self.werewolf = False
        self.transformed_form = None
        self._selected_class = ""
        super().__init__(skill_choices, parent)

    def set_affiliation(self, *, vampire: bool = False, werewolf: bool = False):
        self.vampire = bool(vampire)
        self.werewolf = bool(werewolf)
        self._rebuild_combos()

    def set_form(self, form: str | None):
        value = (form or "").strip().casefold()
        self.transformed_form = value if value in {"vampire", "werewolf"} else None
        self._rebuild_combos()

    def set_class(self, eso_class: str):
        self._selected_class = eso_class or ""
        self._rebuild_combos()

    def _rebuild_combos(self):
        current_values = [field.currentText().strip() for field in self.fields]
        for i, (field, current) in enumerate(zip(self.fields, current_values)):
            field.blockSignals(True)
            field.clear()
            field.addItem("")
            choices = filter_skill_choices(
                self.all_skill_choices,
                character_class=self._selected_class,
                slot_index=i,
                vampire=self.vampire,
                werewolf=self.werewolf,
                transformed_form=self.transformed_form,
            )
            for skill in choices:
                name = str(skill.get("name", "") or "").strip()
                if not name:
                    continue
                field.addItem(name, skill)
                icon = _icon_for_skill(skill)
                if not icon.isNull():
                    field.setItemIcon(field.count() - 1, icon)
            index = field.findText(current, Qt.MatchFlag.MatchExactly)
            field.setCurrentIndex(index if index >= 0 else 0)
            field.setIconSize(QSize(42, 42))
            field.blockSignals(False)


class EligibleBuildEditor(build_editor.BuildEditor):
    """BuildEditor with build-name and centralized skill eligibility."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.build_name = QLineEdit()
        self.build_name.setPlaceholderText("Build name")

        # BuildEditor already owns the single Vampire/Werewolf pair in the
        # Identity card. Add only the build-name field here. Do not create a
        # second affiliation control pair.
        identity_card = self.layout().itemAt(0).widget()
        if identity_card is not None and hasattr(identity_card, "body_layout"):
            row = QHBoxLayout()
            row.addWidget(QLabel("Build Name"))
            row.addWidget(self.build_name, 2)
            row.addStretch(1)
            identity_card.addLayout(row)

        self.eso_class.currentTextChanged.connect(self._on_class_changed)
        self._sync_skill_state()

    def _sync_skill_state(self):
        vampire = self.vampire.isChecked()
        werewolf = self.werewolf.isChecked()
        for bar in (getattr(self, "front_bar", None), getattr(self, "back_bar", None)):
            if hasattr(bar, "set_affiliation"):
                bar.set_affiliation(vampire=vampire, werewolf=werewolf)
                bar.set_class(self.eso_class.currentText().strip())

    def _on_class_changed(self, eso_class: str):
        for bar in (getattr(self, "front_bar", None), getattr(self, "back_bar", None)):
            if hasattr(bar, "set_class"):
                bar.set_class(eso_class)
        for card in self._boss_cards:
            card.set_class(eso_class)

    @property
    def model(self):
        model = super().model
        model.BuildName = self.build_name.text().strip()
        return model

    def load(self, model):
        super().load(model)
        self.build_name.setText(getattr(model, "BuildName", "") or "")
        self._sync_skill_state()
