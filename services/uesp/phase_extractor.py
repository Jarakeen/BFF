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
    r"(?i)\b(?:phase\s+(?:\d+|[ivx]+))\b[^.]{0,120}?\b(?:at|reaches?|below|under|hits?)\s+(\d{1,3})\s*%\s*(?:health)?"
)
_FINAL_PHASE_THRESHOLD = re.compile(
    r"(?i)\bfinal\s+phase\b[^.]{0,120}?\b(?:at|reaches?|below|under|hits?)\s+(\d{1,3})\s*%\s*(?:health)?"
)
_HEALTH_THRESHOLD = re.compile(
    r"(?i)\b(?:at|reaches?|below|under|hits?)\s+(\d{1,3})\s*%\s*(?:health)?\b"
)


def extract_phases(blocks: list[dict]) -> list[PhaseFact]:
    """Extract source-explicit phase facts.

    A bare health percentage never creates a phase. Explicit phase references
    are merged, and explicit final-phase thresholds may be attached to the
    next explicitly named phase. This matches UESP prose such as 'the final
    phase starts when she hits 40%' followed by a separate paragraph describing
    Phase 3.
    """
    results: list[PhaseFact] = []
    index_by_label: dict[str, int] = {}
    current_label: str | None = None
    threshold_window = False
    pending_final_threshold: str | None = None

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

        final_match = _FINAL_PHASE_THRESHOLD.search(text)
        if final_match:
            pending_final_threshold = f"{final_match.group(1)}%"

        if kind == "heading":
            heading = text.rstrip(":").strip()
            match = _EXPLICIT_PHASE_HEADING.match(heading)
            if match:
                token = match.group(1)
                current_label = f"Phase {token.upper()}" if token else heading
                threshold_match = _PHASE_THRESHOLD.search(text)
                threshold = f"{threshold_match.group(1)}%" if threshold_match else ""
                if not threshold and pending_final_threshold:
                    threshold = pending_final_threshold
                    pending_final_threshold = None
                add(current_label, threshold, text)
                threshold_window = not bool(threshold)
                continue

        phase_match = _PHASE_REF.search(text)
        if phase_match:
            token = phase_match.group(1).upper()
            current_label = f"Phase {token}"
            threshold_match = _PHASE_THRESHOLD.search(text)
            threshold = f"{threshold_match.group(1)}%" if threshold_match else ""
            if not threshold and pending_final_threshold:
                threshold = pending_final_threshold
                pending_final_threshold = None
            add(current_label, threshold, text)
            threshold_window = not bool(threshold)
            continue

        if threshold_window and current_label:
            threshold_match = _HEALTH_THRESHOLD.search(text)
            if threshold_match:
                add(current_label, f"{threshold_match.group(1)}%", text)

        threshold_window = False

    return results
