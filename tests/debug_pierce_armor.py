from pathlib import Path

from bs4 import BeautifulSoup

from eso_hub_skill_crawler import (
    extract_relationship_items,
)


HTML_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "raw"
    / "pierce_armor_debug.html"
)


def main():

    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Pierce Armor Relationship Test")
    print("=" * 60)
    print()

    soup = BeautifulSoup(
        HTML_PATH.read_text(
            encoding="utf-8"
        ),
        "html.parser",
    )

    sets = extract_relationship_items(
        soup,
        "Armor sets that modify",
    )

    print()
    print("MODIFYING SETS:")
    print()

    for item in sets:
        print(item)

    print()
    print(
        f"Total sets found: {len(sets)}"
    )

    expected_urls = {
        "https://eso-hub.com/en/sets/perfected-puncturing-remedy",
        "https://eso-hub.com/en/sets/puncturing-remedy",
    }

    actual_urls = {
        item.get("url")
        for item in sets
    }

    print()
    print("EXPECTED URL CHECK:")

    for url in expected_urls:

        if url in actual_urls:
            print(f"  PASS: {url}")
        else:
            print(f"  FAIL: {url}")

    missing = expected_urls - actual_urls

    print()

    if missing:
        raise SystemExit(
            "FAIL: One or more expected "
            "modifying sets were not found."
        )

    print("=" * 60)
    print(" MODIFYING SET TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()