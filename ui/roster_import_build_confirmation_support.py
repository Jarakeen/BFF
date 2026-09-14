from __future__ import annotations

"""Tighten roster build import around ambiguous consumables and scribed skills.

Raid workbooks are human planning documents. They often contain useful but
non-canonical text such as ``Potions: Tri-stat, Bi-stat Stam`` and partial
scribed-skill recipes without an explicit Grimoire. Preserve that information,
but never silently promote an option list or incomplete recipe into confirmed
build state.
"""

import re
import sqlite3
from typing import Any

from PySide6.QtWidgets import QLabel, QMessageBox, QTableWidgetItem

from engine.config import DEFAULT_DATABASE


_INSTALLED = False
_ORIGINAL_PARSE_PERSONAL_LOADOUT = None
_ORIGINAL_PREVIEW_INIT = None
_ORIGINAL_PREVIEW_ACCEPT = None

_SCRIPT_ALIASES = {
    "bleed dmg": "Bleed Damage",
    "disease dmg": "Disease Damage",
    "fire dmg": "Flame Damage",
    "flame dmg": "Flame Damage",
    "frost dmg": "Frost Damage",
    "magic dmg": "Magic Damage",
    "physical dmg": "Physical Damage",
    "poison dmg": "Poison Damage",
    "shock dmg": "Shock Damage",
}


def _text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value: object) -> str:
    return _text(value).casefold()


def _normalize_script(value: object) -> str:
    text = _text(value)
    return _SCRIPT_ALIASES.get(text.casefold(), text)


def _candidate_skill_names(candidate) -> tuple[str, ...]:
    payload = getattr(candidate, "payload", {}) or {}
    names: list[str] = []
    seen: set[str] = set()
    for field in ("FrontBarSkills", "BackBarSkills"):
        for raw in payload.get(field, []) or []:
            name = _text(raw)
            key = name.casefold()
            if name and key not in seen:
                seen.add(key)
                names.append(name)
    return tuple(names)


def _match_result_name(label: str, candidate) -> str:
    wanted = _key(label)
    if not wanted:
        return ""
    skills = _candidate_skill_names(candidate)
    exact = [name for name in skills if _key(name) == wanted]
    if len(exact) == 1:
        return exact[0]
    prefix = [
        name
        for name in skills
        if _key(name).startswith(wanted) or wanted.startswith(_key(name))
    ]
    if len(prefix) == 1:
        return prefix[0]
    # Human sheets commonly abbreviate Leashing Soul as "Leash" and
    # Ulfsild's Contingency as "Ulfsild's". Use a conservative first-token stem
    # only when it identifies exactly one slotted skill.
    stem = wanted.split()[0].rstrip("':")
    if len(stem) >= 4:
        stem_matches = [
            name
            for name in skills
            if _key(name).split()[0].rstrip("':").startswith(stem[:4])
        ]
        if len(stem_matches) == 1:
            return stem_matches[0]
    return _text(label)


def _read_scribed_recipes(parser, sheet, start_col: int, candidate) -> None:
    bar_row = parser._bar_header_row(sheet, start_col)
    if not bar_row:
        return

    recipes: list[dict[str, str]] = []
    for column in range(start_col + 2, min(start_col + 5, sheet.max_column + 1)):
        heading_row = None
        for row in range(bar_row + 1, min(bar_row + 8, sheet.max_row + 1)):
            if _key(sheet.cell(row, column).value) == "scribed skills":
                heading_row = row
                break
        if heading_row is None:
            continue

        for row in range(heading_row + 1, min(heading_row + 6, sheet.max_row + 1)):
            raw = _text(sheet.cell(row, column).value)
            if not raw or raw.casefold() in {"n/a", "na", "none"}:
                continue
            if ":" not in raw:
                continue
            label, details = raw.split(":", 1)
            parts = [_normalize_script(piece) for piece in re.split(r"\s*,\s*", details) if _text(piece)]
            if len(parts) < 3:
                continue
            result_name = _match_result_name(label, candidate)
            recipes.append(
                {
                    "ResultName": result_name,
                    # The workbook gives Focus / Signature / Affix but not the
                    # Grimoire. Leave it explicit for user confirmation rather
                    # than guessing from partially reviewed compatibility data.
                    "Grimoire": "",
                    "Focus": parts[0],
                    "Signature": parts[1],
                    "Affix": parts[2],
                }
            )

    if not recipes:
        return
    payload = candidate.payload
    existing = list(payload.get("ScribedSkillRecipes") or [])
    by_result = {_key(row.get("ResultName")): row for row in existing if isinstance(row, dict)}
    for recipe in recipes:
        by_result[_key(recipe["ResultName"])] = recipe
    payload["ScribedSkillRecipes"] = list(by_result.values())
    payload["ScribedSkills"] = [row["ResultName"] for row in payload["ScribedSkillRecipes"] if row.get("ResultName")]


def _preserve_ambiguous_potion(candidate) -> None:
    payload = getattr(candidate, "payload", {}) or {}
    raw = _text(payload.get("Potion"))
    if not raw:
        return
    options = tuple(piece.strip() for piece in re.split(r"\s*,\s*", raw) if piece.strip())
    if len(options) <= 1:
        return
    payload["_ImportPotionOptions"] = list(options)
    payload["Potion"] = ""
    note = f"Imported potion options (choose one): {', '.join(options)}"
    notes = str(payload.get("Notes") or "").strip()
    if note.casefold() not in notes.casefold():
        payload["Notes"] = "\n".join(piece for piece in (notes, note) if piece)


def _parse_personal_loadout_with_review(self, *args, **kwargs):
    assert _ORIGINAL_PARSE_PERSONAL_LOADOUT is not None
    candidate = _ORIGINAL_PARSE_PERSONAL_LOADOUT(self, *args, **kwargs)
    if candidate is None:
        return None
    sheet = kwargs.get("sheet") if "sheet" in kwargs else (args[0] if args else None)
    start_col = kwargs.get("start_col")
    if start_col is None and len(args) >= 2:
        start_col = args[1]
    if sheet is not None and start_col is not None:
        _read_scribed_recipes(self, sheet, int(start_col), candidate)
    _preserve_ambiguous_potion(candidate)
    return candidate


def _ability_is_crafted(name: str, eso_class: str) -> bool:
    if not DEFAULT_DATABASE.is_file() or not _text(name):
        return False
    try:
        with sqlite3.connect(DEFAULT_DATABASE) as db:
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(ability)")}
            if not {"name", "is_crafted"}.issubset(columns):
                return False
            clauses = ["lower(trim(name)) = lower(trim(?))", "coalesce(is_crafted, 0) = 1"]
            params: list[Any] = [name]
            if eso_class and "class_type" in columns:
                clauses.append("(trim(coalesce(class_type,'')) = '' OR lower(trim(class_type)) = lower(trim(?)))")
                params.append(eso_class)
            row = db.execute(
                f"SELECT 1 FROM ability WHERE {' AND '.join(clauses)} LIMIT 1",
                params,
            ).fetchone()
            return row is not None
    except sqlite3.Error:
        return False


def _candidate_issues(candidate) -> tuple[str, ...]:
    payload = getattr(candidate, "payload", {}) or {}
    issues: list[str] = []
    potion_options = tuple(payload.get("_ImportPotionOptions") or ())
    potion = _text(payload.get("Potion"))
    if potion_options:
        issues.append("choose potion: " + " / ".join(str(value) for value in potion_options))
    elif not potion:
        issues.append("potion not confirmed")

    recipes = {
        _key(row.get("ResultName")): row
        for row in payload.get("ScribedSkillRecipes", []) or []
        if isinstance(row, dict) and _text(row.get("ResultName"))
    }
    for skill in _candidate_skill_names(candidate):
        if not _ability_is_crafted(skill, getattr(candidate, "eso_class", "")):
            continue
        recipe = recipes.get(_key(skill))
        if recipe is None:
            issues.append(f"scribed recipe missing: {skill}")
            continue
        missing = [
            label
            for label, key in (
                ("Grimoire", "Grimoire"),
                ("Focus", "Focus"),
                ("Signature", "Signature"),
                ("Affix", "Affix"),
            )
            if not _text(recipe.get(key))
        ]
        if missing:
            issues.append(f"confirm {skill}: {', '.join(missing)}")
    return tuple(dict.fromkeys(issues))


def _member_review(member) -> tuple[str, ...]:
    issues: list[str] = []
    for candidate in getattr(member, "builds", ()) or ():
        for issue in _candidate_issues(candidate):
            issues.append(f"{candidate.build_name}: {issue}")
    return tuple(issues)


def _preview_init_with_build_review(self, plan, parent=None):
    assert _ORIGINAL_PREVIEW_INIT is not None
    _ORIGINAL_PREVIEW_INIT(self, plan, parent)
    self._build_review_column = self.table.columnCount()
    self.table.insertColumn(self._build_review_column)
    self.table.setHorizontalHeaderItem(
        self._build_review_column,
        QTableWidgetItem("Build Check"),
    )
    for row, member in enumerate(plan.members):
        issues = _member_review(member)
        text = "Ready" if not issues else f"Confirm {len(issues)} item(s)"
        item = QTableWidgetItem(text)
        if issues:
            item.setToolTip("\n".join(issues))
        self.table.setItem(row, self._build_review_column, item)
    self.table.resizeColumnsToContents()

    note = QLabel(
        "Build Check flags imported details Foundry cannot safely choose for you, especially potion option lists and incomplete scribed-skill recipes. "
        "The workbook evidence is preserved; ambiguous values are not silently promoted into canonical build state."
    )
    note.setWordWrap(True)
    note.setProperty("muted", True)
    self.layout().insertWidget(max(0, self.layout().count() - 1), note)


def _selected_review_issues(dialog) -> tuple[str, ...]:
    if not dialog.import_builds.isChecked():
        return ()
    issues: list[str] = []
    for row, member in enumerate(dialog.plan.members):
        enabled = dialog.table.item(row, 0)
        if enabled is None or enabled.checkState().value == 0:
            continue
        for issue in _member_review(member):
            issues.append(f"{member.gamertag} • {issue}")
    return tuple(issues)


def _preview_accept_with_confirmation(self) -> None:
    assert _ORIGINAL_PREVIEW_ACCEPT is not None
    issues = _selected_review_issues(self)
    if issues:
        shown = "\n".join(f"• {line}" for line in issues[:18])
        if len(issues) > 18:
            shown += f"\n• + {len(issues) - 18} more item(s)"
        answer = QMessageBox.warning(
            self,
            "Confirm Incomplete Build Details",
            (
                "Some detected build details need human confirmation before Foundry can use them as canonical capability evidence:\n\n"
                f"{shown}\n\n"
                "You can still import now. Ambiguous potion choices are preserved in build notes and partial scribed recipe details are retained for completion in Builds."
            ),
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Ok:
            return
    _ORIGINAL_PREVIEW_ACCEPT(self)


def install() -> None:
    global _INSTALLED
    global _ORIGINAL_PARSE_PERSONAL_LOADOUT, _ORIGINAL_PREVIEW_INIT, _ORIGINAL_PREVIEW_ACCEPT
    if _INSTALLED:
        return

    from ui import roster_import_workflow

    parser_type = roster_import_workflow.RosterImportParser
    dialog_type = roster_import_workflow.RosterImportPreviewDialog
    _ORIGINAL_PARSE_PERSONAL_LOADOUT = parser_type._parse_personal_loadout
    _ORIGINAL_PREVIEW_INIT = dialog_type.__init__
    _ORIGINAL_PREVIEW_ACCEPT = dialog_type.accept

    parser_type._parse_personal_loadout = _parse_personal_loadout_with_review
    dialog_type.__init__ = _preview_init_with_build_review
    dialog_type.accept = _preview_accept_with_confirmation
    _INSTALLED = True


__all__ = ["install", "_candidate_issues"]
