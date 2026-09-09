from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from pathlib import Path
from typing import Iterable

from minmax.rotation_plan import RotationAction, RotationPlan
from services.rotation_timeline_projection_service import RotationTimelineProjection
from services.share_document_export import (
    ShareDocumentTheme,
    VISUAL_THEME_RYLO,
    resolve_share_theme,
)


@dataclass(frozen=True)
class RotationPdfExportContext:
    """Human-readable metadata rendered around one authoritative rotation plan."""

    role: str = "Unspecified"
    eso_class: str = "Unspecified"
    race: str = "Unspecified"
    rotation_mode: str = "Semi-static"
    target_type: str = "Single Target"
    sustain_summary: str = ""
    sustain_detail: str = ""
    notes: str = ""


class RotationPdfExportService:
    """Render the currently materialized rotation timeline as a readable PDF.

    The visual timeline consumes RotationTimelineProjection directly. This exporter
    does not resolve durations, recalculate uptime, re-rank actions, or reinterpret
    the plan. Long rotations are split into 30-second portrait sections so the PDF
    remains readable on a phone instead of becoming one glorious microscopic strip.
    """

    DEFAULT_WINDOW_SECONDS = 30.0

    def export(
        self,
        *,
        plan: RotationPlan,
        projection: RotationTimelineProjection,
        path: str | Path,
        context: RotationPdfExportContext | None = None,
        theme_name: str | None = None,
        include_details: bool = True,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
    ) -> Path:
        if projection.duration_seconds != plan.duration_seconds:
            raise ValueError("rotation PDF requires projection and plan durations to match")
        if window_seconds <= 0 or not math.isfinite(float(window_seconds)):
            raise ValueError("rotation PDF window_seconds must be finite and positive")

        output = Path(path)
        if output.suffix.casefold() != ".pdf":
            output = output.with_suffix(".pdf")
        output.parent.mkdir(parents=True, exist_ok=True)

        rl = self._reportlab()
        theme = resolve_share_theme(theme_name)
        canvas = rl["canvas"].Canvas(str(output), pagesize=rl["LETTER"])
        canvas.setTitle(f"{plan.character_name} - {plan.build_name} Rotation")
        resolved_context = context or RotationPdfExportContext()

        page_number = 1
        self._draw_summary_page(
            canvas,
            rl,
            theme,
            plan,
            projection,
            resolved_context,
            page_number,
        )

        for start, end in self.timeline_windows(plan.duration_seconds, window_seconds):
            canvas.showPage()
            page_number += 1
            self._draw_timeline_page(
                canvas,
                rl,
                theme,
                plan,
                projection,
                resolved_context,
                start,
                end,
                page_number,
            )

        if include_details and plan.actions:
            detail_pages = self._detail_page_slices(plan.actions)
            for page_actions in detail_pages:
                canvas.showPage()
                page_number += 1
                self._draw_details_page(
                    canvas,
                    rl,
                    theme,
                    plan,
                    page_actions,
                    page_number,
                )

        canvas.save()
        return output

    @classmethod
    def timeline_windows(
        cls,
        duration_seconds: float,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
    ) -> tuple[tuple[float, float], ...]:
        duration = max(0.0, float(duration_seconds))
        window = float(window_seconds)
        if duration == 0.0:
            return ((0.0, 0.0),)
        count = int(math.ceil(duration / window))
        return tuple(
            (
                index * window,
                min(duration, (index + 1) * window),
            )
            for index in range(count)
        )

    @staticmethod
    def _detail_page_slices(
        actions: Iterable[RotationAction],
        *,
        rows_per_column: int = 34,
    ) -> tuple[tuple[RotationAction, ...], ...]:
        ordered = tuple(actions)
        per_page = rows_per_column * 2
        return tuple(
            ordered[index : index + per_page]
            for index in range(0, len(ordered), per_page)
        )

    @staticmethod
    def _reportlab():
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import LETTER
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfgen import canvas
        except ImportError as exc:
            raise RuntimeError(
                "Rotation PDF export requires ReportLab. The packaged BFF build includes it."
            ) from exc
        return {
            "colors": colors,
            "LETTER": LETTER,
            "ImageReader": ImageReader,
            "canvas": canvas,
        }

    @staticmethod
    def _lane_palette(theme: ShareDocumentTheme) -> tuple[str, ...]:
        if theme.key == VISUAL_THEME_RYLO:
            return (
                theme.accent,
                "#A23A3F",
                "#C79A3B",
                "#8C8275",
                "#655F59",
                "#BEB6A6",
            )
        return (
            theme.accent,
            "#2F7A80",
            "#59AEB3",
            "#6FA76D",
            "#C89B5A",
            "#B56E66",
        )

    @staticmethod
    def _text_lines(value: str) -> tuple[str, ...]:
        return tuple(
            line.strip()
            for line in str(value or "").replace("\r", "").split("\n")
            if line.strip()
        )

    @staticmethod
    def _truncate(value: str, limit: int) -> str:
        text = str(value or "").strip()
        if len(text) <= limit:
            return text
        return text[: max(1, limit - 3)].rstrip() + "..."

    @classmethod
    def _wrap_text(cls, canvas, text: str, *, font_name: str, font_size: float, width: float) -> tuple[str, ...]:
        words = str(text or "").split()
        if not words:
            return ()
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if canvas.stringWidth(candidate, font_name, font_size) <= width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return tuple(lines)

    @staticmethod
    def _draw_page_chrome(canvas, rl, theme: ShareDocumentTheme, *, page_number: int, label: str) -> None:
        colors = rl["colors"]
        width, height = rl["LETTER"]
        canvas.setFillColor(colors.HexColor(theme.background))
        canvas.rect(0, 0, width, height, stroke=0, fill=1)

        canvas.setFillColor(colors.HexColor(theme.header))
        canvas.rect(0, height - 50, width, 50, stroke=0, fill=1)
        canvas.setStrokeColor(colors.HexColor(theme.accent))
        canvas.setLineWidth(1.0)
        canvas.line(30, height - 50, width - 30, height - 50)

        canvas.setFillColor(colors.HexColor(theme.accent))
        canvas.setFont(theme.heading_font, 13)
        canvas.drawString(34, height - 31, theme.brand)
        canvas.setFont(theme.body_font, 7)
        canvas.setFillColor(colors.HexColor(theme.muted))
        canvas.drawRightString(width - 34, height - 31, f"ROTATION RECORD - {label.upper()}")

        canvas.setStrokeColor(colors.HexColor(theme.rule))
        canvas.setLineWidth(0.6)
        canvas.line(34, 30, width - 34, 30)
        canvas.setFont(theme.body_font, 6.5)
        canvas.setFillColor(colors.HexColor(theme.muted))
        canvas.drawString(34, 18, theme.motto)
        canvas.drawRightString(
            width - 34,
            18,
            f"Generated {datetime.now().strftime('%b %d, %Y')} - Page {page_number}",
        )

    def _draw_summary_page(
        self,
        canvas,
        rl,
        theme: ShareDocumentTheme,
        plan: RotationPlan,
        projection: RotationTimelineProjection,
        context: RotationPdfExportContext,
        page_number: int,
    ) -> None:
        colors = rl["colors"]
        width, height = rl["LETTER"]
        self._draw_page_chrome(canvas, rl, theme, page_number=page_number, label="Summary")

        x = 36
        y = height - 86
        canvas.setFillColor(colors.HexColor(theme.text))
        canvas.setFont(theme.heading_font, 21)
        canvas.drawString(x, y, self._truncate(plan.character_name.upper(), 44))
        y -= 24
        canvas.setFillColor(colors.HexColor(theme.accent))
        canvas.setFont(theme.heading_font, 11)
        canvas.drawString(x, y, self._truncate(plan.build_name.upper(), 56))

        y -= 28
        info = (
            ("ROLE", context.role),
            ("CLASS", context.eso_class),
            ("RACE", context.race),
            ("MODE", context.rotation_mode),
            ("TARGET", context.target_type),
            ("LENGTH", f"{plan.duration_seconds:g}s"),
            ("ACTIONS", str(len(plan.actions))),
            ("TIMELINE ICONS", str(len(projection.actions))),
        )
        col_width = (width - 72) / 4
        for index, (label, value) in enumerate(info):
            row = index // 4
            col = index % 4
            cell_x = x + col * col_width
            cell_y = y - row * 36
            canvas.setFont(theme.body_font, 6.5)
            canvas.setFillColor(colors.HexColor(theme.muted))
            canvas.drawString(cell_x, cell_y, label)
            canvas.setFont(theme.body_font, 9)
            canvas.setFillColor(colors.HexColor(theme.text))
            canvas.drawString(cell_x, cell_y - 12, self._truncate(value, 22))
        y -= 82

        def section(title: str, lines: tuple[str, ...], *, max_lines: int = 8) -> None:
            nonlocal y
            canvas.setFillColor(colors.HexColor(theme.accent))
            canvas.setFont(theme.heading_font, 9)
            canvas.drawString(x, y, title)
            y -= 13
            if not lines:
                lines = ("None reported.",)
            canvas.setFillColor(colors.HexColor(theme.text))
            canvas.setFont(theme.body_font, 7.5)
            for raw in lines[:max_lines]:
                wrapped = self._wrap_text(
                    canvas,
                    raw,
                    font_name=theme.body_font,
                    font_size=7.5,
                    width=width - 72,
                ) or ("",)
                for line in wrapped[:2]:
                    canvas.drawString(x + 6, y, self._truncate(line, 112))
                    y -= 10
            y -= 8

        sustain_lines = self._text_lines(context.sustain_summary) + self._text_lines(context.sustain_detail)
        section("SUSTAIN", sustain_lines, max_lines=8)
        section("ROTATION NOTES", self._text_lines(context.notes), max_lines=7)
        section("ASSUMPTIONS", tuple(plan.assumptions), max_lines=6)
        section("UNRESOLVED EVIDENCE", tuple(projection.unresolved), max_lines=10)

        canvas.setFillColor(colors.HexColor(theme.muted))
        canvas.setFont(theme.body_font, 6.5)
        canvas.drawString(
            x,
            46,
            "Timeline pages use the already-materialized RotationTimelineProjection; no PDF-side duration or uptime math is performed.",
        )

    def _draw_timeline_page(
        self,
        canvas,
        rl,
        theme: ShareDocumentTheme,
        plan: RotationPlan,
        projection: RotationTimelineProjection,
        context: RotationPdfExportContext,
        start: float,
        end: float,
        page_number: int,
    ) -> None:
        colors = rl["colors"]
        width, height = rl["LETTER"]
        self._draw_page_chrome(
            canvas,
            rl,
            theme,
            page_number=page_number,
            label=f"Timeline {start:g}-{end:g}s",
        )

        canvas.setFillColor(colors.HexColor(theme.text))
        canvas.setFont(theme.heading_font, 15)
        canvas.drawString(36, height - 82, f"{plan.character_name} - {plan.build_name}")
        canvas.setFont(theme.body_font, 7)
        canvas.setFillColor(colors.HexColor(theme.muted))
        canvas.drawString(
            36,
            height - 96,
            f"{context.role} - {context.rotation_mode} - {start:g}s to {end:g}s",
        )

        label_width = 84.0
        plot_left = 36.0 + label_width
        plot_right = width - 36.0
        plot_width = max(1.0, plot_right - plot_left)
        window = max(0.001, end - start)

        icon_y = height - 145
        icon_size = 20.0
        axis_y = height - 160
        lane_top = height - 190

        canvas.setStrokeColor(colors.HexColor(theme.rule))
        canvas.setLineWidth(0.4)
        tick = math.ceil(start / 5.0) * 5.0
        while tick <= end + 1e-9:
            x = plot_left + ((tick - start) / window) * plot_width
            canvas.line(x, axis_y - 4, x, 70)
            canvas.setFont(theme.body_font, 6.5)
            canvas.setFillColor(colors.HexColor(theme.muted))
            canvas.drawCentredString(x, axis_y + 3, f"{tick:g}s")
            tick += 5.0

        actions = tuple(
            action
            for action in projection.actions
            if start <= action.time_seconds < end
            or (end == projection.duration_seconds and action.time_seconds == end)
        )
        for action in actions:
            x = plot_left + ((action.time_seconds - start) / window) * plot_width
            icon_x = x - icon_size / 2
            path = Path(str(action.icon_path or ""))
            if path.is_file():
                try:
                    canvas.drawImage(
                        rl["ImageReader"](str(path)),
                        icon_x,
                        icon_y,
                        width=icon_size,
                        height=icon_size,
                        preserveAspectRatio=True,
                        mask="auto",
                    )
                except Exception:
                    self._draw_icon_fallback(canvas, rl, theme, action.name, icon_x, icon_y, icon_size)
            else:
                self._draw_icon_fallback(canvas, rl, theme, action.name, icon_x, icon_y, icon_size)
            canvas.setStrokeColor(colors.HexColor(theme.rule))
            canvas.setFillColor(colors.transparent)
            canvas.rect(icon_x, icon_y, icon_size, icon_size, stroke=1, fill=0)

        lanes = projection.lanes
        lane_count = max(1, len(lanes))
        available_height = max(130.0, lane_top - 210.0)
        lane_pitch = min(18.0, max(11.0, available_height / lane_count))
        palette = self._lane_palette(theme)

        for index, lane in enumerate(lanes):
            y = lane_top - index * lane_pitch
            canvas.setFont(theme.body_font, 6.3)
            canvas.setFillColor(colors.HexColor(theme.text))
            canvas.drawRightString(plot_left - 6, y + 2, self._truncate(lane.label, 20))
            canvas.setStrokeColor(colors.HexColor(theme.rule))
            canvas.setFillColor(colors.HexColor(theme.surface_alt))
            canvas.roundRect(plot_left, y - 2, plot_width, 8, 3, stroke=0, fill=1)
            color = colors.HexColor(palette[index % len(palette)])
            for segment in lane.segments:
                clipped_start = max(start, segment.start_seconds)
                clipped_end = min(end, segment.end_seconds)
                if clipped_end <= clipped_start:
                    continue
                x1 = plot_left + ((clipped_start - start) / window) * plot_width
                x2 = plot_left + ((clipped_end - start) / window) * plot_width
                canvas.setFillColor(color)
                canvas.roundRect(x1, y - 2, max(2.0, x2 - x1), 8, 3, stroke=0, fill=1)

        legend_top = 190.0
        canvas.setFillColor(colors.HexColor(theme.accent))
        canvas.setFont(theme.heading_font, 8)
        canvas.drawString(36, legend_top + 12, "SKILL LEGEND")
        unique_actions = []
        seen: set[str] = set()
        for action in actions:
            key = action.icon_key or action.name.casefold()
            if key in seen:
                continue
            seen.add(key)
            unique_actions.append(action)

        columns = 2
        per_column = max(1, int(math.ceil(len(unique_actions) / columns)))
        column_width = (width - 72) / columns
        for index, action in enumerate(unique_actions):
            col = index // per_column
            row = index % per_column
            item_x = 36 + col * column_width
            item_y = legend_top - row * 15
            path = Path(str(action.icon_path or ""))
            if path.is_file():
                try:
                    canvas.drawImage(
                        rl["ImageReader"](str(path)),
                        item_x,
                        item_y - 4,
                        width=11,
                        height=11,
                        preserveAspectRatio=True,
                        mask="auto",
                    )
                except Exception:
                    pass
            canvas.setFillColor(colors.HexColor(theme.text))
            canvas.setFont(theme.body_font, 6.6)
            canvas.drawString(item_x + 15, item_y, self._truncate(action.name, 34))

        canvas.setFillColor(colors.HexColor(theme.muted))
        canvas.setFont(theme.body_font, 6.5)
        canvas.drawString(
            36,
            46,
            f"Projected skill/ultimate icons: {len(actions)} - duration lanes: {len(lanes)} - unresolved evidence: {len(projection.unresolved)}",
        )

    @staticmethod
    def _draw_icon_fallback(canvas, rl, theme: ShareDocumentTheme, name: str, x: float, y: float, size: float) -> None:
        colors = rl["colors"]
        canvas.setFillColor(colors.HexColor(theme.surface_alt))
        canvas.roundRect(x, y, size, size, 3, stroke=0, fill=1)
        words = [part for part in str(name or "").replace("-", " ").split() if part]
        initials = "?" if not words else "".join(word[0] for word in words[:2]).upper()
        canvas.setFont(theme.body_font, 6)
        canvas.setFillColor(colors.HexColor(theme.text))
        canvas.drawCentredString(x + size / 2, y + size / 2 - 2, initials)

    def _draw_details_page(
        self,
        canvas,
        rl,
        theme: ShareDocumentTheme,
        plan: RotationPlan,
        actions: tuple[RotationAction, ...],
        page_number: int,
    ) -> None:
        colors = rl["colors"]
        width, height = rl["LETTER"]
        self._draw_page_chrome(canvas, rl, theme, page_number=page_number, label="Action Details")

        canvas.setFillColor(colors.HexColor(theme.text))
        canvas.setFont(theme.heading_font, 15)
        canvas.drawString(36, height - 82, f"{plan.character_name} - {plan.build_name}")
        canvas.setFont(theme.body_font, 7)
        canvas.setFillColor(colors.HexColor(theme.muted))
        canvas.drawString(36, height - 96, "Chronological scheduled actions from the authoritative RotationPlan")

        rows_per_column = 34
        column_width = (width - 84) / 2
        start_y = height - 124
        row_height = 18
        for index, action in enumerate(actions):
            col = index // rows_per_column
            row = index % rows_per_column
            x = 36 + col * (column_width + 12)
            y = start_y - row * row_height
            if col > 1:
                break

            canvas.setFillColor(colors.HexColor(theme.muted))
            canvas.setFont(theme.body_font, 6.3)
            canvas.drawString(x, y, f"{action.time_seconds:5.1f}s")
            canvas.drawString(x + 36, y, (action.bar or "-").upper())
            canvas.setFillColor(colors.HexColor(theme.text))
            canvas.setFont(theme.body_font, 7.1)
            name = action.name or action.kind.value.replace("_", " ").title()
            canvas.drawString(x + 72, y, self._truncate(name, 26))
            canvas.setFillColor(colors.HexColor(theme.muted))
            canvas.setFont(theme.body_font, 5.8)
            canvas.drawString(x + 72, y - 8, action.kind.value.replace("_", " "))


__all__ = [
    "RotationPdfExportContext",
    "RotationPdfExportService",
]
