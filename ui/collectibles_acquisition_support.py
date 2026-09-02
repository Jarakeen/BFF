from __future__ import annotations

"""Prefer useful source-backed acquisition text in Collectibles details."""

import json
import re

_INSTALLED = False

_GENERIC_ACQUISITION_PATTERNS = (
    re.compile(r"^obtained in (?:the )?elder scrolls online\.?$", re.IGNORECASE),
    re.compile(r"^found in (?:the )?elder scrolls online\.?$", re.IGNORECASE),
    re.compile(r"^available in (?:the )?elder scrolls online\.?$", re.IGNORECASE),
    re.compile(r"^acquired in (?:the )?elder scrolls online\.?$", re.IGNORECASE),
    re.compile(r"^play (?:the )?elder scrolls online.*$", re.IGNORECASE),
)


def _clean_text(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _is_useful_acquisition(value: object) -> bool:
    text = _clean_text(value)
    if not text:
        return False
    if len(text) < 8:
        return False
    return not any(pattern.match(text) for pattern in _GENERIC_ACQUISITION_PATTERNS)


def _extract_acquisition_from_raw(raw_json: object) -> str:
    try:
        payload = json.loads(str(raw_json or ""))
    except (TypeError, json.JSONDecodeError):
        return ""

    candidates: list[object] = []
    if isinstance(payload, dict):
        fields = payload.get("fields")
        if isinstance(fields, dict):
            candidates.extend((fields.get("acquisition"), fields.get("hint")))
        candidates.extend((payload.get("acquisition"), payload.get("hint")))

    for candidate in candidates:
        if _is_useful_acquisition(candidate):
            return _clean_text(candidate)
    return ""


def _source_acquisition(service, collectible_id: int) -> str:
    """Return the best useful acquisition text available for one collectible.

    Prefer richer UESP page-derived acquisition metadata when it exists in any
    source row. Fall back to the normalized collectible's raw source data. This
    leaves the canonical source untouched and merely projects useful text into
    the display layer.
    """

    try:
        row = service.connection.execute(
            "SELECT entity_id, hint, source_raw_json FROM collectible WHERE id = ?",
            (int(collectible_id),),
        ).fetchone()
    except Exception:
        return ""
    if row is None:
        return ""

    entity_id = row["entity_id"] if hasattr(row, "keys") else row[0]
    hint = row["hint"] if hasattr(row, "keys") else row[1]
    source_raw = row["source_raw_json"] if hasattr(row, "keys") else row[2]

    # A UESP page parser already understands the Online Collectible Summary
    # acquisition field. If those richer page records are present, prefer them.
    try:
        if entity_id:
            source_rows = service.connection.execute(
                "SELECT raw_json FROM entity_source WHERE entity_id = ? ORDER BY id DESC",
                (entity_id,),
            ).fetchall()
            for source_row in source_rows:
                raw_value = source_row["raw_json"] if hasattr(source_row, "keys") else source_row[0]
                acquisition = _extract_acquisition_from_raw(raw_value)
                if acquisition:
                    return acquisition
    except Exception:
        pass

    acquisition = _extract_acquisition_from_raw(source_raw)
    if acquisition:
        return acquisition
    return _clean_text(hint) if _is_useful_acquisition(hint) else ""


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import collectibles_page

    original_selection_changed = collectibles_page.CollectiblesPage._selection_changed

    def selection_changed_with_acquisition(self, current, previous):
        original_selection_changed(self, current, previous)
        if current is None or self.current_collectible_id is None:
            return

        # Learned Recipes, Motifs, and Lorebooks install after this layer and
        # provide their own detail rendering. This patch is for the canonical
        # ESO collectible catalog only.
        acquisition = _source_acquisition(self.service, self.current_collectible_id)
        self.detail_hint.setText(f"Where to obtain: {acquisition}" if acquisition else "")

    collectibles_page.CollectiblesPage._selection_changed = selection_changed_with_acquisition
    _INSTALLED = True
