from pathlib import Path

import app


def test_app_installs_build_progression_readiness_after_scroll_fix() -> None:
    source = Path(app.__file__).read_text(encoding="utf-8")

    import_line = (
        "from ui.build_progression_readiness_support import install as "
        "install_build_progression_readiness_support"
    )
    assert import_line in source
    assert "install_build_progression_readiness_support()" in source

    scroll_install = source.index("install_build_progression_scroll_fix()")
    readiness_install = source.index("install_build_progression_readiness_support()")
    assert scroll_install < readiness_install
