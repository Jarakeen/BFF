from pathlib import Path

from tools.recover_uesp_alchemy_missing_u50_traits import (
    MISSING_U50_TRAITS,
    parse_effect_html,
    recover,
    source_url,
)


def _page(effect: str) -> str:
    return f"""
    <html><body>
      <h1>Online:{effect}</h1>
      <table>
        <tr><th>Solvent</th><th>Level</th><th>Potion</th><th>Effect</th></tr>
        <tr><td>Lorkhan's Tears</td><td>CP150</td><td>Essence</td><td>example</td></tr>
      </table>
    </body></html>
    """


def test_missing_u50_trait_scope_is_explicit():
    assert MISSING_U50_TRAITS == ("Ravage Magicka", "Ravage Stamina", "Timidity")


def test_parse_effect_html_requires_exact_page_identity():
    record = parse_effect_html(
        _page("Timidity"),
        expected_effect="Timidity",
        source=source_url("Timidity"),
    )
    assert record["effect_name"] == "Timidity"
    assert len(record["potion_tiers"]) == 1

    try:
        parse_effect_html(
            _page("Ravage Magicka"),
            expected_effect="Timidity",
            source=source_url("Timidity"),
        )
    except ValueError as exc:
        assert "identity mismatch" in str(exc)
    else:
        raise AssertionError("mismatched effect page should fail closed")


def test_recover_writes_v3_supplementary_record_shape(tmp_path: Path):
    output = tmp_path / "missing_traits.json"

    def fetcher(url: str) -> str:
        effect = url.rsplit("Online:", 1)[1].replace("_", " ")
        return _page(effect)

    payload, exit_code = recover(
        effects=MISSING_U50_TRAITS,
        output=output,
        fetcher=fetcher,
    )

    assert exit_code == 0
    assert output.exists()
    assert [row["effect_name"] for row in payload["records"]] == list(MISSING_U50_TRAITS)
    assert payload["failures"] == []
