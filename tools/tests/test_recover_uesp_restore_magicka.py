from tools.recover_uesp_restore_magicka import parse_restore_magicka_html


def test_parse_restore_magicka_html_recovers_potion_tiers_and_source():
    html = """
    <html><body>
      <h1>Online:Restore Magicka</h1>
      <table>
        <tr><th>Solvent</th><th>Level</th><th>Potion</th><th>Restore</th></tr>
        <tr><td>Lorkhan's Tears</td><td>CP150</td><td>Essence of Magicka</td><td>7582 Magicka</td></tr>
      </table>
    </body></html>
    """

    record = parse_restore_magicka_html(
        html,
        source_url="https://en.uesp.net/wiki/Online:Restore_Magicka",
    )

    assert record["effect_name"] == "Restore Magicka"
    assert record["source_files"] == [
        "https://en.uesp.net/wiki/Online:Restore_Magicka"
    ]
    assert record["potion_tiers"] == [
        {
            "solvent": "Lorkhan's Tears",
            "level": "CP150",
            "name": "Essence of Magicka",
            "values": ["7582 Magicka"],
        }
    ]


def test_parse_restore_magicka_html_rejects_wrong_page():
    html = "<html><body><h1>Online:Restore Stamina</h1></body></html>"

    try:
        parse_restore_magicka_html(html, source_url="example")
    except ValueError as exc:
        assert "does not identify Restore Magicka" in str(exc)
    else:
        raise AssertionError("wrong UESP page should fail closed")
