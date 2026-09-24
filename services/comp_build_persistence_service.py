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
from uuid import NAMESPACE_URL, uuid4, uuid5

from models.build_model import PlayerBuild
from engine.config import get_user_database_path
from models.comp_plan_state import CompChairState, CompPlanState
from services.canonical_build_bridge import CanonicalBuildBridge
from services.eso_database import EsoDatabase
from services.roster_service import RosterService


@dataclass(frozen=True)
class CompBuildPersistenceResult:
    state: CompPlanState
    saved_seats: tuple[str, ...] = ()
    skipped_seats: tuple[str, ...] = ()


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
    def _existing_comp_record(
        builds: list[dict],
        chair: CompChairState,
    ) -> dict | None:
        selected_id = str(chair.selected_build_id or "").strip()
        if selected_id:
            selected = next(
                (
                    row
                    for row in builds
                    if isinstance(row, dict)
                    and str(row.get("build_id") or "").strip() == selected_id
                ),
                None,
            )
            if (
                isinstance(selected, dict)
                and str(selected.get("build_kind") or "").strip().casefold() == "comp"
                and str(selected.get("character_id") or "").strip()
                == str(chair.character_id or "").strip()
            ):
                return selected

        return next(
            (
                row
                for row in builds
                if isinstance(row, dict)
                and str(row.get("build_kind") or "").strip().casefold() == "comp"
                and str(row.get("character_id") or "").strip()
                == str(chair.character_id or "").strip()
                and str((row.get("source") or {}).get("seat_id") or "").strip().casefold()
                == chair.seat_id.casefold()
                and str((row.get("source") or {}).get("plan_id") or "").strip()
                == str(getattr(chair, "_source_plan_id", "") or "").strip()
            ),
            None,
        )

    @staticmethod
    def _source_baseline(
        builds: list[dict],
        chair: CompChairState,
    ) -> dict | None:
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
            ),
            None,
        )

    @staticmethod
    def _build_name(state: CompPlanState, chair: CompChairState) -> str:
        explicit = str(chair.selected_build_name or "").strip()
        if explicit and str(chair.build_source_kind or "").strip().casefold() == "comp_build":
            return explicit
        return f"{state.raid_plan_name} • {chair.seat_id}"

    def persist(self, state: CompPlanState) -> CompBuildPersistenceResult:
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
        staged_roster_bindings: list[tuple[int, str, str]] = []

        for chair in state.chairs:
            if not self._is_real_player(chair) or not self._has_build_plan(chair):
                skipped.append(chair.seat_id)
                continue

            canonical_player_id, character_id = self._ensure_canonical_identity(
                chair=chair,
                catalog=catalog,
                players=players,
                characters=characters,
                staged_roster_bindings=staged_roster_bindings,
            )
            character = characters[character_id]

            if (
                str(chair.player_id or "").strip() != canonical_player_id
                or str(chair.character_id or "").strip() != character_id
            ):
                chair = chair.with_changes(
                    player_id=canonical_player_id,
                    character_id=character_id,
                    roster_member_id=chair.roster_member_id,
                )
                updated_state = updated_state.with_chair(chair)

            existing_comp = self._existing_comp_record(builds, chair)
            baseline_record = existing_comp or self._source_baseline(builds, chair)
            snapshot = self._record_snapshot(baseline_record)

            player = players.get(canonical_player_id, {})
            snapshot.PlayerId = canonical_player_id
            snapshot.CharacterId = character_id
            snapshot.Name = str(character.get("name") or chair.character_name or "").strip()
            snapshot.Gamertag = str(
                player.get("gamertag")
                or character.get("gamertag")
                or chair.player_name
                or ""
            ).strip()
            snapshot.EsoClass = str(chair.eso_class or character.get("eso_class") or snapshot.EsoClass or "").strip()
            snapshot.Role = str(chair.role or character.get("role") or snapshot.Role or "").strip()
            snapshot.BuildKind = "comp"
            snapshot.BuildName = self._build_name(state, chair)
            snapshot.PlannedGearSets = list(chair.planned_gear_sets)
            snapshot.PlannedSkills = list(chair.planned_skills)
            if chair.planned_mundus:
                snapshot.Mundus = chair.planned_mundus
            snapshot.SourcePlanId = str(state.raid_plan_id or "").strip()
            snapshot.SourcePlanName = state.raid_plan_name
            snapshot.SourceSeatId = chair.seat_id

            build_id = (
                str(existing_comp.get("build_id") or "").strip()
                if isinstance(existing_comp, dict)
                else ""
            ) or str(uuid4())
            snapshot.BuildId = build_id
            legacy = snapshot.to_dict()
            payload = deepcopy(legacy)
            payload["PlayerId"] = canonical_player_id
            payload["CharacterId"] = character_id
            payload["BuildId"] = build_id

            record = {
                "build_id": build_id,
                "character_id": character_id,
                "name": snapshot.BuildName,
                "build_kind": "comp",
                "source": {
                    "kind": "comp_maker",
                    "plan_id": str(state.raid_plan_id or "").strip(),
                    "plan_name": state.raid_plan_name,
                    "seat_id": chair.seat_id,
                    "candidate_id": str(chair.candidate_id or "").strip(),
                    "source_kind": str(chair.build_source_kind or "").strip(),
                    "source_name": str(chair.build_source_name or "").strip(),
                    "source_url": str(chair.build_source_url or "").strip(),
                },
                "legacy": legacy,
                "payload": payload,
            }

            replaced = False
            for index, current in enumerate(builds):
                if str(current.get("build_id") or "").strip() == build_id:
                    builds[index] = record
                    replaced = True
                    break
            if not replaced:
                builds.append(record)

            updated_chair = chair.with_changes(
                selected_build_id=build_id,
                selected_build_name=snapshot.BuildName,
                build_source_kind="comp_build",
                build_source_name="Comp Maker",
            )
            updated_state = updated_state.with_chair(updated_chair)
            saved.append(chair.seat_id)

        if saved:
            catalog["builds"] = builds
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
        )


__all__ = ["CompBuildPersistenceResult", "CompBuildPersistenceService"]
