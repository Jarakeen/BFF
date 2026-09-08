from __future__ import annotations

"""Keep named raid-support effects from disappearing behind top-N aura ranking.

The canonical performance service historically kept only the eight highest-
uptime rows returned by each ESO Logs aura table. That is reasonable for a
"top buffs" chart, but wrong for explicit tracking: Major Brittle, Major Slayer,
Major Courage, etc. can be present in the full aura table yet fall outside the
top eight and then look falsely absent in the dashboard.

This compatibility layer keeps the original top-N ordering and additionally
preserves any known support effect that exists anywhere in the fetched aura
rows. It does not invent data and it does not create timeline intervals; those
require ESO Logs event/interval queries rather than aggregate aura totals.
"""

_INSTALLED = False

_TRACKED_SUPPORT_EFFECTS = {
    "major brittle",
    "minor berserk",
    "major courage",
    "major slayer",
    "major vulnerability",
    "minor vulnerability",
    "major force",
    "minor force",
    "major breach",
    "minor breach",
    "off balance",
    "major resolve",
    "minor resolve",
    "major protection",
    "minor protection",
    "major mending",
    "minor mending",
    "empower",
}


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from services import performance_dashboard_service as service_module

    original_top_uptimes = service_module._top_uptimes

    def top_uptimes_with_tracked_support(auras, duration_seconds: float, limit: int):
        # Preserve the canonical ranked rows exactly as before.
        ranked = list(original_top_uptimes(auras, duration_seconds, limit))
        ranked_keys = {row.Name.strip().casefold() for row in ranked}

        # Re-run the canonical parser without a practical cap so explicit
        # support effects can be recovered from the same fetched table.
        all_rows = list(original_top_uptimes(auras, duration_seconds, max(len(auras), limit)))
        for row in all_rows:
            key = row.Name.strip().casefold()
            if key in _TRACKED_SUPPORT_EFFECTS and key not in ranked_keys:
                ranked.append(row)
                ranked_keys.add(key)

        return ranked

    service_module._top_uptimes = top_uptimes_with_tracked_support
    _INSTALLED = True
