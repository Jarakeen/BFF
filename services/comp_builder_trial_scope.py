from __future__ import annotations


COMP_MAKER_TRIALS: tuple[str, ...] = (
    "Sunspire",
    "Rockgrove",
    "Dreadsail Reef",
    "Sanity's Edge",
    "Lucent Citadel",
    "Ossein Cage",
    "Cloudrest",
    "Kyne's Aegis",
    "Asylum Sanctorium",
    "Halls of Fabrication",
)

# Existing reference/template catalogs are achievement-keyed in some places. Keep
# those legacy identities underneath the new trial-first UI rather than discarding
# useful evidence when the visible selector changes from achievement to trial.
_DEFAULT_GOAL_BY_TRIAL: dict[str, str] = {
    "Sunspire": "Godslayer",
    "Rockgrove": "Planebreaker",
    "Dreadsail Reef": "Swashbuckler Supreme",
    "Cloudrest": "Gryphon Heart",
    "Kyne's Aegis": "Dawnbringer",
    "Asylum Sanctorium": "Immortal Redeemer",
    "Halls of Fabrication": "Tick-Tock Tormentor",
}

_LEGACY_TRIAL_BY_GOAL: dict[str, str] = {
    "Godslayer": "Sunspire",
    "Planebreaker": "Rockgrove",
    "Swashbuckler Supreme": "Dreadsail Reef",
    "Hurricane Herald": "Dreadsail Reef",
    "Gryphon Heart": "Cloudrest",
    "Dawnbringer": "Kyne's Aegis",
    "Immortal Redeemer": "Asylum Sanctorium",
    "Tick-Tock Tormentor": "Halls of Fabrication",
}


def trial_for_selection(value: str) -> str:
    selected = " ".join(str(value or "").strip().split())
    if selected in COMP_MAKER_TRIALS:
        return selected
    return _LEGACY_TRIAL_BY_GOAL.get(selected, selected)


def default_goal_for_trial(trial_name: str) -> str:
    trial = trial_for_selection(trial_name)
    return _DEFAULT_GOAL_BY_TRIAL.get(trial, trial)
