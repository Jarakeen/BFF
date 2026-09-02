from services.paths import PROJECT_ROOT


def test_pyinstaller_build_uses_foundrydock_without_upx() -> None:
    spec = (PROJECT_ROOT / "packaging" / "BFF.spec").read_text(encoding="utf-8")

    assert 'name="FoundryDock"' in spec
    assert "upx=False" in spec
    assert "upx=True" not in spec


def test_build_scripts_expect_foundrydock_executable() -> None:
    for relative_path in (
        "packaging/build_friend.ps1",
        "packaging/build_test.ps1",
        "packaging/FRIEND_README.txt",
    ):
        text = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        assert "FoundryDock.exe" in text
        assert "BFF.exe" not in text
