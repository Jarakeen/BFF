from tools.collect_collectible_icons import CollectibleRef, _candidates_for_file


def test_saved_uesp_html_prefers_collectible_image_over_nearby_frame(tmp_path):
    page = tmp_path / "mounts.htm"
    page.write_text(
        """
        <html><head><title>Mounts - UESP</title></head><body>
        <img src="//images.uesp.net/thumb/b/b4/ON-icon-ActiveFrame.png/48px-ON-icon-ActiveFrame.png">
        <a href="//esoitem.uesp.net/itemLink.php?collectid=42&quality=5" collectid="42">Ashen Wolf</a>
        <img src="//images.uesp.net/1/12/ON-icon-collectible-Ashen_Wolf.png">
        <img src="//images.uesp.net/2/34/ON-icon-achievement-Random_Thing.png">
        </body></html>
        """,
        encoding="utf-8",
    )
    collectibles = {
        42: CollectibleRef(
            id=42,
            name="Ashen Wolf",
            icon="/esoui/art/icons/collectible_ashen_wolf.dds",
        )
    }

    candidates = _candidates_for_file(page, collectibles)
    best = max((candidate for candidate in candidates if candidate.collectible_id == 42), key=lambda item: item.score)

    assert best.url == "https://images.uesp.net/1/12/ON-icon-collectible-Ashen_Wolf.png"
    assert best.score > 30
