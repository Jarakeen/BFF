from minmax.skill_known_effects import verified_skill_effects
from minmax.support_target_type import SupportTargetType


CASES = (
    (183555, 0, "Arcanist's Domain", 20.0),
    (85536, 1, "Enchanted Growth", 20.0),
    (33195, 2, "Refreshing Path", 10.0),
    (28418, 2, "Regenerative Ward", 10.0),
    (26209, 0, "Restoring Aura", 20.0),
)


def test_verified_minor_intellect_self_effects_are_present():
    for base_ability_id, morph, source, duration in CASES:
        effects = verified_skill_effects(base_ability_id, morph)
        matches = tuple(effect for effect in effects if effect.name == "minor_intellect")
        assert len(matches) == 1
        effect = matches[0]
        assert effect.source == source
        assert effect.magnitude == 0.15
        assert effect.duration == duration
        assert effect.target_type is SupportTargetType.SELF
        assert effect.condition is None
        assert effect.trigger is None
