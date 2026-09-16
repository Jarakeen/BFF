from __future__ import annotations

"""Safe mockup-style polish for Rotation Builder evidence, Compare, and Save/Export tabs.

This layer deliberately moves only live widgets whose ownership is known. It does not
rebuild the whole Rotation workspace and does not delete engine-owned controls.
"""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_card import FoundryCard


def _tab(page, title: str) -> QWidget | None:
    tabs = getattr(page, "rotation_builder_tabs", None)
    if tabs is None:
        return None
    wanted = str(title or "").strip().casefold()
    for index in range(tabs.count()):
        if str(tabs.tabText(index) or "").strip().casefold() == wanted:
            return tabs.widget(index)
    return None


def _card(page, title: str) -> FoundryCard | None:
    wanted = str(title or "").strip().casefold()
    for card in page.findChildren(FoundryCard):
        if str(card.title_label.text() or "").strip().casefold() == wanted:
            return card
    return None


def _field(title: str, widget: QWidget) -> QWidget:
    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    label = QLabel(title)
    label.setProperty("sidebarHeading", True)
    layout.addWidget(label)
    layout.addWidget(widget)
    return host


def _muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setProperty("muted", True)
    return label


def _detach(widget: QWidget, page) -> None:
    widget.setParent(page)


def _clear_layout(layout, *, preserve=()) -> None:
    keep = set(preserve)
    while layout.count():
        item = layout.takeAt(0)
        nested = item.layout()
        if nested is not None:
            _clear_layout(nested, preserve=keep)
        widget = item.widget()
        if widget is not None and widget not in keep:
            widget.setParent(None)
            widget.deleteLater()


def _flatten_duration_evidence(page) -> None:
    """Remove the redundant FoundryCard wrapped around RotationDurationEvidenceCard."""
    tab = _tab(page, "Uptime & Resources")
    inner = getattr(page, "duration_evidence_card", None)
    if tab is None or inner is None:
        return
    layout = tab.layout()
    if not isinstance(layout, QGridLayout):
        return

    outer = _card(page, "Duration & Uptime Evidence")
    if outer is None or outer is inner:
        return

    position = None
    index = layout.indexOf(outer)
    if index >= 0:
        position = layout.getItemPosition(index)
        layout.takeAt(index)

    _detach(inner, page)
    outer.setParent(None)
    outer.deleteLater()

    row, column, row_span, column_span = position or (0, 1, 1, 1)
    inner.set_body_margins(10, 7, 10, 8)
    inner.set_body_spacing(5)
    layout.addWidget(inner, row, column, row_span, column_span)


def _compare_identity_text(page, artifact, *, fallback: str) -> str:
    if isinstance(artifact, dict):
        character = str(artifact.get("character_name") or "").strip()
        build = str(artifact.get("build_name") or "").strip()
        if character or build:
            return "\n".join(part for part in (character, build) if part)
    plan = getattr(page, "rotation_plan", None)
    if fallback == "Current Generated" and plan is not None:
        character = str(getattr(plan, "character_name", "") or "").strip()
        build = str(getattr(plan, "build_name", "") or "").strip()
        if character or build:
            return "\n".join(part for part in (character, build) if part)
    return fallback


def _refresh_compare_headers(page) -> None:
    if not hasattr(page, "rotation_compare_header_labels"):
        return
    current_saved = None
    build = page._selected_build()
    if build is not None:
        from engine.config import get_data_dir
        from services.build_rotation_artifact_service import (
            BuildRotationArtifactService,
            resolve_canonical_build_id,
        )

        build_id = resolve_canonical_build_id(page.build_service.canonical.catalog_service, build)
        if build_id:
            current_saved = BuildRotationArtifactService(
                get_data_dir() / "build_rotations.json"
            ).get_rotation(build_id)

    alternate = page.rotation_compare_build_combo.currentData()
    texts = (
        _compare_identity_text(page, None, fallback="Current Generated"),
        _compare_identity_text(page, current_saved, fallback="Current Saved"),
        _compare_identity_text(page, alternate, fallback="Alternate Saved"),
    )
    for label, text in zip(page.rotation_compare_header_labels, texts):
        label.setText(text)


def _rebuild_compare(page) -> None:
    tab = _tab(page, "Compare")
    if tab is None or bool(getattr(page, "_rotation_mockup_compare_installed", False)):
        return
    layout = tab.layout()
    if layout is None:
        return

    combo = page.rotation_compare_build_combo
    table = page.rotation_compare_table
    _detach(combo, page)
    _detach(table, page)
    _clear_layout(layout, preserve=(combo, table))

    card = FoundryCard("Compare Rotations", "◇").set_watermark("compass", 0.035)
    card.set_body_margins(10, 7, 10, 8)
    card.set_body_spacing(6)

    intro = QHBoxLayout()
    intro.setContentsMargins(0, 0, 0, 0)
    intro.setSpacing(8)
    title = QLabel("See how changes affect performance, uptime, and sustain.")
    title.setProperty("muted", True)
    intro.addWidget(title, 1)

    page.rotation_compare_by_combo = QComboBox()
    page.rotation_compare_by_combo.addItem("Builds")
    page.rotation_compare_by_combo.setEnabled(False)
    page.rotation_compare_by_combo.setToolTip(
        "Only saved-build comparison is wired today; other comparison families are not implemented."
    )
    intro.addWidget(_field("COMPARE BY", page.rotation_compare_by_combo))
    intro.addWidget(_field("ADD BUILD", combo), 1)
    refresh = QPushButton("Refresh")
    refresh.clicked.connect(lambda: page.rotation_compare_build_combo.currentIndexChanged.emit(combo.currentIndex()))
    intro.addWidget(refresh)
    card.addLayout(intro)

    headers = QGridLayout()
    headers.setContentsMargins(0, 0, 0, 0)
    headers.setHorizontalSpacing(8)
    page.rotation_compare_header_labels = []
    for column, heading in enumerate(("Current Generated", "Current Saved", "Alternate Saved")):
        host = QWidget()
        host.setProperty("rotationCompareBuildCard", True)
        host_layout = QVBoxLayout(host)
        host_layout.setContentsMargins(10, 8, 10, 8)
        host_layout.setSpacing(2)
        eyebrow = QLabel(heading.upper())
        eyebrow.setProperty("sidebarHeading", True)
        value = QLabel(heading)
        value.setWordWrap(True)
        value.setProperty("cardTitle", True)
        host_layout.addWidget(eyebrow)
        host_layout.addWidget(value)
        headers.addWidget(host, 0, column)
        headers.setColumnStretch(column, 1)
        page.rotation_compare_header_labels.append(value)
    card.addLayout(headers)

    table.setMinimumHeight(280)
    table.setAlternatingRowColors(True)
    table.horizontalHeader().setStretchLastSection(True)
    card.addWidget(table)

    page.rotation_compare_summary = _muted(
        "Comparison is evidence-only. Metrics absent from an older saved artifact remain blank rather than being reconstructed or guessed."
    )
    card.addWidget(page.rotation_compare_summary)
    layout.addWidget(card)

    combo.currentIndexChanged.connect(lambda _index: _refresh_compare_headers(page))
    page._rotation_mockup_compare_installed = True
    _refresh_compare_headers(page)


def _disabled_checkbox(text: str, reason: str) -> QCheckBox:
    box = QCheckBox(text)
    box.setChecked(True)
    box.setEnabled(False)
    box.setToolTip(reason)
    return box


def _rebuild_save_export(page) -> None:
    tab = _tab(page, "Save / Export")
    if tab is None or bool(getattr(page, "_rotation_mockup_save_export_installed", False)):
        return
    layout = tab.layout()
    if layout is None:
        return

    save_button = page.rotation_v2_save_button
    export_button = page.rotation_v2_export_pdf_button
    _detach(save_button, page)
    _detach(export_button, page)
    _clear_layout(layout, preserve=(save_button, export_button))

    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(8)
    grid.setColumnStretch(0, 3)
    grid.setColumnStretch(1, 2)

    save = FoundryCard("Save Rotation", "◆").set_watermark("compass", 0.035)
    save.set_body_margins(10, 7, 10, 8)
    save.set_body_spacing(6)

    page.rotation_save_name_preview = QLineEdit()
    page.rotation_save_name_preview.setReadOnly(True)
    page.rotation_save_name_preview.setPlaceholderText("Uses the canonical Character • Build identity")
    save.addWidget(_field("NAME", page.rotation_save_name_preview))

    page.rotation_save_description_preview = QTextEdit()
    page.rotation_save_description_preview.setReadOnly(True)
    page.rotation_save_description_preview.setMaximumHeight(82)
    page.rotation_save_description_preview.setPlaceholderText(
        "Description metadata is not persisted by build_rotations.json yet."
    )
    page.rotation_save_description_preview.setEnabled(False)
    page.rotation_save_description_preview.setToolTip(
        "Disabled until the rotation artifact schema owns description metadata."
    )
    save.addWidget(_field("DESCRIPTION", page.rotation_save_description_preview))

    tags = QLineEdit()
    tags.setPlaceholderText("Tags")
    tags.setEnabled(False)
    tags.setToolTip("Tags are visible in the mockup but are not part of the rotation artifact schema yet.")
    save.addWidget(_field("TAGS", tags))

    save_to = QHBoxLayout()
    my_rotations = QRadioButton("My Rotations")
    team_library = QRadioButton("Team Library")
    export_only = QRadioButton("Export Only")
    my_rotations.setChecked(True)
    team_library.setEnabled(False)
    export_only.setEnabled(False)
    team_library.setToolTip("Team Library persistence is not implemented yet.")
    export_only.setToolTip("Use the Export Options card for the implemented PDF export.")
    save_to.addWidget(my_rotations)
    save_to.addWidget(team_library)
    save_to.addWidget(export_only)
    save_to.addStretch()
    save.addLayout(save_to)

    save_button.setText("Save Rotation")
    save_button.setProperty("primary", True)
    save.addWidget(save_button)
    grid.addWidget(save, 0, 0)

    right = QWidget()
    right_layout = QVBoxLayout(right)
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(8)

    export = FoundryCard("Export Options", "✦").set_watermark("feather", 0.04)
    export.set_body_margins(10, 7, 10, 8)
    export.set_body_spacing(4)
    export.addWidget(_disabled_checkbox(
        "Include timeline", "The existing PDF renderer owns timeline inclusion; per-section export toggles are not implemented yet."
    ))
    export.addWidget(_disabled_checkbox(
        "Include rotation steps", "The existing PDF renderer owns action-step inclusion; per-section export toggles are not implemented yet."
    ))
    export.addWidget(_disabled_checkbox(
        "Include resource summary", "The existing PDF renderer owns resource-summary inclusion; per-section export toggles are not implemented yet."
    ))
    export.addWidget(_disabled_checkbox(
        "Include explanations", "The existing PDF renderer does not expose independent section toggles yet."
    ))
    export_format = QComboBox()
    export_format.addItem("PDF (Formatted)")
    export_format.setEnabled(False)
    export.addWidget(_field("EXPORT FORMAT", export_format))
    export_button.setText("Export")
    export.addWidget(export_button)
    right_layout.addWidget(export)

    share = FoundryCard("Share", "◇").set_watermark("compass", 0.03)
    copy_link = QPushButton("Copy Link")
    share_code = QPushButton("Generate Share Code")
    copy_link.setEnabled(False)
    share_code.setEnabled(False)
    copy_link.setToolTip("Share links are not implemented for local build-owned rotation artifacts.")
    share_code.setToolTip("Share-code generation is not implemented yet.")
    share_row = QHBoxLayout()
    share_row.addWidget(copy_link)
    share_row.addWidget(share_code)
    share.addLayout(share_row)
    right_layout.addWidget(share)
    grid.addWidget(right, 0, 1)

    footer = _muted("Leave better records.")
    footer.setProperty("cardTitle", True)
    grid.addWidget(footer, 1, 0, 1, 2)
    layout.addLayout(grid)

    def refresh_identity(*_args) -> None:
        build = page._selected_build()
        if build is None:
            page.rotation_save_name_preview.clear()
            return
        character = str(getattr(build, "Name", "") or "").strip()
        build_name = str(getattr(build, "BuildName", "") or "").strip()
        page.rotation_save_name_preview.setText(
            " • ".join(part for part in (character, build_name) if part)
        )

    page.character_combo.currentIndexChanged.connect(refresh_identity)
    page.build_combo.currentIndexChanged.connect(refresh_identity)
    refresh_identity()
    page._rotation_mockup_save_export_installed = True


def install_rotation_builder_v2_mockup_cards(page) -> None:
    """Apply the safe mockup-card pass without rebuilding the full workspace."""
    if bool(getattr(page, "_rotation_builder_v2_mockup_cards_installed", False)):
        return
    _flatten_duration_evidence(page)
    _rebuild_compare(page)
    _rebuild_save_export(page)
    page._rotation_builder_v2_mockup_cards_installed = True


__all__ = ["install_rotation_builder_v2_mockup_cards"]
