from __future__ import annotations

"""Performance Mode one-page Build Matrix PDF export.

This exporter deliberately treats Context Variants as sparse encounter swaps.
The saved Build remains the baseline authority; effective variant builds are
resolved through the canonical context resolver before presentation.

All UI -> export-service inputs cross a strict Pydantic boundary so malformed
slot maps, duplicate variant assignments, unbounded labels, or non-boolean
include flags fail before ReportLab sees them.
"""

from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models.build_model import BuildContextVariant, PlayerBuild
from services.build_context_variant_service import resolve_build_context
from services.performance_mode_build_export_source_schema import (
    validate_performance_mode_export_source,
)

BuildMatrixSlot = Literal["boss1", "boss2", "boss3", "trash", "flex"]
BuildMatrixMode = Literal["current", "mapped_variants", "separate_variants"]

_SLOT_ORDER: tuple[BuildMatrixSlot, ...] = ("boss1", "boss2", "boss3", "trash", "flex")
_SLOT_TITLES = {
    "boss1": ("BOSS 1", "PRIMARY"),
    "boss2": ("BOSS 2", "MECHANIC"),
    "boss3": ("BOSS 3", "EXECUTE"),
    "trash": ("TRASH / WAVES", "CLEAVE + SPEED"),
    "flex": ("FLEX / PORTAL / SPECIAL", "SITUATIONAL"),
}
_SLOT_COLORS = {
    "boss1": "#143D40",
    "boss2": "#76598F",
    "boss3": "#2F7A80",
    "trash": "#B98539",
    "flex": "#76598F",
}


class BuildMatrixIncludeOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    sets: bool = True
    weapons: bool = True
    skills: bool = True
    champion_points: bool = True
    food: bool = True
    potions: bool = True
    class_mastery: bool = True
    notes: bool = True


class BuildMatrixSlotSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    slot: BuildMatrixSlot
    variant_index: int | None = Field(default=None, ge=0)


class BuildMatrixExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    mode: BuildMatrixMode = "mapped_variants"
    slots: tuple[BuildMatrixSlotSelection, ...]
    include: BuildMatrixIncludeOptions = Field(default_factory=BuildMatrixIncludeOptions)

    @model_validator(mode="after")
    def validate_slot_map(self):
        names = tuple(item.slot for item in self.slots)
        if names != _SLOT_ORDER:
            raise ValueError("Build Matrix slots must be supplied exactly once in canonical order")
        if self.slots[0].variant_index is not None:
            raise ValueError("Boss 1 is the saved Build baseline and cannot map to a Context Variant")
        assigned = [item.variant_index for item in self.slots if item.variant_index is not None]
        if len(assigned) != len(set(assigned)):
            raise ValueError("A Context Variant cannot be mapped to more than one Build Matrix slot")
        return self


class BuildMatrixCard(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    title: str
    subtitle: str = ""
    sets_pieces: str = ""
    weapons: str = ""
    mythic_monster: str = ""
    champion_points: str = ""
    food_potion: str = ""
    mastery: str = ""
    front_skills: tuple[str, str, str, str, str, str] = ("", "", "", "", "", "")
    back_skills: tuple[str, str, str, str, str, str] = ("", "", "", "", "", "")
    swaps_triggers: str = ""
    why_this_build: str = ""

    @field_validator(
        "title",
        "subtitle",
        "sets_pieces",
        "weapons",
        "mythic_monster",
        "champion_points",
        "food_potion",
        "mastery",
        "swaps_triggers",
        "why_this_build",
    )
    @classmethod
    def bounded_text(cls, value: str) -> str:
        value = value.strip()
        if len(value) > 1000:
            raise ValueError("Build Matrix card text is unexpectedly long")
        return value

    @field_validator("front_skills", "back_skills")
    @classmethod
    def bounded_skill_text(
        cls,
        values: tuple[str, str, str, str, str, str],
    ) -> tuple[str, str, str, str, str, str]:
        cleaned = tuple(value.strip() for value in values)
        if any(len(value) > 240 for value in cleaned):
            raise ValueError("Build Matrix skill text is unexpectedly long")
        return cleaned  # type: ignore[return-value]


class BuildMatrixBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    mundus: str = ""
    attributes: str = ""
    curse: str = ""
    class_mastery: str = ""
    food: str = ""
    potions: str = ""
    cp_core: str = ""
    static_note: str = ""

    @field_validator("*")
    @classmethod
    def bounded_text(cls, value: str) -> str:
        value = value.strip()
        if len(value) > 1200:
            raise ValueError("Build Matrix baseline text is unexpectedly long")
        return value


class BuildMatrixPage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    player: str
    eso_class: str = ""
    role: str = ""
    team_trial: str = ""
    patch: str = ""
    date: str = ""
    build_name: str = ""
    cards: tuple[BuildMatrixCard, BuildMatrixCard, BuildMatrixCard, BuildMatrixCard, BuildMatrixCard]
    baseline: BuildMatrixBaseline

    @field_validator("player", "eso_class", "role", "team_trial", "patch", "date", "build_name")
    @classmethod
    def bounded_metadata(cls, value: str) -> str:
        value = value.strip()
        if len(value) > 500:
            raise ValueError("Build Matrix page metadata is unexpectedly long")
        return value


@dataclass(frozen=True)
class _VariantRef:
    index: int
    variant: BuildContextVariant
    label: str


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _bar(values: Sequence[str]) -> tuple[str, str, str, str, str, str]:
    items = [_clean(value) for value in list(values or ())[:6]]
    items.extend([""] * (6 - len(items)))
    return tuple(items[:6])  # type: ignore[return-value]


def _variant_records(build: PlayerBuild) -> tuple[_VariantRef, ...]:
    variants = list(getattr(build, "ContextVariants", ()) or ())
    if not variants:
        variants = [
            BuildContextVariant.from_boss_loadout(item)
            for item in (getattr(build, "BossLoadouts", ()) or ())
        ]
    records: list[_VariantRef] = []
    for index, variant in enumerate(variants):
        label_bits = [
            _clean(getattr(variant, "BossName", "")),
            _clean(getattr(variant, "TeamName", "")),
        ]
        label = " · ".join(item for item in label_bits if item)
        if not label:
            label = f"{_clean(getattr(variant, 'ContextType', 'Variant')) or 'Variant'} {index + 1}"
        records.append(_VariantRef(index=index, variant=variant, label=label))
    return tuple(records)


def variant_choices(build: PlayerBuild) -> tuple[tuple[int, str], ...]:
    """Stable index/label choices for the export dialog."""
    build = validate_performance_mode_export_source(build)
    return tuple((item.index, item.label) for item in _variant_records(build))


def _variant_bucket(ref: _VariantRef) -> str:
    haystack = " ".join(
        (
            ref.label,
            _clean(getattr(ref.variant, "Notes", "")),
            _clean(getattr(ref.variant, "ContextType", "")),
        )
    ).casefold()
    if any(word in haystack for word in ("trash", "wave", "add pack", "cleave")):
        return "trash"
    if any(word in haystack for word in ("portal", "solo", "kite", "special", "utility")):
        return "flex"
    if any(word in haystack for word in ("execute", "burn")):
        return "boss3"
    return "boss"


def default_export_request(build: PlayerBuild) -> BuildMatrixExportRequest:
    """Map saved variants conservatively without inventing game semantics."""
    build = validate_performance_mode_export_source(build)
    refs = list(_variant_records(build))
    mapped: dict[BuildMatrixSlot, int | None] = {slot: None for slot in _SLOT_ORDER}
    used: set[int] = set()

    for preferred in ("trash", "flex", "boss3"):
        match = next(
            (ref for ref in refs if ref.index not in used and _variant_bucket(ref) == preferred),
            None,
        )
        if match is not None:
            mapped[preferred] = match.index  # type: ignore[index]
            used.add(match.index)

    for slot in ("boss2", "boss3", "trash", "flex"):
        if mapped[slot] is not None:
            continue
        match = next((ref for ref in refs if ref.index not in used), None)
        if match is None:
            break
        mapped[slot] = match.index
        used.add(match.index)

    mode: BuildMatrixMode = "mapped_variants" if refs else "current"
    return BuildMatrixExportRequest(
        mode=mode,
        slots=tuple(
            BuildMatrixSlotSelection(slot=slot, variant_index=mapped[slot])
            for slot in _SLOT_ORDER
        ),
    )


def _gear_slots(build: PlayerBuild) -> list[tuple[str, object]]:
    rows: list[tuple[str, object]] = []
    for name in ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet"):
        rows.append((name, build.Armor.get(name, {})))
    rows.extend(
        [
            ("Neck", build.Necklace),
            ("Ring 1", build.Ring1),
            ("Ring 2", build.Ring2),
            ("Front", build.FrontBarWeapon),
            ("Front Off", build.FrontBarOffHand),
            ("Back", build.BackBarWeapon),
            ("Back Off", build.BackBarOffHand),
        ]
    )
    return rows


def _field(slot: object, name: str) -> str:
    if isinstance(slot, dict):
        return _clean(slot.get(name, ""))
    return _clean(getattr(slot, name, ""))


def _set_summary(build: PlayerBuild) -> str:
    counts: dict[str, int] = {}
    for _name, slot in _gear_slots(build):
        for field in ("Set", "Set2"):
            set_name = _field(slot, field)
            if set_name:
                counts[set_name] = counts.get(set_name, 0) + 1
    return " / ".join(f"{name} ({count})" for name, count in counts.items())


def _weapon_summary(build: PlayerBuild) -> str:
    bits: list[str] = []
    for label, slot in (
        ("F", build.FrontBarWeapon),
        ("F2", build.FrontBarOffHand),
        ("B", build.BackBarWeapon),
        ("B2", build.BackBarOffHand),
    ):
        values = [value for value in (_field(slot, "Set"), _field(slot, "WeaponType")) if value]
        if values:
            bits.append(f"{label}: {' · '.join(values)}")
    return " / ".join(bits)


def _cp_summary(build: PlayerBuild) -> str:
    return " · ".join(
        f"{_clean(cp.Name)} ({_clean(cp.Points)})" if _clean(cp.Points) else _clean(cp.Name)
        for cp in build.ChampionPoints
        if _clean(cp.Name)
    )


def _mastery_summary(build: PlayerBuild, mastery_names: dict[int, str]) -> str:
    values: list[str] = []
    for raw in getattr(build, "ClassMasteryAbilityIds", ()) or ():
        try:
            ability_id = int(raw)
        except (TypeError, ValueError):
            continue
        values.append(mastery_names.get(ability_id, f"Ability {ability_id}"))
    return " · ".join(values)


def _curse(build: PlayerBuild) -> str:
    if bool(getattr(build, "Werewolf", False)):
        return "Werewolf"
    if bool(getattr(build, "Vampire", False)):
        return "Vampire"
    return "Mortal"


def _variant_effective(build: PlayerBuild, variant: BuildContextVariant) -> PlayerBuild:
    resolved = resolve_build_context(
        build,
        team_name=_clean(getattr(variant, "TeamName", "")),
        boss_name=_clean(getattr(variant, "BossName", "")),
    )
    return validate_performance_mode_export_source(resolved)


def _gear_changes(base: PlayerBuild, effective: PlayerBuild) -> tuple[str, str]:
    sets: list[str] = []
    weapons: list[str] = []
    base_rows = dict(_gear_slots(base))
    effective_rows = dict(_gear_slots(effective))
    for label, current in effective_rows.items():
        before = base_rows.get(label, {})
        before_set = " / ".join(value for value in (_field(before, "Set"), _field(before, "Set2")) if value)
        after_set = " / ".join(value for value in (_field(current, "Set"), _field(current, "Set2")) if value)
        if before_set != after_set and after_set:
            sets.append(f"{label}: {after_set}")
        if label.startswith(("Front", "Back")):
            before_weapon = " · ".join(value for value in (_field(before, "Set"), _field(before, "WeaponType")) if value)
            after_weapon = " · ".join(value for value in (_field(current, "Set"), _field(current, "WeaponType")) if value)
            if before_weapon != after_weapon and after_weapon:
                weapons.append(f"{label}: {after_weapon}")
    return "; ".join(sets), "; ".join(weapons)


def _bar_changes(base: Sequence[str], effective: Sequence[str]) -> tuple[str, str, str, str, str, str]:
    a = _bar(base)
    b = _bar(effective)
    return tuple(b[index] if b[index] != a[index] else "" for index in range(6))  # type: ignore[return-value]


def _variant_card(
    *,
    slot: BuildMatrixSlot,
    base: PlayerBuild,
    ref: _VariantRef,
    include: BuildMatrixIncludeOptions,
    mastery_names: dict[int, str],
) -> BuildMatrixCard:
    effective = _variant_effective(base, ref.variant)
    title, default_subtitle = _SLOT_TITLES[slot]
    set_changes, weapon_changes = _gear_changes(base, effective)
    cp_change = _cp_summary(effective) if _cp_summary(effective) != _cp_summary(base) else ""
    context = ref.label
    notes = _clean(getattr(ref.variant, "Notes", "")) if include.notes else ""
    return BuildMatrixCard(
        title=title,
        subtitle=context or default_subtitle,
        sets_pieces=set_changes if include.sets else "",
        weapons=weapon_changes if include.weapons else "",
        champion_points=cp_change if include.champion_points else "",
        food_potion="",
        mastery="",
        front_skills=_bar_changes(base.FrontBarSkills, effective.FrontBarSkills) if include.skills else ("", "", "", "", "", ""),
        back_skills=_bar_changes(base.BackBarSkills, effective.BackBarSkills) if include.skills else ("", "", "", "", "", ""),
        swaps_triggers=context,
        why_this_build=notes,
    )


def _baseline_card(
    build: PlayerBuild,
    *,
    include: BuildMatrixIncludeOptions,
    mastery_names: dict[int, str],
) -> BuildMatrixCard:
    return BuildMatrixCard(
        title="BOSS 1",
        subtitle=_clean(build.BuildName) or "PRIMARY",
        sets_pieces=_set_summary(build) if include.sets else "",
        weapons=_weapon_summary(build) if include.weapons else "",
        champion_points="",
        food_potion="",
        mastery="",
        front_skills=_bar(build.FrontBarSkills) if include.skills else ("", "", "", "", "", ""),
        back_skills=_bar(build.BackBarSkills) if include.skills else ("", "", "", "", "", ""),
        swaps_triggers="Base / primary setup",
        why_this_build=_clean(build.Notes) if include.notes else "",
    )


def build_matrix_page(
    build: PlayerBuild,
    request: BuildMatrixExportRequest,
    *,
    team_trial: str = "",
    patch: str = "",
    date: str = "",
    mastery_names: dict[int, str] | None = None,
) -> BuildMatrixPage:
    """Create the validated presentation model before any PDF drawing."""
    build = validate_performance_mode_export_source(build)
    request = BuildMatrixExportRequest.model_validate(request)
    refs = {item.index: item for item in _variant_records(build)}
    for selection in request.slots:
        if selection.variant_index is not None and selection.variant_index not in refs:
            raise ValueError(f"Context Variant index {selection.variant_index} does not exist on this Build")

    names = dict(mastery_names or {})
    include = request.include
    cards: list[BuildMatrixCard] = [
        _baseline_card(build, include=include, mastery_names=names)
    ]
    for selection in request.slots[1:]:
        if request.mode == "current" or selection.variant_index is None:
            title, subtitle = _SLOT_TITLES[selection.slot]
            cards.append(BuildMatrixCard(title=title, subtitle=subtitle))
            continue
        cards.append(
            _variant_card(
                slot=selection.slot,
                base=build,
                ref=refs[selection.variant_index],
                include=include,
                mastery_names=names,
            )
        )

    baseline = BuildMatrixBaseline(
        mundus=_clean(build.Mundus),
        attributes=f"H {int(build.AttributeHealth)} / M {int(build.AttributeMagicka)} / S {int(build.AttributeStamina)}",
        curse=_curse(build),
        class_mastery=_mastery_summary(build, names) if include.class_mastery else "",
        food=_clean(build.Food) if include.food else "",
        potions=_clean(build.Potion) if include.potions else "",
        cp_core=_cp_summary(build) if include.champion_points else "",
        static_note="Class Mastery, Food and Potions are shared across every encounter setup.",
    )
    return BuildMatrixPage(
        player=_clean(build.Name) or _clean(build.Gamertag) or "Unnamed Character",
        eso_class=_clean(build.EsoClass),
        role=_clean(build.Role),
        team_trial=_clean(team_trial),
        patch=_clean(patch),
        date=_clean(date),
        build_name=_clean(build.BuildName),
        cards=tuple(cards),  # type: ignore[arg-type]
        baseline=baseline,
    )


class PerformanceModeBuildMatrixExporter:
    """Render one low-ink landscape Letter page per Build."""

    def __init__(self, *, eso_db_path: str | Path | None = None) -> None:
        self.eso_db_path = Path(eso_db_path) if eso_db_path else None

    def _mastery_names(self, build: PlayerBuild) -> dict[int, str]:
        if self.eso_db_path is None or not self.eso_db_path.exists():
            return {}
        try:
            from services.class_mastery_repository import ClassMasteryRepository

            repository = ClassMasteryRepository(self.eso_db_path)
            return {
                int(item.base_ability_id): str(item.name)
                for item in repository.for_class(_clean(build.EsoClass))
            }
        except Exception:
            return {}

    @staticmethod
    def _reportlab():
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import LETTER, landscape
            from reportlab.pdfgen import canvas
        except ImportError as exc:
            raise RuntimeError(
                "Performance Mode PDF export requires ReportLab. The packaged FoundryDock build includes it."
            ) from exc
        return colors, landscape(LETTER), canvas

    def export_build(
        self,
        build: PlayerBuild,
        path: str | Path,
        *,
        request: BuildMatrixExportRequest | None = None,
        team_trial: str = "",
        patch: str = "",
        date: str = "",
    ) -> Path:
        return self.export_builds(
            [build],
            path,
            requests=[request or default_export_request(build)],
            team_trial=team_trial,
            patch=patch,
            date=date,
        )

    def export_builds(
        self,
        builds: Sequence[PlayerBuild],
        path: str | Path,
        *,
        requests: Sequence[BuildMatrixExportRequest] | None = None,
        team_trial: str = "",
        patch: str = "",
        date: str = "",
    ) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        selected: list[PlayerBuild] = []
        for build in builds:
            if not isinstance(build, PlayerBuild):
                raise TypeError("Performance Mode Build Matrix export requires PlayerBuild records")
            if not (_clean(build.Name) or _clean(build.Gamertag) or _clean(build.BuildName)):
                continue
            selected.append(validate_performance_mode_export_source(build))
        if requests is None:
            reqs = [default_export_request(build) for build in selected]
        else:
            reqs = [BuildMatrixExportRequest.model_validate(item) for item in requests]
            if len(reqs) != len(selected):
                raise ValueError("Build Matrix request count must match exported Build count")

        colors, pagesize, canvas_module = self._reportlab()
        pdf = canvas_module.Canvas(str(target), pagesize=pagesize)
        pdf.setTitle("Performance Mode Build Matrix")

        if not selected:
            self._draw_empty(pdf, pagesize, colors)
            pdf.save()
            return target

        first_page = True
        for build, request in zip(selected, reqs):
            if request.mode == "separate_variants":
                variant_refs = _variant_records(build)
                pages: list[tuple[PlayerBuild, str]] = [(build, _clean(build.BuildName) or "Base Build")]
                for ref in variant_refs:
                    pages.append((_variant_effective(build, ref.variant), ref.label))
                for effective, label in pages:
                    if not first_page:
                        pdf.showPage()
                    separate_request = BuildMatrixExportRequest(
                        mode="current",
                        slots=tuple(
                            BuildMatrixSlotSelection(slot=slot, variant_index=None)
                            for slot in _SLOT_ORDER
                        ),
                    )
                    page = build_matrix_page(
                        effective,
                        separate_request,
                        team_trial=team_trial,
                        patch=patch,
                        date=date,
                        mastery_names=self._mastery_names(build),
                    )
                    page = BuildMatrixPage.model_validate(
                        {
                            **page.model_dump(mode="python"),
                            "build_name": label,
                        }
                    )
                    self._draw_page(pdf, pagesize, colors, page)
                    first_page = False
                continue

            if not first_page:
                pdf.showPage()
            page = build_matrix_page(
                build,
                request,
                team_trial=team_trial,
                patch=patch,
                date=date,
                mastery_names=self._mastery_names(build),
            )
            self._draw_page(pdf, pagesize, colors, page)
            first_page = False

        pdf.save()
        return target

    @staticmethod
    def _draw_empty(pdf, pagesize, colors) -> None:
        width, height = pagesize
        pdf.setFillColor(colors.HexColor("#F7F4EC"))
        pdf.rect(0, 0, width, height, stroke=0, fill=1)
        pdf.setFillColor(colors.HexColor("#143D40"))
        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawCentredString(width / 2, height / 2 + 10, "PERFORMANCE MODE BUILD MATRIX")
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(width / 2, height / 2 - 12, "No saved Builds were available to export.")

    @staticmethod
    def _fit(pdf, text: str, max_chars: int) -> str:
        value = _clean(text)
        if len(value) <= max_chars:
            return value
        return value[: max(1, max_chars - 1)].rstrip() + "…"

    @staticmethod
    def _wrap_lines(
        pdf,
        text: str,
        *,
        font_name: str,
        font_size: float,
        max_width: float,
    ) -> list[str]:
        """Wrap without ellipsizing so gameplay names remain readable in the PDF."""
        value = _clean(text)
        if not value:
            return [""]
        words = value.split(" ")
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if pdf.stringWidth(candidate, font_name, font_size) <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            if pdf.stringWidth(word, font_name, font_size) <= max_width:
                current = word
                continue

            fragment = ""
            for char in word:
                candidate_fragment = fragment + char
                if fragment and pdf.stringWidth(
                    candidate_fragment,
                    font_name,
                    font_size,
                ) > max_width:
                    lines.append(fragment)
                    fragment = char
                else:
                    fragment = candidate_fragment
            current = fragment
        if current:
            lines.append(current)
        return lines or [""]

    def _draw_page(self, pdf, pagesize, colors, page: BuildMatrixPage) -> None:
        width, height = pagesize
        bg = colors.HexColor("#F7F4EC")
        ink = colors.HexColor("#24353A")
        muted = colors.HexColor("#6F7B7D")
        pale = colors.HexColor("#E9EEEB")
        gold = colors.HexColor("#C8A46A")
        header = colors.HexColor("#143D40")

        pdf.setFillColor(bg)
        pdf.rect(0, 0, width, height, stroke=0, fill=1)

        header_h = 38
        pdf.setFillColor(header)
        pdf.rect(0, height - header_h, width, header_h, stroke=0, fill=1)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 17)
        pdf.drawString(18, height - 25, "PERFORMANCE MODE BUILD MATRIX")
        pdf.setFont("Helvetica-Bold", 6.6)
        pdf.drawRightString(width - 58, height - 23, "BASELINE / CORE SETUP   •   PER-BUILD SWAPS   •   ONE PAGE")
        pdf.setStrokeColor(gold)
        pdf.setLineWidth(1)
        pdf.line(0, height - header_h, width, height - header_h)

        # Muted PM monogram, intentionally vector-only for low ink and reliable packaging.
        pdf.setStrokeColor(colors.HexColor("#809092"))
        pdf.setFillColor(colors.HexColor("#D8C69E"))
        pdf.setLineWidth(1.2)
        pdf.circle(width - 27, height - 19, 13, stroke=1, fill=0)
        pdf.setFont("Helvetica-BoldOblique", 10)
        pdf.drawCentredString(width - 27, height - 22, "PM")

        meta_y = height - 55
        meta_h = 24
        pdf.setFillColor(colors.white)
        pdf.roundRect(18, meta_y - meta_h, width - 36, meta_h, 5, stroke=0, fill=1)
        meta = [
            ("PLAYER", page.player, 0.20),
            ("CLASS", page.eso_class, 0.12),
            ("ROLE", page.role, 0.10),
            ("TEAM / TRIAL", page.team_trial, 0.23),
            ("PATCH", page.patch, 0.10),
            ("DATE", page.date, 0.12),
        ]
        x = 26
        usable = width - 52
        for label, value, fraction in meta:
            cell_w = usable * fraction
            pdf.setFillColor(muted)
            pdf.setFont("Helvetica-Bold", 5.6)
            pdf.drawString(x, meta_y - 10, label)
            pdf.setFillColor(ink)
            pdf.setFont("Helvetica", 6.8)
            pdf.drawString(x, meta_y - 19, self._fit(pdf, value, max(10, int(cell_w / 4.2))))
            x += cell_w

        gap = 8
        left = 18
        right = width - 18
        top = meta_y - meta_h - 9
        baseline_h = 76
        bottom = 16 + baseline_h + 8
        top_row_h = 210
        bottom_row_h = top - bottom - top_row_h - gap
        col_w = (right - left - 2 * gap) / 3

        rects = {
            "boss1": (left, top - top_row_h, col_w, top_row_h),
            "boss2": (left + col_w + gap, top - top_row_h, col_w, top_row_h),
            "boss3": (left + 2 * (col_w + gap), top - top_row_h, col_w, top_row_h),
            "trash": (left, bottom, (right - left - gap) * 0.5, bottom_row_h),
            "flex": (left + (right - left + gap) * 0.5, bottom, (right - left - gap) * 0.5, bottom_row_h),
        }
        for slot, card in zip(_SLOT_ORDER, page.cards):
            self._draw_card(pdf, colors, ink, muted, pale, slot, card, rects[slot])

        self._draw_baseline(
            pdf,
            colors,
            ink,
            muted,
            gold,
            page.baseline,
            (left, 16, right - left, baseline_h),
        )

    def _draw_card(self, pdf, colors, ink, muted, pale, slot, card: BuildMatrixCard, rect) -> None:
        x, y, w, h = rect
        accent = colors.HexColor(_SLOT_COLORS[slot])
        pdf.setFillColor(colors.white)
        pdf.setStrokeColor(accent)
        pdf.setLineWidth(0.8)
        pdf.roundRect(x, y, w, h, 6, stroke=1, fill=1)

        band_h = 25
        pdf.setFillColor(accent)
        pdf.roundRect(x, y + h - band_h, w, band_h, 6, stroke=0, fill=1)
        pdf.rect(x, y + h - band_h, w, band_h - 6, stroke=0, fill=1)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x + 9, y + h - 16, card.title)
        pdf.setFont("Helvetica-Bold", 5.8)
        pdf.drawRightString(x + w - 8, y + h - 16, self._fit(pdf, card.subtitle, 28).upper())

        row_y = y + h - band_h - 11
        label_x = x + 9
        value_x = x + 68
        value_width = x + w - 8 - value_x

        # Food, potions and Class Mastery are static footer data. Keep the
        # encounter cards for the things a player actually swaps.
        rows = (
            ("SETS / PIECES", card.sets_pieces),
            ("WEAPONS", card.weapons),
            ("CP", card.champion_points),
        )
        for label, value in rows:
            pdf.setFillColor(muted)
            pdf.setFont("Helvetica-Bold", 5.3)
            pdf.drawString(label_x, row_y, label)
            lines = self._wrap_lines(
                pdf,
                value,
                font_name="Helvetica",
                font_size=5.35,
                max_width=value_width,
            )
            pdf.setFillColor(ink)
            pdf.setFont("Helvetica", 5.35)
            line_y = row_y
            for line in lines:
                pdf.drawString(value_x, line_y, line)
                line_y -= 6.3
            used_h = max(10.5, 6.3 * len(lines) + 2.5)
            pdf.setStrokeColor(colors.HexColor("#BEC7C5"))
            pdf.setLineWidth(0.35)
            pdf.line(value_x, row_y - used_h + 1.5, x + w - 8, row_y - used_h + 1.5)
            row_y -= used_h

        pdf.setFillColor(accent)
        pdf.setFont("Helvetica-Bold", 5.8)
        pdf.drawString(label_x, row_y, "SKILLS")
        pdf.setStrokeColor(accent)
        pdf.line(value_x - 6, row_y - 1, x + w - 8, row_y - 1)
        row_y -= 10

        skill_x = value_x - 8
        available = x + w - 8 - skill_x
        cell_gap = 3
        cell_w = (available - cell_gap * 2) / 3
        cell_h = 15.5
        row_gap = 2.5
        for bar_label, values in (("FRONT", card.front_skills), ("BACK", card.back_skills)):
            pdf.setFillColor(muted)
            pdf.setFont("Helvetica-Bold", 5.2)
            pdf.drawString(label_x, row_y - 4, bar_label)
            for index, value in enumerate(values):
                grid_row = index // 3
                grid_col = index % 3
                cx = skill_x + grid_col * (cell_w + cell_gap)
                cy = row_y - grid_row * (cell_h + row_gap) - cell_h
                pdf.setFillColor(pale)
                pdf.roundRect(cx, cy, cell_w, cell_h, 2.5, stroke=0, fill=1)
                slot_label = str(index + 1) if index < 5 else "ULT"
                shown = _clean(value)
                pdf.setFillColor(muted if not shown else ink)
                pdf.setFont("Helvetica-Bold" if not shown else "Helvetica", 4.25)
                if not shown:
                    pdf.drawCentredString(cx + cell_w / 2, cy + 5.4, slot_label)
                    continue
                skill_lines = self._wrap_lines(
                    pdf,
                    f"{slot_label}. {shown}",
                    font_name="Helvetica",
                    font_size=4.25,
                    max_width=cell_w - 4,
                )
                text_y = cy + cell_h - 5.0
                for line in skill_lines:
                    pdf.drawString(cx + 2, text_y, line)
                    text_y -= 4.6
            row_y -= 2 * (cell_h + row_gap) + 4

        max_chars = max(18, int((w - 82) / 3.8))
        for label, value in (("SWAPS / TRIGGERS", card.swaps_triggers), ("WHY THIS BUILD", card.why_this_build)):
            pdf.setFillColor(muted)
            pdf.setFont("Helvetica-Bold", 5.2)
            pdf.drawString(label_x, row_y, label)
            pdf.setFillColor(ink)
            pdf.setFont("Helvetica", 5.35)
            pdf.drawString(value_x, row_y, self._fit(pdf, value, max_chars))
            pdf.setStrokeColor(colors.HexColor("#BEC7C5"))
            pdf.line(value_x, row_y - 2, x + w - 8, row_y - 2)
            row_y -= 11.5

    def _draw_baseline(self, pdf, colors, ink, muted, gold, baseline: BuildMatrixBaseline, rect) -> None:
        x, y, w, h = rect
        pdf.setFillColor(colors.white)
        pdf.setStrokeColor(gold)
        pdf.setLineWidth(0.8)
        pdf.roundRect(x, y, w, h, 6, stroke=1, fill=1)

        pdf.setFillColor(colors.HexColor("#B98539"))
        pdf.roundRect(x + 9, y + h - 20, 88, 14, 7, stroke=0, fill=1)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 6.8)
        pdf.drawCentredString(x + 53, y + h - 15.5, "ALWAYS ON")
        pdf.setFillColor(muted)
        pdf.setFont("Helvetica-Oblique", 5.8)
        pdf.drawString(x + 110, y + h - 15.5, "Only write a value in a build card if it changes from this baseline.")

        fields = [
            ("MUNDUS", baseline.mundus),
            ("ATTR", baseline.attributes),
            ("CURSE", baseline.curse),
            ("CLASS MASTERY", baseline.class_mastery),
            ("FOOD", baseline.food),
            ("POTIONS", baseline.potions),
            ("CP CORE", baseline.cp_core),
            ("STATIC NOTE", baseline.static_note),
        ]
        columns = 4
        cell_w = (w - 18) / columns
        for index, (label, value) in enumerate(fields):
            row = index // columns
            col = index % columns
            fx = x + 9 + col * cell_w
            fy = y + h - 34 - row * 26
            pdf.setFillColor(muted)
            pdf.setFont("Helvetica-Bold", 4.9)
            pdf.drawString(fx, fy, label)
            lines = self._wrap_lines(
                pdf,
                value,
                font_name="Helvetica",
                font_size=5.2,
                max_width=cell_w - 7,
            )
            pdf.setFillColor(ink)
            pdf.setFont("Helvetica", 5.2)
            line_y = fy - 7
            for line in lines:
                pdf.drawString(fx, line_y, line)
                line_y -= 5.8
            pdf.setStrokeColor(colors.HexColor("#C9D0CE"))
            pdf.line(fx, fy - 21, fx + cell_w - 7, fy - 21)

        pdf.setStrokeColor(colors.HexColor("#B8BDBA"))
        pdf.setFillColor(colors.HexColor("#DDD4BF"))
        pdf.circle(x + w - 27, y + 18, 14, stroke=1, fill=0)
        pdf.setFont("Helvetica-BoldOblique", 9)
        pdf.drawCentredString(x + w - 27, y + 15, "PM")


__all__ = [
    "BuildMatrixExportRequest",
    "BuildMatrixIncludeOptions",
    "BuildMatrixSlotSelection",
    "BuildMatrixPage",
    "PerformanceModeBuildMatrixExporter",
    "build_matrix_page",
    "default_export_request",
    "variant_choices",
]
