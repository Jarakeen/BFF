from bs4 import BeautifulSoup

from crawlers.eso_hub_cp_section_parser import extract_current_cp_section


def test_extracts_current_eso_hub_inline_cp_links_and_conditions():
    soup = BeautifulSoup(
        """
        <main>
          <div>Champion Points that buff Energy Orb</div>
          <ul>
            <li><a href='/en/champion-points/star/blessed'>Blessed</a></li>
            <li><a href='/en/champion-points/star/rejuvenator'>Rejuvenator</a> (only while slotted)</li>
            <li><a href='/en/champion-points/star/soothing-tide'>Soothing Tide</a> (only while slotted)</li>
          </ul>
          <h4>Unmorphed version</h4>
          <a href='/en/champion-points/star/swift-renewal'>Swift Renewal</a>
        </main>
        """,
        "html.parser",
    )
    cp_vocab = {
        "blessed": {"id": 1, "name": "Blessed"},
        "rejuvenator": {"id": 2, "name": "Rejuvenator"},
        "soothing tide": {"id": 3, "name": "Soothing Tide"},
        "swift renewal": {"id": 4, "name": "Swift Renewal"},
    }

    rows, error = extract_current_cp_section(soup, "Energy Orb", cp_vocab)

    assert error is None
    assert [(row["champion_point_name"], row["condition"]) for row in rows] == [
        ("Blessed", None),
        ("Rejuvenator", "only while slotted"),
        ("Soothing Tide", "only while slotted"),
    ]


def test_missing_exact_section_fails_closed():
    soup = BeautifulSoup("<main><a>Rejuvenator</a></main>", "html.parser")
    rows, error = extract_current_cp_section(
        soup,
        "Energy Orb",
        {"rejuvenator": {"id": 2, "name": "Rejuvenator"}},
    )

    assert rows == []
    assert error == "CP section not found"
