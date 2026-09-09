from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QPushButton

from services.rotation_pdf_export_service import (
    RotationPdfExportContext,
    RotationPdfExportService,
)


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip()).strip("_.")
    return cleaned or "rotation"


def install_rotation_pdf_export(
    page,
    *,
    exporter: RotationPdfExportService | None = None,
) -> None:
    """Attach mobile-friendly PDF export to the canonical visual timeline."""
    if getattr(page, "_rotation_pdf_export_installed", False):
        return
    page._rotation_pdf_export_installed = True
    page.rotation_pdf_exporter = exporter or RotationPdfExportService()

    page.export_rotation_pdf_button = QPushButton("Export PDF")
    page.export_rotation_pdf_button.setEnabled(getattr(page, "rotation_plan", None) is not None)
    page.export_rotation_pdf_button.setToolTip(
        "Export the current rotation as a portrait, phone-readable PDF using the same materialized timeline projection shown here."
    )

    controls_parent = page.rotation_timeline_details_button.parentWidget()
    controls_layout = controls_parent.layout() if controls_parent is not None else None
    if controls_layout is None:
        raise RuntimeError("rotation timeline controls are unavailable for PDF export")
    controls_layout.insertWidget(2, page.export_rotation_pdf_button)

    def export_current_rotation() -> None:
        plan = getattr(page, "rotation_plan", None)
        projection = getattr(page.rotation_timeline_widget.canvas, "_projection", None)
        if plan is None:
            page.status.warning("Generate a rotation before exporting a PDF.")
            return
        if projection is None:
            detail = str(getattr(page, "rotation_timeline_error", "") or "").strip()
            suffix = f": {detail}" if detail else "."
            page.status.warning(f"The visual timeline is unavailable for PDF export{suffix}")
            return

        build = page._selected_build()
        settings = page.rotation_settings()
        character = str(plan.character_name or "Rotation")
        build_name = str(plan.build_name or "Plan")
        default_name = (
            f"{_safe_filename(character)}_{_safe_filename(build_name)}_rotation.pdf"
        )
        filename, _ = QFileDialog.getSaveFileName(
            page,
            "Export Rotation PDF",
            default_name,
            "PDF Files (*.pdf)",
        )
        if not filename:
            return

        context = RotationPdfExportContext(
            role=str(getattr(build, "Role", "") or "Unspecified"),
            eso_class=str(getattr(build, "EsoClass", "") or "Unspecified"),
            race=str(getattr(build, "Race", "") or "Unspecified"),
            rotation_mode=str(settings.get("rotation_type", "Semi-static") or "Semi-static"),
            target_type=str(settings.get("target_type", "Single Target") or "Single Target"),
            sustain_summary=page.resource_summary.text(),
            sustain_detail=page.resource_detail.text(),
            notes=page.notes_edit.toPlainText().strip(),
        )

        try:
            output = page.rotation_pdf_exporter.export(
                plan=plan,
                projection=projection,
                path=Path(filename),
                context=context,
                include_details=True,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            page.status.warning(f"Rotation PDF export failed: {exc}")
            return

        page.status.success(f"Rotation PDF exported: {output}")

    page.export_current_rotation_pdf = export_current_rotation
    page.export_rotation_pdf_button.clicked.connect(export_current_rotation)

    original_set_plan = page.set_rotation_plan

    def set_plan_with_pdf_export(plan) -> None:
        original_set_plan(plan)
        page.export_rotation_pdf_button.setEnabled(True)

    page.set_rotation_plan = set_plan_with_pdf_export

    original_clear_plan = page.clear_rotation_plan

    def clear_plan_with_pdf_export(*, refresh: bool = True) -> None:
        original_clear_plan(refresh=refresh)
        page.export_rotation_pdf_button.setEnabled(False)

    page.clear_rotation_plan = clear_plan_with_pdf_export


__all__ = [
    "_safe_filename",
    "install_rotation_pdf_export",
]
