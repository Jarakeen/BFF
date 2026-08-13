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


def extract_phases(blocks: list[dict]) -> list[PhaseFact]:
    """Extract only source-explicit phase facts.

    A bare health percentage is never enough to create a phase. This avoids
    turning ordinary statements such as 'at 70% health' into fake phases.
    """
    results: list[PhaseFact] = []
    seen: set[tuple[str, str]] = set()
    current_label: str | None = None

    def add(label: str, threshold: str = "", description: str = "") -> None:
        clean = label.strip()
        if not clean:
            return
        key = (clean.casefold(), threshold)
        if key in seen:
            return
        seen.add(key)
        results.append(PhaseFact(clean, threshold, description.strip()))

    for block in blocks:
        kind = block.get("type", "")
        text = block.get("text", "").strip()
        if not text:
            continue

        if kind == "heading":
            heading = text.rstrip(":").strip()
            match = _EXPLICIT_PHASE_HEADING.match(heading)
            if match:
                token = match.group(1)
                if token:
                    current_label = f"Phase {token.upper()}"
                elif heading.casefold() in {"phase", "final phase"}:
                    current_label = heading
                else:
                    current_label = heading

                threshold_match = _PHASE_THRESHOLD.search(text)
                threshold = f"{threshold_match.group(1)}%" if threshold_match else ""
                add(current_label, threshold, text)
                continue

        phase_match = _PHASE_REF.search(text)
        if not phase_match:
            continue

        token = phase_match.group(1).upper()
        label = f"Phase {token}"
        threshold_match = _PHASE_THRESHOLD.search(text)
        threshold = f"{threshold_match.group(1)}%" if threshold_match else ""
        add(label, threshold, text)

    return results
