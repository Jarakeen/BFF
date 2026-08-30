from pathlib import Path
from engine.config import get_resource_path
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QAbstractSpinBox, QFrame, QHBoxLayout, QLabel
from widgets import build_editor
from services.skill_bar_eligibility import filter_skill_choices

ASSET_ROOT = get_resource_path("assets", "AbilityIcons", "icons", "128")


def _icon_for_skill(skill: dict) -> QIcon:
    texture = str(skill.get("texture", "") or "").strip()
    if not texture:
        return QIcon()
    filename = Path(texture.replace("\\", "/")).name
    local = ASSET_ROOT / Path(filename).with_suffix(".png")
    return QIcon(str(local)) if local.exists() else QIcon()


def _vertical_separator() -> QFrame:
    separator = QFrame()
    separator.setFrameShape(QFrame.Shape.VLine)
    separator.setFrameShadow(QFrame.Shadow.Plain)
    separator.setFixedHeight(28)
    separator.setStyleSheet("color: rgba(200, 164, 106, 0.45);")
    return separator


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
    """BuildEditor with compact build identity and centralized skill eligibility."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Reuse the canonical fields created by BuildEditor. Recreating build_name
        # here used to sever the visible control from the base model, while the
        # grid cleanup also discarded the base Mundus selector entirely.
        self.build_name.setPlaceholderText("Build name")
        self.build_name.setFixedWidth(500)
        self.mundus.setMinimumWidth(180)

        identity_card = self.layout().itemAt(0).widget()
        if identity_card is not None and hasattr(identity_card, "body_layout"):
            grid = identity_card.body_layout.itemAt(0).layout()
            if grid is not None:
                keep = {
                    self.build_name,
                    self.vampire,
                    self.werewolf,
                    self.attribute_health,
                    self.attribute_magicka,
                    self.attribute_stamina,
                    self.attribute_total,
                    self.mundus,
                }
                remove = []
                for index in range(grid.count() - 1, -1, -1):
                    item = grid.itemAt(index)
                    widget = item.widget()
                    row, _column, _row_span, _column_span = grid.getItemPosition(index)
                    if row >= 2:
                        remove.append((index, widget))
                for index, widget in remove:
                    grid.takeAt(index)
                    if widget is not None and widget not in keep:
                        widget.setParent(None)
                        widget.deleteLater()

            row = QHBoxLayout()
            row.setContentsMargins(8, 4, 8, 4)
            row.setSpacing(8)
            row.addWidget(self.build_name)

            self.werewolf.setText("WW")
            self.vampire.setText("Vamp")
            row.addWidget(self.werewolf)
            row.addWidget(self.vampire)

            # Treat attributes as one compact visual island rather than letting
            # them bleed into the affiliation and Mundus controls.
            row.addSpacing(18)
            row.addWidget(_vertical_separator())
            row.addSpacing(18)

            for widget, prefix in (
                (self.attribute_magicka, "Mag "),
                (self.attribute_stamina, "Stam "),
                (self.attribute_health, "Health "),
            ):
                widget.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
                widget.setFixedWidth(78 if prefix != "Health " else 88)
                widget.setPrefix(prefix)
                widget.lineEdit().setPlaceholderText("")
                row.addWidget(widget)

            self.attribute_total.setText("0/64")
            self.attribute_total.setMinimumWidth(48)
            row.addWidget(self.attribute_total)

            row.addSpacing(18)
            row.addWidget(_vertical_separator())
            row.addSpacing(18)
            row.addStretch(1)

            mundus_label = QLabel("Mundus")
            mundus_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(mundus_label)
            row.addWidget(self.mundus)
            identity_card.addLayout(row)

        self.eso_class.currentTextChanged.connect(self._on_class_changed)
        self._sync_skill_state()

    def _update_attribute_limits(self):
        super()._update_attribute_limits()
        self.attribute_total.setText(
            f"{self.attribute_health.value() + self.attribute_magicka.value() + self.attribute_stamina.value()}/64"
        )

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
