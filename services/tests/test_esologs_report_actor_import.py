import sqlite3

from services.esologs_combat_importer import EsoLogsCombatImporter


class _Client:
    def normalize_report_code(self, value):
        return str(value).strip()

    def _query(self, query, variables):
        assert "masterData" in query
        assert variables == {"code": "REPORT1"}
        return {
            "reportData": {
                "report": {
                    "masterData": {
                        "actors": [
                            {
                                "id": 101,
                                "gameID": 9001,
                                "name": "Iron Atronach",
                                "type": "NPC",
                                "subType": "NPC",
                                "petOwner": None,
                            },
                            {
                                "id": 102,
                                "gameID": 9002,
                                "name": "Daedroth",
                                "type": "NPC",
                                "subType": "NPC",
                                "petOwner": None,
                            },
                        ]
                    }
                }
            }
        }


def test_report_master_actor_import_persists_event_identity_map():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    importer = EsoLogsCombatImporter(connection, _Client())

    count = importer.import_report_actors("REPORT1")

    assert count == 2
    rows = connection.execute(
        "SELECT actor_id, game_id, name, actor_type, actor_subtype FROM log_report_actor ORDER BY actor_id"
    ).fetchall()
    assert [tuple(row) for row in rows] == [
        (101, 9001, "Iron Atronach", "NPC", "NPC"),
        (102, 9002, "Daedroth", "NPC", "NPC"),
    ]
