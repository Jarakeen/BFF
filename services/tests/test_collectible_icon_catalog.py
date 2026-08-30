import json

from services.collectible_icon_catalog import CollectibleIconCatalog


def test_manifest_resolves_existing_local_icon(tmp_path):
    icon_dir = tmp_path / "collectible_icons"
    icon_dir.mkdir()
    image = icon_dir / "42_test_mount.png"
    image.write_bytes(b"png-data")
    (icon_dir / "manifest.json").write_text(
        json.dumps({"entries": {"42": {"file": image.name}}}),
        encoding="utf-8",
    )

    catalog = CollectibleIconCatalog(tmp_path)

    assert catalog.path_for(42) == image.resolve()
    assert catalog.available_count == 1


def test_manifest_rejects_path_outside_icon_cache(tmp_path):
    icon_dir = tmp_path / "collectible_icons"
    icon_dir.mkdir()
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"not-allowed")
    (icon_dir / "manifest.json").write_text(
        json.dumps({"entries": {"99": {"file": "../outside.png"}}}),
        encoding="utf-8",
    )

    catalog = CollectibleIconCatalog(tmp_path)

    assert catalog.path_for(99) is None
    assert catalog.available_count == 0
