from __future__ import annotations

"""Install the approved Rotation Builder mockup without rebuilding the live context card.

The older mockup finisher predates Team/Difficulty context and its context rebuild can
orphan those canonical controls. The compact-context layer now owns that card, so this
bridge applies the rest of the approved mockup composition and leaves context alone.
"""

from ui import rotation_builder_mockup_finish_support as mockup


def install_rotation_builder_v2_mockup_bridge(page) -> None:
    if bool(getattr(page, "_rotation_builder_v2_mockup_bridge_installed", False)):
        return
    if not hasattr(page, "rotation_builder_tabs"):
        raise RuntimeError("Rotation Builder V2 tabs must exist before mockup composition")

    mockup._polish_tabs(page)
    mockup._rebuild_style(page)
    mockup._rebuild_rules(page)
    mockup._rebuild_pressure(page)
    mockup._rebuild_timeline(page)
    mockup._rebuild_resources(page)
    mockup._rebuild_explanations(page)
    mockup._install_result_refresh(page)

    page._rotation_builder_v2_mockup_bridge_installed = True


__all__ = ["install_rotation_builder_v2_mockup_bridge"]
