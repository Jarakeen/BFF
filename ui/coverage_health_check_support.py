from __future__ import annotations

"""Make Coverage a self-loading raid-team health check.

Coverage remains diagnostic: it reads saved roster/team/build state and audits
those builds without changing the team, assignments, or build configuration.

The direct Coverage workflow intentionally audits the team's assigned *base*
builds. Team/Boss context variants are only applied when another workflow (for
example Assignments -> Evaluate) explicitly supplies an encounter context.
"""

from copy import deepcopy

from PySide6.QtWidgets import QComboBox

from engine.config import get_user_database_path
from models.build_model import PlayerBuild
from services.build_context_variant_service import resolve_build_context
from services.eso_database import EsoDatabase
from services.roster_service import RosterService


RAID_TEAM_SLOTS = 12


def _clean(value: object) -> str:
    return str(value or "").strip().lstrip("@").casefold()


def _member_belongs_to_team(member, team_name: str) -> bool:
    wanted = _clean(team_name)
    return any(
        _clean(name) == wanted
        for name in str(getattr(member, "Team", "") or "").split(",")
    )


def _player_build_from_catalog_record(record: object) -> PlayerBuild | None:
    if not isinstance(record, dict):
        return None
    payload = record.get("legacy")
    if not isinstance(payload, dict):
        payload = record.get("payload")
    if not isinstance(payload, dict):
        return None
    try:
        return PlayerBuild.from_dict(payload)
    except Exception:
        return None


def _resolved_or_base(
    build: PlayerBuild,
    *,
    team_name: str,
    boss_name: str,
    use_context: bool,
) -> PlayerBuild:
    if not use_context:
        return deepcopy(build)
    return resolve_build_context(
        build,
        team_name=team_name,
        boss_name=boss_name,
    )


def _canonical_team_builds(
    page,
    team_name: str,
    boss_name: str = "",
    *,
    use_context: bool = False,
):
    """Load exact build assignments for a team from the canonical build catalog.

    Team membership identifies *which* saved builds belong in the check. It does
    not itself imply that Team or Boss ContextVariants should be applied. Direct
    Coverage checks therefore return base builds unless ``use_context`` is true.
    """
    bridge = getattr(getattr(page, "build_service", None), "canonical", None)
    catalog = getattr(bridge, "catalog_service", None)
    if catalog is None:
        return (), ()

    selected = []
    unresolved = []
    seen_build_ids: set[str] = set()
    try:
        assignments = tuple(catalog.assignments_for_team(team_name))
    except Exception:
        return (), ()

    for assignment in assignments:
        build_id = str(assignment.get("build_id") or "").strip()
        if not build_id or build_id in seen_build_ids:
            continue
        seen_build_ids.add(build_id)
        record = catalog.get_build(build_id)
        build = _player_build_from_catalog_record(record)
        if build is None:
            unresolved.append(
                str(assignment.get("slot_name") or assignment.get("raid_role") or build_id)
            )
            continue
        effective = _resolved_or_base(
            build,
            team_name=team_name,
            boss_name=boss_name,
            use_context=use_context,
        )
        slot = str(
            assignment.get("slot_name")
            or assignment.get("raid_role")
            or getattr(build, "Role", "")
            or getattr(build, "Gamertag", "")
            or "Roster"
        )
        selected.append((slot, effective))

    return tuple(selected), tuple(unresolved)


def select_team_builds(
    builds,
    members,
    team_name: str,
    boss_name: str = "",
    *,
    use_context: bool = False,
):
    """Fallback selection for teams without canonical build assignments.

    A unique Ready-for-Raid build wins; otherwise a sole candidate wins. Any
    ambiguous player remains unresolved rather than silently choosing a build.
    Direct Coverage returns the base build. Context variants are applied only
    when an explicit contextual caller requests them.
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

        effective = _resolved_or_base(
            chosen,
            team_name=team_name,
            boss_name=boss_name,
            use_context=use_context,
        )
        slot = str(
            getattr(member, "PrimaryRole", "")
            or getattr(member, "PlayerName", "")
            or "Roster"
        )
        selected.append((slot, effective))

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
        "TEAM HEALTH CHECK\nNo saved team builds could be resolved."
    ))
    page.providers_card.clear()
    page.providers_card.addWidget(page._review_label("No build evidence loaded."))
    page.status.warning(
        f"{team_name}: no saved team builds could be loaded for the health check."
    )


def run_team_health_check(
    page,
    team_name: str | None = None,
    *,
    boss_name: str = "",
    use_context: bool | None = None,
) -> None:
    """Run one diagnostic health check, optionally selecting ``team_name`` first.

    Direct Coverage calls omit ``boss_name`` and therefore audit base builds only.
    Contextual callers can provide a Boss and/or ``use_context=True`` to audit the
    effective Team/Boss build instead.
    """
    combo = getattr(page, "scope_combo", None)
    if combo is None:
        page.status.error("Coverage build-scope control is unavailable.")
        return

    if team_name is not None:
        selected_team = str(team_name or "").strip()
    else:
        data = str(combo.currentData() or "").strip()
        if data.startswith("roster_team:"):
            selected_team = data.split(":", 1)[1].strip()
        elif data == "team":
            selected_team = str(getattr(page, "_team_scope_name", "") or "").strip()
        else:
            selected_team = ""

    if not selected_team:
        page._team_scope = ()
        page._team_scope_name = ""
        old_scope = page.scope_combo.findData("all")
        if old_scope >= 0:
            page.scope_combo.setCurrentIndex(old_scope)
        page.refresh()
        page.scope_card.set_title("All Saved Builds")
        page.scope_note.setText(
            "Library-wide build audit. Choose a raid team above to check that team's base builds."
        )
        return

    roster_service = getattr(page, "health_check_roster_service", None)
    if roster_service is None:
        roster_service = RosterService(EsoDatabase(get_user_database_path()))
        page.health_check_roster_service = roster_service

    members = tuple(
        member for member in roster_service.list_members()
        if _member_belongs_to_team(member, selected_team)
    )

    contextual = bool(boss_name) if use_context is None else bool(use_context)

    # Exact canonical team->build assignments are authoritative for identity.
    # Direct Coverage audits the assigned base build. Context variants are only
    # resolved when a caller explicitly requests contextual evaluation.
    selected, unresolved = _canonical_team_builds(
        page,
        selected_team,
        boss_name,
        use_context=contextual,
    )
    source = "canonical team assignments"
    if not selected:
        try:
            builds = tuple(page.build_service.load().Members)
        except Exception as exc:
            page.status.error(f"Could not load saved builds for {selected_team}: {exc}")
            return
        selected, unresolved = select_team_builds(
            builds,
            members,
            selected_team,
            boss_name,
            use_context=contextual,
        )
        source = "roster member matching"

    if not selected:
        _clear_empty_team_result(page, selected_team, len(members), unresolved)
        return

    page.set_team_scope(selected_team, selected, total_slots=RAID_TEAM_SLOTS)
    loaded = len(selected)
    member_count = len(members)
    context_note = (
        f" • effective context: {boss_name}"
        if contextual and boss_name
        else " • base builds only"
    )
    lines = [
        f"Direct roster health check • {member_count}/{RAID_TEAM_SLOTS} roster slots populated • "
        f"{loaded} saved team build(s) resolved via {source}{context_note}."
    ]
    if unresolved:
        lines.append(f"Build selection unresolved for: {', '.join(unresolved[:8])}")
    lines.append("Static capability evidence only. Coverage never changes the team or its builds.")
    page.scope_note.setText("\n".join(lines))
    if unresolved:
        page.status.warning(
            f"{selected_team}: health check loaded {loaded} build(s); unresolved: {', '.join(unresolved[:6])}."
        )
    else:
        mode = f"{boss_name} context" if contextual and boss_name else "base builds"
        page.status.success(
            f"{selected_team}: health check loaded {loaded} saved {mode}."
        )


def _sync_team_choices(page) -> None:
    """Expose saved Roster teams in Coverage's one canonical Build Scope menu."""
    combo = getattr(page, "scope_combo", None)
    service = getattr(page, "health_check_roster_service", None)
    if combo is None or service is None:
        return

    current = combo.currentData()
    names = tuple(service.list_team_names())
    combo.blockSignals(True)
    try:
        for index in range(combo.count() - 1, -1, -1):
            if str(combo.itemData(index) or "").startswith("roster_team:"):
                combo.removeItem(index)
        for name in names:
            combo.addItem(f"Roster Team: {name}", f"roster_team:{name}")
        if current is not None:
            index = combo.findData(current)
            if index >= 0:
                combo.setCurrentIndex(index)
    finally:
        combo.blockSignals(False)


def enhance_coverage_page(page) -> None:
    """Retain legacy team-health helpers without exposing them as Coverage scopes.

    Coverage's visible selector is owned by the Raid Plan adapter and contains saved
    Raid Plans only. Roster-team health checks remain callable by legacy/internal
    workflows, but they no longer inject competing scope choices into the page.
    """
    if bool(getattr(page, "_health_check_enhanced", False)):
        return

    page._health_check_enhanced = True
    page.health_check_roster_service = RosterService(EsoDatabase(get_data_dir() / "eso.db"))

    if hasattr(page.header, "title"):
        page.header.title.setText("Coverage")
    if hasattr(page.header, "subtitle"):
        page.header.subtitle.setText(
            "Audit one saved Raid Plan for buff, debuff, utility, and provider coverage."
        )

    scope_combo = getattr(page, "scope_combo", None)
    if scope_combo is not None:
        parent = scope_combo.parentWidget()
        if parent is not None:
            parent.setVisible(True)
        scope_combo.setToolTip(
            "Choose one saved Raid Plan. Roster teams seed plans elsewhere; "
            "Coverage evaluates the trial-specific plan."
        )


__all__ = ["enhance_coverage_page", "run_team_health_check", "select_team_builds"]
