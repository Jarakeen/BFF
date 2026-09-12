import json
from pathlib import Path

from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjectionService,
)


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_projection_builds_timeline_and_strategy_from_reviewed_evidence(tmp_path: Path):
    _write(
        tmp_path / "encounter_evidence" / "boss.json",
        {
            "schema_version": 1,
            "content_id": "trial",
            "encounter_id": "boss",
            "encounter_name": "Boss",
            "evidence": [
                {
                    "fact_type": "phase",
                    "fact_key": "phase_1",
                    "value": {"label": "Opening", "order": 1},
                    "source_type": "guide",
                    "source_name": "Guide A",
                    "confidence": "high",
                },
                {
                    "fact_type": "transition",
                    "fact_key": "execute_transition",
                    "value": {"threshold": "30%", "result": "execute"},
                    "source_type": "guide",
                    "source_name": "Guide A",
                    "confidence": "high",
                },
                {
                    "fact_type": "mechanic_state",
                    "fact_key": "big_blast_exists",
                    "value": True,
                    "source_type": "guide",
                    "source_name": "Guide A",
                    "confidence": "high",
                },
                {
                    "fact_type": "mechanic_detail",
                    "fact_key": "big_blast_behavior",
                    "value": {"target_count": 3, "radius_m": 8},
                    "source_type": "guide",
                    "source_name": "Guide A",
                    "confidence": "high",
                },
            ],
        },
    )
    _write(
        tmp_path / "reference_mitigations.json",
        {
            "schema_version": 1,
            "entries": [
                {
                    "entry_name": "Big Blast — Boss",
                    "mitigation": "Spread out.",
                    "source": "reviewed_encounter_evidence",
                }
            ],
        },
    )
    _write(
        tmp_path / "reference_common_names.json",
        {
            "schema_version": 1,
            "entries": [
                {
                    "entry_name": "Big Blast — Boss",
                    "common_names": ["Boom"],
                    "source": "player_raid_terminology",
                }
            ],
        },
    )

    projection = EncounterGuideEvidenceProjectionService(tmp_path).get("boss", "Boss")

    assert [(row.marker, row.label) for row in projection.timeline] == [
        ("P1", "Opening"),
        ("30%", "Execute Transition"),
    ]
    blast = next(row for row in projection.strategy if row.mechanic == "Big Blast")
    assert blast.common_names == ("Boom",)
    assert blast.mitigation == "Spread out."
    assert "Target Count: 3" in blast.summary
    assert projection.callouts == ("Big Blast: Spread out.",)


def test_real_dsr_twins_projection_exposes_timeline_and_strategy():
    projection = EncounterGuideEvidenceProjectionService(DATA).get(
        "lylanar_turlassil", "Lylanar and Turlassil"
    )

    assert any(row.label == "Hounds" for row in projection.timeline)
    assert any(row.label == "Brothers Reunited" for row in projection.timeline)
    names = {row.mechanic for row in projection.strategy}
    assert "Destructive Ember" in names
    assert "Synchronized Kill" in names
    synced = next(row for row in projection.strategy if row.mechanic == "Synchronized Kill")
    assert "7.5 seconds" in synced.mitigation


def test_real_reef_guardian_projection_exposes_replication_strategy():
    projection = EncounterGuideEvidenceProjectionService(DATA).get(
        "reef_guardian", "Reef Guardian"
    )

    replication = next(row for row in projection.strategy if row.mechanic == "Replication")
    assert "80%" in replication.mitigation
    assert "50%" in replication.mitigation
    assert "HM" in replication.mitigation


def test_real_reef_guardian_projection_exposes_reviewed_tank_role_impact():
    projection = EncounterGuideEvidenceProjectionService(DATA).get(
        "reef_guardian", "Reef Guardian"
    )

    role_text = "\n".join(projection.role_impact)

    assert "Tanks" in role_text
    assert "Acid Reflux" in role_text
    assert "taunt target" in role_text
    assert "persistent pools" in role_text
    assert "stacking vulnerability" in role_text


def test_real_taleria_projection_exposes_thresholds_and_reviewed_mechanics():
    projection = EncounterGuideEvidenceProjectionService(DATA).get(
        "tideborn_taleria", "Tideborn Taleria"
    )

    markers = {row.marker for row in projection.timeline}
    names = {row.mechanic for row in projection.strategy}

    assert {"~75%", "50%", "35%", "20%"}.issubset(markers)
    assert "Rapid Deluge" in names
    assert "Crashing Wave" in names
    assert "Maelstrom" in names
    assert "Coral Slam" in names
    assert "Arcing Slash" in names

    deluge = next(row for row in projection.strategy if row.mechanic == "Rapid Deluge")
    crashing = next(row for row in projection.strategy if row.mechanic == "Crashing Wave")
    maelstrom = next(row for row in projection.strategy if row.mechanic == "Maelstrom")

    assert "swim" in deluge.mitigation.casefold()
    assert "dodge" in crashing.mitigation.casefold() or "block" in crashing.mitigation.casefold()
    assert "heal" in maelstrom.mitigation.casefold()


def test_real_xalvakka_projection_exposes_phase_and_split_structure():
    projection = EncounterGuideEvidenceProjectionService(DATA).get(
        "xalvakka", "Xalvakka"
    )

    markers = {row.marker for row in projection.timeline}
    labels = {row.label for row in projection.timeline}
    names = {row.mechanic for row in projection.strategy}

    assert {"70%", "40%"}.issubset(markers)
    assert "Phase 2" in labels
    assert "Phase 3" in labels
    assert "Summon Wraiths" in names
    assert "Soul Resonance" in names
    assert "Retreat" in names
    assert "Split" in names
    assert "Deadstar" in names
    assert "Havocrel Goliath Summons" in names

    goliath = next(row for row in projection.strategy if row.mechanic == "Havocrel Goliath Summons")
    assert "safe zone" in goliath.mitigation.casefold()
    assert "center" in goliath.mitigation.casefold()


def test_bahsei_reviewed_research_populates_overview_without_canonical_packet():
    projection = EncounterGuideEvidenceProjectionService(DATA).get(
        "flame_herald_bahsei", "Flame-Herald Bahsei"
    )

    names = {row.mechanic for row in projection.strategy}
    brief = "\n".join(projection.brief)
    timeline = {(row.marker, row.label) for row in projection.timeline}

    assert ("55%", "Burning Specters") in timeline
    assert ("55%", "Dagon's Wrath") in timeline
    assert ("50%", "Meteor Swarm") in timeline
    assert ("30%", "Prime Meteor Execute") in timeline

    assert "Skull Salvo" in names
    assert "Cursed Ground/Unholy Spike" in names
    assert "Death Touch/Kiss of Death" in names
    assert "Meteor Swarm" in names
    assert "Summoning Runes" in names
    assert "Summon Behemoth" in names
    assert "Dagon's Wrath" in names
    assert "50%, 40%, 25%, 20%, and 10%" in brief

    summoning = next(row for row in projection.strategy if row.mechanic == "Summoning Runes")
    behemoth = next(row for row in projection.strategy if row.mechanic == "Summon Behemoth")
    curse = next(row for row in projection.strategy if row.mechanic == "Death Touch/Kiss of Death")

    assert "90%, 85%, 80%, 75%, 70%, 65%, and 60%" in summoning.summary
    assert "50%, 40%, 25%, 20%, 10%" in behemoth.summary
    assert "separation" in curse.mitigation.casefold()


def test_oaxiltso_reviewed_research_populates_overview_without_canonical_packet():
    projection = EncounterGuideEvidenceProjectionService(DATA).get(
        "oaxiltso", "Oaxiltso"
    )

    names = {row.mechanic for row in projection.strategy}
    brief = "\n".join(projection.brief)

    assert "Savage Blitz" in names
    assert "Fiery Stomp" in names
    assert "Blistering Smash" in names
    assert "Noxious Sludge" in names
    assert "Summon Havocrel Annihilators" in names
    assert "90%, 75%, 50%, and 25%" in brief

    blitz = next(row for row in projection.strategy if row.mechanic == "Savage Blitz")
    assert "dodge" in blitz.mitigation.casefold()
