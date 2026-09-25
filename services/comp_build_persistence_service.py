from __future__ import annotations

"""Persist accepted Comp Maker chair plans as canonical builds.

Comp Maker owns draft planning state. Once the user saves, every real occupied chair
with a planned build receives a stable canonical build ID before Raid Plan persistence.
Normal saved builds are never overwritten; Comp Maker writes/updates build_kind="comp"
records in the same canonical build catalog.
"""

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from models.build_model import PlayerBuild
from engine.config import get_user_database_path
from models.comp_plan_state import CompChairState, CompPlanState
from services.canonical_build_bridge import CanonicalBuildBridge
from services.eso_database import EsoDatabase
from services.roster_player_identity_service import RosterPlayerIdentityService
from services.roster_service import RosterService


@dataclass(frozen=True)
class CompBuildPersistenceResult:
    state: CompPlanState
    saved_seats: tuple[str, ...] = ()
    skipped_seats: tuple[str, ...] = ()
    skipped_reasons: tuple[tuple[str, str], ...] = ()


class CompBuildPersistenceService:
    def __init__(
        self,
        data_dir: str | Path,
        *,
        database_path: str | Path | None = None,
    ):
        self.data_dir = Path(data_dir)
        self.user_database_path = (
            Path(database_path)
            if database_path is not None
            else get_user_database_path()
        )

        # Comp Builds, canonical Players/Characters, and Personnel are all
        # user-owned state. They must share the same foundrydock.db authority.
        # The legacy JSON paths are migration inputs only.
        self.bridge = CanonicalBuildBridge(
            self.data_dir / "builds.json",
            catalog_path=self.user_database_path,
        )
        self.database = EsoDatabase(self.user_database_path)
        self.roster = RosterService(self.database)

    def _repair_personnel_identity(self, chair: CompChairState) -> tuple[CompChairState, str]:
        """Recover an exact merged/current Personnel identity by player name.

        Comp state can legitimately lag Personnel after a duplicate-player merge:
        the chair may still display a learned alias while its stable ids were not
        carried into the in-memory Comp session. Exact current-name/alias matching
        is safe evidence; fuzzy matching remains forbidden.
        """
        if chair.is_open_player or not chair.player_name:
            return chair, ""
        if chair.roster_member_id is not None and (
            chair.player_id or chair.character_id
        ):
            return chair, ""

        identity = RosterPlayerIdentityService(self.database, None)
        # A selected Personnel row is stronger evidence than its display name.
        # Newly added roster players may not yet have canonical catalog IDs.
        if chair.roster_member_id is not None:
            selected = self.roster.get_member(int(chair.roster_member_id))
            matches = [selected] if selected is not None else []
            issue = "selected Personnel record no longer exists" if selected is None else ""
        else:
            matches = identity.matching_members(chair.player_name)
            if len(matches) > 1 and chair.character_name:
                matches = [
                    member for member in matches
                    if str(member.CharacterName or "").strip().casefold()
                    == str(chair.character_name).strip().casefold()
                ]
            issue = ""
        if len(matches) != 1:
            if not issue:
                issue = (
                    f"{len(matches)} active Personnel records match {chair.player_name!r}; merge duplicates in Players"
                    if matches
                    else f"no active Personnel record matches {chair.player_name!r}; check the saved player name"
                )
            return chair, issue

        member = matches[0]
        # Never let a legacy display-name repair bind a chair to Personnel whose
        # canonical player is already owned by a different chair in this Comp
        # state. Duplicate-seat validation runs again after repair at the UI save
        # boundary; keeping the repaired stable ids here makes that guard reliable.

        return chair.with_changes(
            player_name=str(member.PlayerName or chair.player_name).strip(),
            roster_member_id=int(member.Id) if member.Id is not None else chair.roster_member_id,
            player_id=str(member.CanonicalPlayerId or "").strip() or chair.player_id,
            character_id=str(member.CanonicalCharacterId or "").strip() or chair.character_id,
            character_name=str(member.CharacterName or chair.character_name or "").strip() or chair.character_name,
            eso_class=str(member.EsoClass or chair.eso_class or "").strip() or chair.eso_class,
            role=str(member.PrimaryRole or chair.role or "").strip() or chair.role,
        ), ""

    @staticmethod
    def _is_real_player(chair: CompChairState) -> bool:
        return bool(
            chair.player_name
            and not chair.is_open_player
            and (
                (chair.player_id and chair.character_id)
                or chair.roster_member_id is not None
            )
        )

    @staticmethod
    def _has_build_plan(chair: CompChairState) -> bool:
        return bool(
            chair.selected_build_id
            or chair.selected_build_name
            or chair.planned_gear_sets
            or chair.planned_skills
            or chair.planned_mundus
        )

    @staticmethod
    def _promoted_id(kind: str, roster_member_id: int) -> str:
        return str(uuid5(NAMESPACE_URL, f"bff:comp:{kind}:roster-member:{int(roster_member_id)}"))

    def _ensure_canonical_identity(
        self,
        *,
        chair: CompChairState,
        catalog: dict,
        players: dict[str, dict],
        characters: dict[str, dict],
        staged_roster_bindings: list[tuple[int, str, str]],
    ) -> tuple[str, str]:
        """Resolve or explicitly promote one real Personnel row to canonical identity.

        Promotion uses roster_member_id as the stable seed. It never joins an existing
        canonical player or character by display name.
        """
        player_id = str(chair.player_id or "").strip()
        character_id = str(chair.character_id or "").strip()

        if character_id:
            character = characters.get(character_id)
            if character is None:
                raise ValueError(
                    f"{chair.seat_id}: canonical character {character_id!r} does not exist"
                )
            owner_id = str(character.get("player_id") or "").strip()
            if player_id and owner_id and player_id != owner_id:
                raise ValueError(
                    f"{chair.seat_id}: player/character ownership mismatch"
                )
            player_id = player_id or owner_id

        if player_id and player_id not in players:
            raise ValueError(
                f"{chair.seat_id}: canonical player {player_id!r} does not exist"
            )

        roster_member_id = chair.roster_member_id
        if player_id and character_id:
            return player_id, character_id

        if roster_member_id is None:
            raise ValueError(
                f"{chair.seat_id}: real player has no canonical identity or Personnel row"
            )
        roster_member = self.roster.get_member(int(roster_member_id))
        if roster_member is None:
            raise ValueError(
                f"{chair.seat_id}: Personnel row {roster_member_id} does not exist"
            )

        roster_player_id = str(roster_member.CanonicalPlayerId or "").strip()
        roster_character_id = str(roster_member.CanonicalCharacterId or "").strip()

        if roster_character_id:
            character = characters.get(roster_character_id)
            if character is None:
                raise ValueError(
                    f"{chair.seat_id}: Personnel references missing canonical character "
                    f"{roster_character_id!r}"
                )
            owner_id = str(character.get("player_id") or "").strip()
            if roster_player_id and owner_id and roster_player_id != owner_id:
                raise ValueError(
                    f"{chair.seat_id}: Personnel player/character bindings disagree"
                )
            character_id = character_id or roster_character_id
            player_id = player_id or roster_player_id or owner_id

        if roster_player_id:
            if roster_player_id not in players:
                raise ValueError(
                    f"{chair.seat_id}: Personnel references missing canonical player "
                    f"{roster_player_id!r}"
                )
            player_id = player_id or roster_player_id

        if not player_id:
            player_id = self._promoted_id("player", int(roster_member_id))
            if player_id not in players:
                player = {
                    "player_id": player_id,
                    "gamertag": str(roster_member.PlayerName or chair.player_name or "").strip(),
                    "display_name": str(roster_member.PlayerName or chair.player_name or "").strip(),
                    "notes": "",
                    "status": str(roster_member.Status or "Active").strip() or "Active",
                    "avatar_path": "",
                }
                catalog.setdefault("players", []).append(player)
                players[player_id] = player

        if not character_id:
            character_id = self._promoted_id("character", int(roster_member_id))
            if character_id not in characters:
                character = {
                    "character_id": character_id,
                    "player_id": player_id,
                    "name": str(roster_member.CharacterName or chair.character_name or "").strip(),
                    "gamertag": str(roster_member.PlayerName or chair.player_name or "").strip(),
                    "eso_class": str(roster_member.EsoClass or chair.eso_class or "").strip(),
                    "race": "",
                    "role": str(roster_member.PrimaryRole or chair.role or "").strip(),
                    "alliance": "",
                    "vampire": False,
                    "werewolf": False,
                    "owned_skill_lines": [],
                    "passive_ranks": {},
                    "passive_cp_points": {},
                }
                catalog.setdefault("characters", []).append(character)
                characters[character_id] = character

        owner_id = str(characters[character_id].get("player_id") or "").strip()
        if owner_id != player_id:
            raise ValueError(
                f"{chair.seat_id}: promoted character does not belong to promoted player"
            )

        staged_roster_bindings.append(
            (int(roster_member_id), player_id, character_id)
        )
        return player_id, character_id

    @staticmethod
    def _record_snapshot(record: dict | None) -> PlayerBuild:
        if not isinstance(record, dict):
            return PlayerBuild()
        payload = record.get("payload")
        legacy = record.get("legacy")
        source = payload if isinstance(payload, dict) else legacy
        return PlayerBuild.from_dict(source if isinstance(source, dict) else {})

    @staticmethod
    def _source_baseline(
        builds: list[dict],
        chair: CompChairState,
    ) -> dict | None:
        """Return the explicitly selected reusable saved Build, never a Comp artifact."""
        selected_id = str(chair.selected_build_id or "").strip()
        if not selected_id:
            return None
        return next(
            (
                row
                for row in builds
                if isinstance(row, dict)
                and str(row.get("build_id") or "").strip() == selected_id
                and str(row.get("character_id") or "").strip()
                == str(chair.character_id or "").strip()
                and str(row.get("build_kind") or "saved").strip().casefold() != "comp"
            ),
            None,
        )


    def persist(self, state: CompPlanState) -> CompBuildPersistenceResult:
        """Validate Comp chair identity without manufacturing another Build flavor.

        Comp Maker owns Raid Plan assignment/override state. A reusable saved Build
        remains a reference by BuildId; planned gear/skills/mundus remain on the
        chair. Legacy build_kind="comp" rows stay readable for history/recovery but
        no new Comp Build rows are created here.
        """
        catalog = self.bridge.load_catalog()
        builds = [
            deepcopy(row)
            for row in catalog.get("builds", [])
            if isinstance(row, dict)
        ]
        characters = {
            str(row.get("character_id") or "").strip(): row
            for row in catalog.get("characters", [])
            if isinstance(row, dict) and str(row.get("character_id") or "").strip()
        }
        players = {
            str(row.get("player_id") or "").strip(): row
            for row in catalog.get("players", [])
            if isinstance(row, dict) and str(row.get("player_id") or "").strip()
        }

        updated_state = state
        saved: list[str] = []
        skipped: list[str] = []
        skipped_reasons: list[tuple[str, str]] = []
        staged_roster_bindings: list[tuple[int, str, str]] = []

        for original_chair in state.chairs:
            chair, identity_issue = self._repair_personnel_identity(original_chair)

            if not self._is_real_player(chair):
                skipped.append(chair.seat_id)
                reason = (
                    "open/recruit chair"
                    if chair.is_open_player or not chair.player_name
                    else identity_issue
                    or "player is not linked to a Personnel record; load the saved player list"
                )
                skipped_reasons.append((chair.seat_id, reason))
                if chair != original_chair:
                    updated_state = updated_state.with_chair(chair)
                continue

            try:
                canonical_player_id, character_id = self._ensure_canonical_identity(
                    chair=chair,
                    catalog=catalog,
                    players=players,
                    characters=characters,
                    staged_roster_bindings=staged_roster_bindings,
                )
            except ValueError as exc:
                skipped.append(chair.seat_id)
                skipped_reasons.append((chair.seat_id, str(exc).removeprefix(f"{chair.seat_id}: ")))
                if chair != original_chair:
                    updated_state = updated_state.with_chair(chair)
                continue
            if (
                str(chair.player_id or "").strip() != canonical_player_id
                or str(chair.character_id or "").strip() != character_id
            ):
                chair = chair.with_changes(
                    player_id=canonical_player_id,
                    character_id=character_id,
                )

            selected_id = str(chair.selected_build_id or "").strip()
            selected_record = self._source_baseline(builds, chair) if selected_id else None
            if selected_id and selected_record is None:
                legacy_comp = next(
                    (
                        row
                        for row in builds
                        if str(row.get("build_id") or "").strip() == selected_id
                        and str(row.get("build_kind") or "").strip().casefold() == "comp"
                    ),
                    None,
                )
                if legacy_comp is not None:
                    # Old Comp Builds are historical snapshots, not reusable Build
                    # assignments. Keep their planned chair data, but detach the
                    # pseudo-Build reference so it cannot masquerade as Saved.
                    chair = chair.with_changes(
                        selected_build_id=None,
                        selected_build_name=None,
                        build_source_kind="planned",
                        build_source_name="Raid Plan",
                    )
                    selected_id = ""
                else:
                    raise ValueError(
                        f"{chair.seat_id}: selected Build does not belong to this character"
                    )

            if selected_record is not None:
                build_name = str(selected_record.get("name") or chair.selected_build_name or "").strip()
                chair = chair.with_changes(
                    selected_build_name=build_name or chair.selected_build_name,
                    build_source_kind="saved_build",
                    build_source_name=build_name or "Saved Build",
                )
            elif chair.planned_gear_sets or chair.planned_skills or chair.planned_mundus:
                chair = chair.with_changes(
                    selected_build_id=None,
                    selected_build_name=None,
                    build_source_kind="planned",
                    build_source_name="Raid Plan",
                )
            elif not self._has_build_plan(chair):
                skipped.append(chair.seat_id)
                skipped_reasons.append((chair.seat_id, "no saved or planned build assignment"))
                updated_state = updated_state.with_chair(chair)
                continue

            updated_state = updated_state.with_chair(chair)
            saved.append(chair.seat_id)

        # Canonical identity promotion may add Players/Characters. Persist those
        # additions, but never add/update a Build merely because Comp Maker saved.
        if staged_roster_bindings:
            self.bridge.save_catalog(catalog)
        for roster_member_id, player_id, character_id in dict.fromkeys(
            staged_roster_bindings
        ):
            self.database.execute(
                """
                UPDATE roster_member
                SET canonical_player_id = ?, canonical_character_id = ?
                WHERE id = ?
                """,
                (player_id, character_id, roster_member_id),
            )
        if staged_roster_bindings:
            self.database.commit()

        return CompBuildPersistenceResult(
            state=updated_state,
            saved_seats=tuple(saved),
            skipped_seats=tuple(skipped),
            skipped_reasons=tuple(skipped_reasons),
        )



__all__ = ["CompBuildPersistenceResult", "CompBuildPersistenceService"]
