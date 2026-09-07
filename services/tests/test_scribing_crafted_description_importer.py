import sqlite3

from importers.scribing_crafted_description_importer import (
    UespCraftedScriptDescriptionImporter,
    clean_eso_markup,
)


def _html() -> str:
    return """
    <html><body>
    <h1>ESO: Viewing Update 51 PTS: Crafted Script Descriptions</h1>
    <table id='esologtable'>
      <thead><tr><th></th><th>id</th><th>craftedAbilityId</th><th>scriptId</th><th>classId</th><th>abilityId</th><th>name</th><th>description</th><th></th></tr></thead>
      <tbody>
      <tr><td>View</td><td>528</td><td>12</td><td>46</td><td>0</td><td>217699</td><td>Banner Bearer</td><td>Grants you Major Savagery, increasing Weapon and Spell Critical rating by |cffffff2629|r.</td><td></td></tr>
      <tr><td>View</td><td>360</td><td>12</td><td>31</td><td>3</td><td>217699</td><td>Banner Bearer</td><td>Restore |cffffff400|r Magicka and Stamina.\nThis effect reapplies itself every |cffffff5|r seconds.</td><td></td></tr>
      </tbody>
    </table>
    </body></html>
    """


def test_clean_eso_markup_preserves_wrapped_values():
    assert clean_eso_markup("Gain |cffffff2629|r Critical and |cffffff5|r% damage") == (
        "Gain 2629 Critical and 5% damage"
    )


def test_parser_models_u51_rows_without_color_tags(tmp_path):
    source = tmp_path / "crafted.htm"
    source.write_text(_html(), encoding="utf-8")

    rows = UespCraftedScriptDescriptionImporter.parse_html(source)

    assert len(rows) == 2
    assert rows[0].crafted_ability_id == 12
    assert rows[0].script_id == 46
    assert rows[0].ability_id == 217699
    assert rows[0].name == "Banner Bearer"
    assert rows[0].description.endswith("2629.")
    assert "|c" not in rows[0].description
    assert "|r" not in rows[0].description
    assert "|cffffff2629|r" in rows[0].description_raw
    assert rows[1].class_id == 3
    assert "400 Magicka" in rows[1].description
    assert "every 5 seconds" in rows[1].description


def test_importer_creates_versioned_provenance_and_rows(tmp_path):
    source = tmp_path / "crafted.htm"
    source.write_text(_html(), encoding="utf-8")
    database = tmp_path / "eso.db"
    sqlite3.connect(database).close()

    importer = UespCraftedScriptDescriptionImporter(database)
    summary = importer.run(source_path=source)

    assert summary.rows == 2
    assert summary.crafted_abilities == 1
    assert summary.scripts == 2
    assert summary.classes == 2
    assert summary.abilities == 1
    assert summary.names == 1

    with sqlite3.connect(database) as connection:
        source_row = connection.execute(
            "SELECT source_record, game_update, channel, row_count FROM scribing_crafted_description_source"
        ).fetchone()
        assert source_row == ("craftedScriptDescriptions51pts", 51, "PTS", 2)

        imported = connection.execute(
            """
            SELECT source_row_id, crafted_ability_id, script_id, class_id,
                   ability_id, name, description_raw, description
            FROM scribing_crafted_script_description
            ORDER BY source_row_id
            """
        ).fetchall()

    assert len(imported) == 2
    assert imported[0][0] == 360
    assert "|cffffff400|r" in imported[0][6]
    assert "|c" not in imported[0][7]
    assert imported[1][0] == 528
    assert imported[1][7].endswith("2629.")


def test_reimport_replaces_same_source_snapshot_without_duplicates(tmp_path):
    source = tmp_path / "crafted.htm"
    source.write_text(_html(), encoding="utf-8")
    database = tmp_path / "eso.db"
    sqlite3.connect(database).close()

    importer = UespCraftedScriptDescriptionImporter(database)
    importer.run(source_path=source)
    importer.run(source_path=source)

    with sqlite3.connect(database) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM scribing_crafted_script_description"
        ).fetchone()[0]
    assert count == 2
