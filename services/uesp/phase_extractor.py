from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PhaseFact:
    label: str
    threshold: str = ""
    description: str = ""


_PHASE_REF = re.compile(r"(?i)\bphase\s+(\d+|[ivx]+)\b")
_EXPLICIT_PHASE_HEADING = re.compile(r"(?i)^phase(?:\s+(\d+|[ivx]+))?(?:\s*[-:.]\s*.*)?$")
_PHASE_THRESHOLD = re.compile(
    r"(?i)\b(?:phase\s+(?:\d+|[ivx]+)|final\s+phase)\b[^.]{0,120}?\b(?:at|reaches?|below|under)\s+(\d{1,3})\s*%\s*(?:health)?"
)
_HEALTH_THRESHOLD = re.compile(
    r"(?i)\b(?:at|reaches?|below|under)\s+(\d{1,3})\s*%\s*(?:health)?\b"
)


def extract_phases(blocks: list[dict]) -> list[PhaseFact]:
    """Extract only source-explicit phase facts.

    A bare health percentage is never enough to create a phase. Repeated
    references to the same phase are merged. A threshold in the same block,
    or in the immediately following block, may enrich the current explicit
    phase reference. After that one-block window, percentages are ignored.
    """
    results: list[PhaseFact] = []
    index_by_label: dict[str, int] = {}
    current_label: str | None = None
    threshold_window = False

    def add(label: str, threshold: str = "", description: str = "") -> None:
        clean = label.strip()
        if not clean:
            return
        key = clean.casefold()
        description = description.strip()
        existing_index = index_by_label.get(key)
        if existing_index is None:
            index_by_label[key] = len(results)
            results.append(PhaseFact(clean, threshold, description))
            return

        existing = results[existing_index]
        merged_threshold = existing.threshold or threshold
        merged_description = existing.description
        if threshold and not existing.threshold and description:
            merged_description = f"{existing.description} {description}".strip()
        elif description and description != existing.description and threshold:
            merged_description = f"{existing.description} {description}".strip()
        results[existing_index] = PhaseFact(existing.label, merged_threshold, merged_description)

    for block in blocks:
        kind = block.get("type", "")
        text = block.get("text", "").strip()
        if not text:
            continue

        # A phase reference opens a one-block threshold window.
        if kind == "heading":
            heading = text.rstrip(":").strip()
            match = _EXPLICIT_PHASE_HEADING.match(heading)
            if match:
                token = match.group(1)
                current_label = f"Phase {token.upper()}" if token else heading
                threshold_match = _PHASE_THRESHOLD.search(text)
                threshold = f"{threshold_match.group(1)}%" if threshold_match else ""
                add(current_label, threshold, text)
                threshold_window = not bool(threshold)
                continue

        phase_match = _PHASE_REF.search(text)
        if phase_match:
            token = phase_match.group(1).upper()
            current_label = f"Phase {token}"
            threshold_match = _PHASE_THRESHOLD.search(text)
            threshold = f"{threshold_match.group(1)}%" if threshold_match else ""
            add(current_label, threshold, text)
            threshold_window = not bool(threshold)
            continue

        if threshold_window and current_label:
            threshold_match = _HEALTH_THRESHOLD.search(text)
            if threshold_match:
                add(current_label, f"{threshold_match.group(1)}%", text)

        # Never let a percentage many blocks later attach to an old phase.
        threshold_window = False

    return results
