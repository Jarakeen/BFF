from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from services.scribing_catalog import (
    compatible_affix,
    compatible_focus,
    compatible_signature,
    grimoire_names,
    result_name,
    skill_line_for_grimoire,
)
from services.scribing_result_service import ScribingResultService
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage
from ui.ux_icons import set_button_icon


class ScribingSimulatorPage(FoundryPage):
    """Standalone theorycrafting workspace for ESO Scribing recipes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False
        self.result_service = ScribingResultService(get_data_dir() / "eso.db")
        self._build_ui()
        self.reset()

    def _build_ui(self) -> None:
        header = FoundryHeader(
            title="Scribing Simulator",
            subtitle="Theorycraft a Grimoire with one compatible Focus, Signature, and Affix script.",
            department="TOOLS • SCRIBING",
        )
        self.set_header(header)

        workspace = QHBoxLayout()
        workspace.setContentsMargins(0, 0, 0, 0)
        workspace.setSpacing(8)

        builder = FoundryCard("Scribing Recipe", "lunar-wand")
        builder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        self.grimoire = QComboBox()
        self.focus = QComboBox()
        self.signature = QComboBox()
        self.affix = QComboBox()
        for combo in (self.grimoire, self.focus, self.signature, self.affix):
            combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.grimoire.addItem("Choose a Grimoire", "")
        for name in grimoire_names():
            self.grimoire.addItem(name, name)

        form.addRow("Grimoire", self.grimoire)
        form.addRow("Focus Script", self.focus)
        form.addRow("Signature Script", self.signature)
        form.addRow("Affix Script", self.affix)
        builder.addLayout(form)

        actions = QHBoxLayout()
        reset = FoundryButton("Reset", role=ButtonRole.SECONDARY, compact=True)
        set_button_icon(reset, "refresh", 15)
        reset.clicked.connect(self.reset)
        actions.addStretch(1)
        actions.addWidget(reset)
        builder.addLayout(actions)
        workspace.addWidget(builder, 2)

        preview = FoundryCard("Result Preview", "open-book").set_watermark("lunar-wand", 0.04)
        self.result_title = QLabel("Choose a Grimoire")
        self.result_title.setProperty("heroTitle", True)
        self.result_title.setWordWrap(True)
        self.skill_line = QLabel()
        self.skill_line.setWordWrap(True)
        self.recipe = QLabel()
        self.recipe.setWordWrap(True)
        self.recipe.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.compatibility = QLabel()
        self.compatibility.setWordWrap(True)
        self.note = QLabel()
        self.note.setWordWrap(True)

        preview.addWidget(self.result_title)
        preview.addWidget(self.skill_line)
        preview.addWidget(self.recipe)
        preview.addWidget(self.compatibility)
        preview.addWidget(self.note)
        preview.addStretch(1)
        workspace.addWidget(preview, 3)

        host = QWidget()
        host.setLayout(workspace)
        self.add_workspace(host)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

        self.grimoire.currentIndexChanged.connect(self._grimoire_changed)
        self.focus.currentIndexChanged.connect(self._refresh_preview)
        self.signature.currentIndexChanged.connect(self._refresh_preview)
        self.affix.currentIndexChanged.connect(self._refresh_preview)

    @staticmethod
    def _replace_combo(combo: QComboBox, label: str, values: list[str]) -> None:
        current = str(combo.currentData() or "")
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(label, "")
        for value in values:
            combo.addItem(value, value)
        if current:
            index = combo.findData(current)
            if index >= 0:
                combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def reset(self) -> None:
        self._loading = True
        self.grimoire.setCurrentIndex(0)
        self._replace_combo(self.focus, "Choose a Focus Script", [])
        self._replace_combo(self.signature, "Choose a Signature Script", [])
        self._replace_combo(self.affix, "Choose an Affix Script", [])
        self._loading = False
        self._refresh_preview()

    def _grimoire_changed(self, *_args) -> None:
        if self._loading:
            return
        grimoire = str(self.grimoire.currentData() or "")
        self._loading = True
        self._replace_combo(self.focus, "Choose a Focus Script", compatible_focus(grimoire))
        self._replace_combo(self.signature, "Choose a Signature Script", compatible_signature(grimoire))
        self._replace_combo(self.affix, "Choose an Affix Script", compatible_affix(grimoire))
        self._loading = False
        self._refresh_preview()

    def _verified_result_name(self, grimoire: str, focus: str) -> tuple[str, str]:
        if not focus:
            return "", ""
        observed = self.result_service.result_name(grimoire, focus)
        if observed:
            return observed, "eso_client"
        static = result_name(grimoire, focus)
        if static:
            return static, "catalog"
        return "", ""

    def _refresh_preview(self, *_args) -> None:
        if self._loading:
            return

        grimoire = str(self.grimoire.currentData() or "")
        focus = str(self.focus.currentData() or "")
        signature = str(self.signature.currentData() or "")
        affix = str(self.affix.currentData() or "")

        if not grimoire:
            self.result_title.setText("Choose a Grimoire")
            self.skill_line.setText("Select a base Scribing skill to begin.")
            self.recipe.clear()
            self.compatibility.clear()
            if self.result_service.available:
                self.note.setText(
                    f"Verified ESO client result-name catalog loaded: {self.result_service.count} Grimoire + Focus pairs."
                )
            else:
                self.note.setText(
                    "No verified ESO client result-name extract is loaded yet. The simulator will use explicit static mappings only."
                )
            self.status.info("Scribing Simulator ready.")
            return

        verified_name, name_source = self._verified_result_name(grimoire, focus)
        self.result_title.setText((verified_name or grimoire).upper())
        line = skill_line_for_grimoire(grimoire) or "Unknown skill line"
        self.skill_line.setText(f"Skill line: {line}")

        values = [
            f"Grimoire: {grimoire}",
            f"Focus: {focus or '—'}",
            f"Signature: {signature or '—'}",
            f"Affix: {affix or '—'}",
        ]
        self.recipe.setText("\n".join(values))

        counts = (
            len(compatible_focus(grimoire)),
            len(compatible_signature(grimoire)),
            len(compatible_affix(grimoire)),
        )
        self.compatibility.setText(
            f"Compatible choices for {grimoire}: {counts[0]} Focus • {counts[1]} Signature • {counts[2]} Affix"
        )

        complete = all((focus, signature, affix))
        if name_source == "eso_client":
            version = self.result_service.game_version or str(self.result_service.api_version or "")
            suffix = f" ({version})" if version else ""
            self.note.setText(
                "Result name observed from the official ESO client Scribing API"
                f"{suffix} for this Grimoire + Focus pair."
            )
        elif name_source == "catalog":
            self.note.setText(
                "Result name is explicitly verified in the Foundry static catalog for this Grimoire + Focus pair."
            )
        elif focus:
            self.note.setText(
                "The exact transformed skill name has not been verified yet, so BFF will not invent one."
            )
        else:
            self.note.setText("Choose one script from each column to complete the recipe.")

        if complete:
            self.status.success("Complete compatible Scribing recipe assembled.")
        else:
            missing = []
            if not focus:
                missing.append("Focus")
            if not signature:
                missing.append("Signature")
            if not affix:
                missing.append("Affix")
            self.status.info("Choose: " + ", ".join(missing))
