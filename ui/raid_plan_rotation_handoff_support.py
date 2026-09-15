from __future__ import annotations

"""Bind one visible Raid Plan chair into the existing canonical Rotation workspace.

RaidPlan owns the selected chair/build/assignments. Rotation owns encounter selection,
generation policy, evidence resolution, and executable planning. This adapter freezes the
exact plan-selected saved build and wraps Rotation's existing canonical context provider;
it does not create a second Rotation or RaidPlan authority.
"""

from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan
from services.raid_plan_saved_build_resolution_service import (
    RaidPlanSavedBuildResolutionService,
)
from ui.raid_plan_rotation_context_bridge import RaidPlanRotationContextBridge


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value: object) -> str:
    return _clean(value).casefold()


def _character_name(build: PlayerBuild) -> str:
    return _clean(getattr(build, "CharacterName", "") or getattr(build, "Name", ""))


class _ExactBuildPageProxy:
    """Proxy live Rotation controls while pinning build reads to one resolved build."""

    def __init__(self, page, build: PlayerBuild) -> None:
        self._page = page
        self._build = build

    def _selected_build(self):
        return self._build

    def __getattr__(self, name: str):
        return getattr(self._page, name)


class RaidPlanRotationGenerateContextProvider:
    """Add stable RaidPlan ownership to Rotation's existing live context provider."""

    def __init__(
        self,
        *,
        base_provider,
        raid_plan: RaidPlan,
        seat_id: str,
        build: PlayerBuild,
        bridge: RaidPlanRotationContextBridge | None = None,
    ) -> None:
        if not callable(getattr(base_provider, "context_for", None)):
            raise TypeError("Raid Plan Rotation handoff requires a canonical context provider")
        self.base_provider = base_provider
        self.raid_plan = raid_plan
        self.seat_id = _clean(seat_id)
        self.build = PlayerBuild.from_dict(build.to_dict())
        self.bridge = bridge or RaidPlanRotationContextBridge()

    def context_for(self, page):
        encounter_id = _clean(page.selected_encounter_id())
        if not encounter_id:
            raise ValueError("select an encounter before generating the Raid Plan rotation")

        base_context = self.base_provider.context_for(
            _ExactBuildPageProxy(page, self.build)
        )
        member = self.raid_plan.member(self.seat_id)
        if member is None:
            raise ValueError(f"Raid Plan seat {self.seat_id!r} is no longer present")

        provenance = tuple(
            text
            for text in (
                f"Primary assignment: {member.primary_assignment}" if member.primary_assignment else "",
                f"Secondary assignment: {member.secondary_assignment}" if member.secondary_assignment else "",
            )
            if text
        )
        return self.bridge.bind(
            base_context=base_context,
            raid_plan=self.raid_plan,
            seat_id=self.seat_id,
            saved_builds=(self.build,),
            encounter_id=encounter_id,
            provenance=provenance,
        )


def _same_build(candidate: PlayerBuild, wanted: PlayerBuild) -> bool:
    return (
        _key(getattr(candidate, "BuildName", "")) == _key(getattr(wanted, "BuildName", ""))
        and _key(getattr(candidate, "Gamertag", "")) == _key(getattr(wanted, "Gamertag", ""))
        and _key(_character_name(candidate)) == _key(_character_name(wanted))
    )


def select_exact_rotation_build(page, build: PlayerBuild) -> None:
    """Make Rotation's visible selectors agree with the exact plan-owned build."""
    if not isinstance(build, PlayerBuild):
        raise TypeError("Rotation build selection requires PlayerBuild")

    # Refresh the Rotation page's reusable-build snapshot before selecting. This changes
    # only UI/application state; saved-build ownership remains with BuildService.
    page.roster = page.build_service.load()
    loader = getattr(page, "_load_characters", None)
    if not callable(loader):
        raise TypeError("Rotation page does not expose saved-character loading")
    loader()

    character = _character_name(build)
    character_index = page.character_combo.findData(character)
    if character_index < 0:
        raise ValueError(f"Rotation cannot select Raid Plan character {character!r}")
    page.character_combo.setCurrentIndex(character_index)

    matching_index = -1
    for combo_index in range(page.build_combo.count()):
        roster_index = page.build_combo.itemData(combo_index)
        if not isinstance(roster_index, int) or not 0 <= roster_index < len(page.roster.Members):
            continue
        candidate = page.roster.Members[roster_index]
        if isinstance(candidate, PlayerBuild) and _same_build(candidate, build):
            matching_index = combo_index
            break
    if matching_index < 0:
        raise ValueError(
            "Rotation cannot select the exact Raid Plan saved build; refresh or resolve duplicate build identity first"
        )
    page.build_combo.setCurrentIndex(matching_index)

    selected = page._selected_build()
    if not isinstance(selected, PlayerBuild) or not _same_build(selected, build):
        raise ValueError("Rotation visible build selection does not match the Raid Plan build")


def bind_raid_plan_rotation_page(
    page,
    *,
    raid_plan: RaidPlan,
    seat_id: str,
) -> RaidPlanRotationGenerateContextProvider:
    """Bind one plan chair to Rotation without changing persisted RaidPlan shape."""
    if not isinstance(raid_plan, RaidPlan):
        raise TypeError("Rotation handoff requires RaidPlan")

    roster = page.build_service.load()
    saved_builds = tuple(getattr(roster, "Members", ()) or ())
    resolution = RaidPlanSavedBuildResolutionService().resolve(
        raid_plan=raid_plan,
        seat_id=seat_id,
        saved_builds=saved_builds,
    )
    if not resolution.resolved or resolution.build is None:
        detail = "; ".join(resolution.unresolved) or "saved build ownership unresolved"
        raise ValueError("Raid Plan chair cannot open Rotation: " + detail)

    select_exact_rotation_build(page, resolution.build)

    provider = getattr(page, "rotation_generate_canonical_context_provider", None)
    if isinstance(provider, RaidPlanRotationGenerateContextProvider):
        provider = provider.base_provider
    if not callable(getattr(provider, "context_for", None)):
        raise ValueError(
            "Rotation canonical application context provider is unavailable; restart the app before opening this Raid Plan chair"
        )

    handoff = RaidPlanRotationGenerateContextProvider(
        base_provider=provider,
        raid_plan=raid_plan,
        seat_id=resolution.seat_id,
        build=resolution.build,
    )
    setter = getattr(page, "set_rotation_generate_canonical_context_provider", None)
    if not callable(setter):
        raise TypeError("Rotation page cannot accept canonical Generate context providers")
    setter(handoff)
    page.raid_plan_rotation_handoff = handoff

    member = raid_plan.member(resolution.seat_id)
    assignments = " / ".join(
        value
        for value in (
            _clean(getattr(member, "primary_assignment", "")),
            _clean(getattr(member, "secondary_assignment", "")),
        )
        if value
    )
    suffix = f" • {assignments}" if assignments else ""
    page.status.info(
        f"Raid Plan: {raid_plan.name} • {member.gamertag} • {resolution.build.BuildName}{suffix}. "
        "Select the encounter and Generate Rotation."
    )
    return handoff


__all__ = [
    "RaidPlanRotationGenerateContextProvider",
    "bind_raid_plan_rotation_page",
    "select_exact_rotation_build",
]
