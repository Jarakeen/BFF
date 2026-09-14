from __future__ import annotations

"""Make Coverage a self-loading raid-team health check.

Coverage remains diagnostic: it reads saved roster/team/build state, resolves the
selected team's effective builds, and audits those builds without changing the
team, assignments, or build configuration.
"""

from PySide6.QtWidgets import QComboBox, QPushButton

from engine.config import get_data_dir
from services.build_context_variant_service import resolve_build_context
from services.eso_database import EsoDatabase
from services.roster_service import RosterService


RAID_TEAM_SLOTS = 12


def _clean(value: object) -> str:
    return str(value or "").strip().lstrip("@").casefold()


def _member_belongs_to_team(member, team_name: str) -> bool:
    wanted = _clean(team_name)
    return any(_clean(name) == wanted for name in str(getattr(member, "Team", "") or "").split(","))


def select_team_builds(builds, members, team_name: str):
    """Return unambiguous saved builds for roster members plus unresolved names.

    Selection is intentionally conservative. A Ready-for-Raid build wins only
    when it is unique; otherwise a sole candidate wins. Ambiguous players stay
    unresolved instead of Coverage silently choosing the wrong character/build.
    """
    selected = []
    unresolved = []
    for member in members:
        player_key = _clean(getattr(member, "PlayerName", ""))
        character_key = _clean(getattr(member, "CharacterName", ""))
        candidates = [
            build for build in builds
            if _clean(getattr(build, "Gamertag", "")) == player_key
        ]
        if character_key:
            exact = [
                build for build in candidates
                if _clean(getattr(build, "Name", "")) == character_key
            ]
            if exact:
                candidates = exact

        ready = [build for build in candidates if bool(getattr(build, "ReadyForRaid", False))]
        if len(ready) == 1:
            chosen = ready[0]
        elif len(candidates) == 1:
            chosen = candidates[0]
        else:
            unresolved.append(
                str(
                    getattr(member, "PlayerName", "")
                    or getattr(member, "CharacterName", "")
                    or "Unnamed"
                )
            )
            continue

        resolved = resolve_build_context(chosen, team_name=team_name, boss_name="")
        slot = str(
            getattr(member, "PrimaryRole", "")
            or getattr(member, "PlayerName", "")
            or "Roster"
        )
        selected.append((slot, resolved))

    return tuple(selected), tuple(unresolved)


def _clear_empty_team_result(page, team_name: str, member_count: int, unresolved: tuple[str, ...]) -> None:
    page._team_scope = ()
    page._team_scope_name = team_name
    page.table.setRowCount(0)
    page.scope_card.set_title(f"Selected Team: {team_name}")
    detail = f"{member_count}/{RAID_TEAM_SLOTS} roster slots populated • 0 saved builds resolved."
    if unresolved:
        detail += f"\nBuild selection unresolved for: {', '.join(unresolved[:8])}"
    page.scope_note.setText(detail)
    page.summary_card.clear()
    page.summary_card.addWidget(page._review_label(
        "TEAM HEALTH CHECK\nNo unambiguous saved builds are available for this team yet."
    ))
    page.providers_card.clear()
    page.providers_card.addWidget(page._review_label("No build evidence loaded."))
    page.status.warning(
        f"{team_name}: no unambiguous saved builds could be loaded for the health check."
    )


def _run_team_health_check(page) -> None:
    combo = getattr(page, "health_check_team_combo", None)
    if combo is None:
        return
    team_name = str(combo.currentData() or "").strip()
    if not team_name:
        page._team_scope = ()
        page._team_scope_name = ""
        old_scope = page.scope_combo.findData("all")
        if old_scope >= 0:
            page.scope_combo.setCurrentIndex(old_scope)
        page.refresh()
        page.scope_card.set_title("All Saved Builds")
        page.scope_note.setText(
            "Library-wide build audit. Choose a raid team above to run a direct team health check."
        )
        return

    roster_service = getattr(page, "health_check_roster_service", None)
    if roster_service is None:
        roster_service = RosterService(EsoDatabase(get_data_dir() / "eso.db"))
        page.health_check_roster_service = roster_service

    members = tuple(
        member for member in roster_service.list_members()
        if _member_belongs_to_team(member, team_name)
    )
    try:
        builds = tuple(page.build_service.load().Members)
    except Exception as exc:
        page.status.error(f"Could not load saved builds for {team_name}: {exc}")
        return

    selected, unresolved = select_team_builds(builds, members, team_name)
    if not selected:
        _clear_empty_team_result(page, team_name, len(members), unresolved)
        return

    page.set_team_scope(team_name, selected, total_slots=RAID_TEAM_SLOTS)
    loaded = len(selected)
    member_count = len(members)
    lines = [
        f"Direct roster health check • {member_count}/{RAID_TEAM_SLOTS} roster slots populated • "
        f"{loaded}/{member_count or RAID_TEAM_SLOTS} saved builds resolved."
    ]
    if unresolved:
        lines.append(f"Build selection unresolved for: {', '.join(unresolved[:8])}")
    lines.append("Static capability evidence only. Coverage never changes the team or its builds.")
    page.scope_note.setText("\n".join(lines))
    if unresolved:
        page.status.warning(
            f"{team_name}: health check loaded {loaded} build(s); unresolved: {', '.join(unresolved[:6])}."
        )
    else:
        page.status.success(f"{team_name}: health check loaded {loaded} saved build(s).")


def _sync_team_choices(page) -> None:
    combo = getattr(page, "health_check_team_combo", None)
    service = getattr(page, "health_check_roster_service", None)
    if combo is None or service is None:
        return
    current = str(combo.currentData() or "")
    names = tuple(service.list_team_names())
    combo.blockSignals(True)
    combo.clear()
    combo.addItem("All Saved Builds", "")
    for name in names:
        combo.addItem(name, name)
    index = combo.findData(current)
    combo.setCurrentIndex(index if index >= 0 else 0)
    combo.blockSignals(False)


def enhance_coverage_page(page) -> None:
    """Install the self-loading health-check controls once on one Coverage page."""
    if bool(getattr(page, "_health_check_enhanced", False)):
        _sync_team_choices(page)
        return

    page._health_check_enhanced = True
    page.health_check_roster_service = RosterService(EsoDatabase(get_data_dir() / "eso.db"))

    if hasattr(page.header, "title"):
        page.header.title.setText("Team Health Check")
    if hasattr(page.header, "subtitle"):
        page.header.subtitle.setText(
            "Load any saved raid team directly and check build/capability coverage without changing it."
        )

    old_scope_parent = page.scope_combo.parentWidget()
    if old_scope_parent is not None:
        old_scope_parent.setVisible(False)

    combo = QComboBox()
    combo.setMinimumWidth(190)
    combo.setToolTip("Choose a saved Roster team. Coverage loads it directly; Optimization is not required.")
    page.health_check_team_combo = combo
    page.header.add_context_widget(page._context_field("TEAM", combo))

    run = QPushButton("Run Health Check")
    run.setProperty("primary", True)
    run.clicked.connect(lambda *_: _run_team_health_check(page))
    page.health_check_run_button = run
    page.header.add_context_widget(run)

    _sync_team_choices(page)
    combo.currentIndexChanged.connect(lambda *_: _run_team_health_check(page))
    page.scope_note.setText(
        "Choose a raid team above for a direct health check, or leave All Saved Builds selected for a library-wide audit."
    )


__all__ = ["enhance_coverage_page", "select_team_builds"]
