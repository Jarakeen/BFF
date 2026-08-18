from pathlib import Path

from services.minmax.effects import EffectOperation, EffectUnit
from services.minmax.glyph_repository import GlyphEffectRepository
from services.minmax.stat_ids import StatId


DB_PATH = Path("data/eso.db")



def test_health_recovery_glyph_can_resolve_minimum():
    repository = GlyphEffectRepository(DB_PATH)

    effects = repository.get_jewelry_glyph_effect(
        26581,
        use_max_value=False,
    )

    assert len(effects) == 1
    assert effects[0].value == 13    