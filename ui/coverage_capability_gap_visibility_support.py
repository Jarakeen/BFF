from __future__ import annotations

"""Expose the exact build-evidence gaps behind Coverage's Unverified state."""

from PySide6.QtWidgets import QLabel


_INSTALLED = False
_ORIGINAL_SNAPSHOT = None
_ORIGINAL_REFRESH = None


def _audit_label(build) -> str:
    return str(
        getattr(build, "Gamertag", "")
        or getattr(build, "Name", "")
        or getattr(build, "BuildName", "")
        or "Unnamed build"
    ).strip()


def _snapshot_with_gap_capture(self, builds):
    assert _ORIGINAL_SNAPSHOT is not None
    snapshot = _ORIGINAL_SNAPSHOT(self, builds)
    captured = []
    service = getattr(self, "capability_service", None)
    if service is not None:
        for build in tuple(builds or ()):
            try:
                captured.append((build, service.audit_build(build)))
            except Exception:
                continue
    self._coverage_build_audits = tuple(captured)
    return snapshot


def _refresh_with_gap_visibility(self, *args, **kwargs):
    assert _ORIGINAL_REFRESH is not None
    result = _ORIGINAL_REFRESH(self, *args, **kwargs)

    audits = tuple(getattr(self, "_coverage_build_audits", ()) or ())
    gaps: list[str] = []
    seen: set[str] = set()
    for build, audit in audits:
        player = _audit_label(build)
        build_name = str(getattr(build, "BuildName", "") or "").strip()
        label = f"{player} • {build_name}" if build_name and build_name.casefold() != player.casefold() else player
        for message in tuple(getattr(audit, "capability_unresolved", ()) or ()):
            text = f"{label}: {message}"
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            gaps.append(text)

    card = getattr(self, "providers_card", None)
    if card is not None and gaps:
        card.set_title("Static Sources & Build Evidence Gaps")
        heading = QLabel(f"{len(gaps)} capability-resolution gap(s) are keeping some effects Unverified:")
        heading.setWordWrap(True)
        heading.setProperty("muted", True)
        card.addWidget(heading)
        for text in gaps[:7]:
            item = QLabel(f"• {text}")
            item.setWordWrap(True)
            item.setTextInteractionFlags(item.textInteractionFlags())
            card.addWidget(item)
        if len(gaps) > 7:
            more = QLabel(f"• + {len(gaps) - 7} more. Fix or confirm the build details, then run the health check again.")
            more.setWordWrap(True)
            more.setProperty("muted", True)
            card.addWidget(more)
    elif card is not None:
        card.set_title("Identified Static Sources")
    return result


def install() -> None:
    global _INSTALLED, _ORIGINAL_SNAPSHOT, _ORIGINAL_REFRESH
    if _INSTALLED:
        return

    from ui.coverage_page import CoveragePage

    _ORIGINAL_SNAPSHOT = CoveragePage.snapshot_for_builds
    _ORIGINAL_REFRESH = CoveragePage.refresh
    CoveragePage.snapshot_for_builds = _snapshot_with_gap_capture
    CoveragePage.refresh = _refresh_with_gap_visibility
    _INSTALLED = True


__all__ = ["install"]
