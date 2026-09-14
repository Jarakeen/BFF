from __future__ import annotations

"""Guarantee imported Context Variants survive persistence and disambiguate Builds UI rows.

The roster importer has several compatibility wrappers.  This final guard runs after
all of them, verifies that any ContextVariants prepared by the import plan are present
on the saved build, and restores them if an older compatibility path dropped them.
It also makes the Builds sidebar show the build name, because several builds can
legitimately belong to the same character.
"""

from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem

from models.build_model import BuildRoster, PlayerBuild


_INSTALLED = False
_ORIGINAL_APPLY_ROSTER_IMPORT = None
_ORIGINAL_REFRESH_ROSTER = None


def _identity_key(value: object) -> str:
    return " ".join(str(value or "").strip().split()).lstrip("@").casefold()


def _text_key(value: object) -> str:
    return " ".join(str(value or "").strip().split()).casefold()


def _expected_build(member, candidate) -> PlayerBuild:
    payload = deepcopy(getattr(candidate, "payload", {}) or {})
    payload["Name"] = str(getattr(member, "character_name", "") or "").strip()
    payload["Gamertag"] = str(getattr(member, "gamertag", "") or "").strip()
    payload["BuildName"] = str(getattr(candidate, "build_name", "") or "").strip()
    payload["EsoClass"] = (
        str(getattr(member, "eso_class", "") or "").strip()
        or str(getattr(candidate, "eso_class", "") or "").strip()
    )
    payload["Role"] = (
        str(getattr(member, "primary_role", "") or "").strip()
        or str(getattr(candidate, "role", "") or "").strip()
    )
    return PlayerBuild.from_dict(payload)


def _restore_prepared_variants(plan, build_service) -> int:
    """Restore only ContextVariants that the reviewed import plan already prepared."""
    expected_by_key: dict[tuple[str, str, str], list] = {}
    for member in getattr(plan, "members", ()):
        if not bool(getattr(member, "selected", True)):
            continue
        for candidate in getattr(member, "builds", ()) or ():
            expected = _expected_build(member, candidate)
            if not expected.ContextVariants:
                continue
            key = (
                _identity_key(expected.Gamertag),
                _text_key(expected.Name),
                _text_key(expected.BuildName),
            )
            expected_by_key[key] = deepcopy(expected.ContextVariants)

    if not expected_by_key:
        return 0

    roster = build_service.load()
    repaired = 0
    for saved in roster.Members:
        key = (
            _identity_key(getattr(saved, "Gamertag", "")),
            _text_key(getattr(saved, "Name", "")),
            _text_key(getattr(saved, "BuildName", "")),
        )
        expected = expected_by_key.get(key)
        if expected is None:
            continue
        if [item.to_dict() for item in saved.ContextVariants] == [item.to_dict() for item in expected]:
            continue
        saved.ContextVariants = deepcopy(expected)
        saved.BossLoadouts = []
        repaired += 1

    if repaired:
        build_service.save(BuildRoster(Members=list(roster.Members)))
    return repaired


def apply_roster_import_with_variant_persistence_guard(
    plan,
    roster_service,
    build_service,
    *,
    import_builds: bool = True,
):
    if not callable(_ORIGINAL_APPLY_ROSTER_IMPORT):
        raise RuntimeError("Roster variant persistence guard is not installed.")

    result = _ORIGINAL_APPLY_ROSTER_IMPORT(
        plan,
        roster_service,
        build_service,
        import_builds=import_builds,
    )
    if not import_builds:
        return result

    repaired = _restore_prepared_variants(plan, build_service)
    if not repaired:
        return result

    warnings = list(result.warnings)
    warnings.append(
        f"Verified and restored Context Variants on {repaired} imported base build(s)."
    )
    return type(result)(
        created_roster_members=result.created_roster_members,
        updated_roster_members=result.updated_roster_members,
        imported_builds=result.imported_builds,
        skipped_builds=result.skipped_builds,
        warnings=tuple(warnings),
    )


def _refresh_roster_with_build_identity(self, *_args) -> None:
    """Show Character + BuildName so legitimate multi-build characters are distinguishable."""
    current = self.selected_index
    self.roster_list.blockSignals(True)
    self.roster_list.clear()

    for index, build in enumerate(self.roster.Members):
        role, status = self._role_for(build)
        character = build.Name.strip() or build.Gamertag.strip() or f"Member {index + 1}"
        build_name = build.BuildName.strip() or "Default"
        variants = list(getattr(build, "ContextVariants", ()) or ())
        if not variants:
            variants = list(getattr(build, "BossLoadouts", ()) or ())
        variant_suffix = f"  [{len(variants)} variant{'s' if len(variants) != 1 else ''}]" if variants else ""
        label = f"{character}  •  {build_name}{variant_suffix}"
        if role:
            label += f"  {role}"

        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, index)
        tooltip = f"{build.EsoClass or 'Class not set'} • {status}"
        if variants:
            tooltip += f" • {len(variants)} context variant{'s' if len(variants) != 1 else ''}"
        item.setToolTip(tooltip)
        self.roster_list.addItem(item)

    if self.roster_list.count():
        self.roster_list.setCurrentRow(min(max(current, 0), self.roster_list.count() - 1))
    self.roster_list.blockSignals(False)
    self._select_member(self.roster_list.currentRow())


def install() -> None:
    global _INSTALLED, _ORIGINAL_APPLY_ROSTER_IMPORT, _ORIGINAL_REFRESH_ROSTER
    if _INSTALLED:
        return

    from ui import roster_import_workflow
    from ui.builds_page import BuildsPage

    _ORIGINAL_APPLY_ROSTER_IMPORT = roster_import_workflow.apply_roster_import
    roster_import_workflow.apply_roster_import = apply_roster_import_with_variant_persistence_guard

    _ORIGINAL_REFRESH_ROSTER = BuildsPage._refresh_roster
    BuildsPage._refresh_roster = _refresh_roster_with_build_identity
    _INSTALLED = True


__all__ = [
    "install",
    "apply_roster_import_with_variant_persistence_guard",
    "_restore_prepared_variants",
]
